from utils.network_utils import send_message
import config

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
			peer_manager.logger.log("FOLLOW", f"{from_user} is now following {to_user}")

	elif msg_type == "UNFOLLOW":
		from_user = message.get("FROM")
		to_user = message.get("TO")
		message_id = message.get("MESSAGE_ID")
		timestamp = message.get("TIMESTAMP")
		token = message.get("TOKEN")

		peer_manager.remove_follower(to_user, from_user, token, timestamp, message_id)

		# Only show unfollow notification in non-verbose mode
		if not peer_manager.logger.verbose:
			print(f"User {from_user} has unfollowed you")