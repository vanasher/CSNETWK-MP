from utils.network_utils import send_message
import config
from utils.network_utils import validate_token
from utils.game_utils import print_board
from utils.game_utils import check_game_result
from utils.game_utils import send_result_message

# Routes incoming LSNP messages to appropriate PeerManager handlers based on the message type
def dispatch(message: dict, addr: str, peer_manager):
	msg_type = message.get("TYPE")

	if msg_type == "PROFILE":
		user_id = message.get("USER_ID")
		name = message.get("DISPLAY_NAME")
		status = message.get("STATUS")
		avatar_type = message.get("AVATAR_TYPE")
		avatar_encoding = message.get("AVATAR_ENCODING")
		avatar_data = message.get("AVATAR_DATA")
		if user_id and name:
			peer_manager.add_peer(user_id, name, status, avatar_type, avatar_encoding, avatar_data)

	elif msg_type == "POST":
		user_id = message.get("USER_ID")
		content = message.get("CONTENT")
		ttl = int(message.get("TTL", 3600)) # default is 3600 per RFC
		message_id = message.get("MESSAGE_ID")
		token = message.get("TOKEN")
		if user_id and content:
			# Only store posts from users we're following
			if peer_manager.is_following(user_id):
				peer_manager.add_post(user_id, content, None, ttl, message_id)
				#peer_manager.logger.log("POST", f"Received post from {user_id}: {content[:50]}...")

	elif msg_type == "DM":
		from_user = message.get("FROM")
		to_user = message.get("TO")
		timestamp = message.get("TIMESTAMP")
		content = message.get("CONTENT")
		message_id = message.get("MESSAGE_ID")
		token = message.get("TOKEN")

		# validate input fields
		if not (from_user and to_user and content and message_id and timestamp and token):
			peer_manager.logger.log_drop("Malformed DM message.")
			return

		# makes sure this message is intended for the user
		my_user_id = peer_manager.own_profile.get("USER_ID")
		if to_user != my_user_id:
			peer_manager.logger.log_drop(f"Ignored DM not addressed to me: {to_user}")
			return

		# store the DM
		peer_manager.add_dm(from_user, content, timestamp, message_id, token)
		# peer_manager.logger.log("DM", f"Received DM from {from_user}: {content[:50]}...")

		# send an ACK back to the sender
		if message_id:
			ack_msg = {
				"TYPE": "ACK",
				"MESSAGE_ID": message_id,
				"STATUS": "RECEIVED"
			}
			send_message(ack_msg, (addr, config.PORT))

	elif msg_type == "PING":
		user_id = message.get("USER_ID")
		# if peer_manager.logger.verbose:
		# 	print(f"[PING] Received ping from {user_id}")

		# resgister peer if not already known (optional)
		# if user_id and user_id not in peer_manager.peers:
		# 		peer_manager.add_peer(user_id, user_id, "", None, None)

	elif msg_type == "ACK":
		message_id = message.get("MESSAGE_ID")
		status = message.get("STATUS")

		if message_id in peer_manager.pending_acks:
			del peer_manager.pending_acks[message_id]
			#peer_manager.logger.log("ACK", f"ACK received for {message_id}: {status}")

	elif msg_type == "FOLLOW":
		message_id = message.get("MESSAGE_ID")
		from_user = message.get("FROM")
		to_user = message.get("TO")
		timestamp = message.get("TIMESTAMP")
		token = message.get("TOKEN")

		if from_user and to_user:
			peer_manager.add_follower(to_user, from_user, token, timestamp, message_id)
			# peer_manager.logger.log("FOLLOW", f"{from_user} is now following {to_user}")

	elif msg_type == "UNFOLLOW":
		from_user = message.get("FROM")
		to_user = message.get("TO")
		message_id = message.get("MESSAGE_ID")
		timestamp = message.get("TIMESTAMP")
		token = message.get("TOKEN")

		peer_manager.remove_follower(to_user, from_user, token, timestamp, message_id)

		# Only show unfollow notification in non-verbose mode
		# if not peer_manager.logger.verbose:
		# 	print(f"User {from_user} has unfollowed you")

	elif msg_type == "REVOKE":
		token = message.get("TOKEN")
		if token:
			peer_manager.revoked_tokens.add(token)
			peer_manager.logger.log("REVOKE", f"Token revoked: {token}")
		return
	
	elif msg_type == "TICTACTOE_INVITE":
		token = message.get("TOKEN")
		valid, reason = validate_token(token, "game", peer_manager.revoked_tokens)
		if not valid:
			peer_manager.logger.log_drop("TICTACTOE_INVITE", addr, reason)
			return

		game_id = message.get("GAMEID")
		from_user = message.get("FROM")
		if game_id in peer_manager.games:
			peer_manager.logger.log_info(f"Duplicate game invite for GAMEID {game_id} ignored.")
			return

		peer_manager.create_game(game_id, from_user, is_initiator=False, token=token)
		# peer_manager.logger.log("TICTACTOE_INVITE", addr, message)
		print(f"New Tic Tac Toe game started with {from_user}.")
		print_board(peer_manager.games[game_id]["board"])

	elif msg_type == "TICTACTOE_MOVE":
		game_id = message.get("GAMEID")
		turn = int(message.get("TURN"))
		pos = int(message.get("POSITION"))
		symbol = message.get("SYMBOL")
		from_user = message.get("FROM")

		game = peer_manager.games.get(game_id)
		if not game:
			peer_manager.logger.log_drop("TICTACTOE_MOVE", addr, f"Unknown GAMEID {game_id}")
			return

		if turn != game["turn"]:
			peer_manager.logger.log_drop("TICTACTOE_MOVE", addr, f"Unexpected TURN: got {turn}, expected {game['turn']}")
			return

		if game["board"][pos] != " ":
			peer_manager.logger.log_drop("TICTACTOE_MOVE", addr, "Invalid move: position already taken")
			return

		success = peer_manager.apply_move(game_id, pos, symbol)
		if success:
			# peer_manager.logger.log("TICTACTOE_MOVE", addr, message)
			print_board(game["board"])
			
			# check win/draw?
			result = check_game_result(game["board"])
			if result:
				send_result_message(game_id, result, from_user, peer_manager.get_own_profile().get("USER_ID"))
		else:
			peer_manager.logger.log_drop("TICTACTOE_MOVE", addr, "Failed to apply move")

	elif msg_type == "TICTACTOE_RESULT":
		game_id = message.get("GAMEID")
		result = message.get("RESULT")
		winner = message.get("WINNER")

		game = peer_manager.games.pop(game_id, None)
		if not game:
			peer_manager.logger.log_drop("TICTACTOE_RESULT", addr, f"No active game with GAMEID {game_id}")
			return

		# peer_manager.logger.log("TICTACTOE_RESULT", addr, message)

		if result == "DRAW":
			print(f"Game {game_id} ended in a draw.")
		elif winner == peer_manager.get_own_profile().get("USER_ID"):
			print(f"You won the game {game_id}!")
		else:
			print(f"You lost game {game_id}. Winner: {winner}")