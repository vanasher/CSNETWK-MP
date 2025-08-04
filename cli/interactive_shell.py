from utils.network_utils import send_message, get_local_ip
from core.peer import PeerManager
import json
import config
from parser.message_parser import craft_message
from parser.message_parser import parse_message
from utils.network_utils import validate_token
from utils.game_utils import print_board
import uuid

def run_shell(logger, peer_manager):
	print("LSNP Interactive Shell. Type 'help' for commands.")

	while True:
		try:
			cmd = input(">>> ").strip()

			if cmd == "exit":
				for token in peer_manager.issued_tokens:
					revoke_msg = {
						"TYPE": "REVOKE",
						"TOKEN": token
					}
					send_message(revoke_msg, (config.BROADCAST_ADDR, config.PORT))
					logger.log_send("REVOKE", get_local_ip(), revoke_msg)

				print("Exiting...")
				break
			
			# 'profile' command to set own profile
			elif cmd == "profile":
				# If no profile is set, prompt for username
				if peer_manager.own_profile is None:
					username = input("Username: ").strip()
				# If profile is set, use the existing username (user can't change it after setting it already)
				else:
					username = peer_manager.own_profile["USER_ID"].split('@')[0]
				display_name = input("Display name: ").strip()
				status = input("Status: ").strip()

				peer_manager.set_own_profile(username, display_name, status)
				logger.log("SHELL", f"Profile set for {username} and will be broadcast periodically.")

			# 'post' command to create a new post
			elif cmd == "post":
				
				own_profile = peer_manager.own_profile
				if not own_profile or "USER_ID" not in own_profile:
					print("Profile not set. Please set your profile first using the 'profile' command.")
					continue
				
				content = input("Post content: ").strip()
				if not content:
					print("Post content cannot be empty.")
					continue

				# ttl_input = input("TTL (in seconds, default 3600): ").strip()
				# try:
				# 	ttl = int(ttl_input) if ttl_input else 3600
				# 	if ttl <= 0:
				# 		raise ValueError
				# except ValueError:
				# 	print("Invalid TTL. Must be a positive integer.")
				# 	continue

				ttl = config.TTL  # default TTL per RFC

				import time, random
				now = int(time.time())

				user_id = own_profile["USER_ID"]
				message_id = f"{random.getrandbits(64):016x}"
				token = f"{user_id}|{now + ttl}|broadcast"

				post_message = {
					"TYPE": "POST",
					"USER_ID": user_id,
					"CONTENT": content,
					"TTL": ttl,
					"MESSAGE_ID": message_id,
					"TOKEN": token
				}

				# check if token is valid
				is_valid, error = validate_token(post_message["TOKEN"], "broadcast", peer_manager.revoked_tokens)
				if not is_valid:
					logger.log("REJECT", f"POST rejected: {error}")
					return
				
				# send only to followers
				follower_ips = peer_manager.get_follower_ips()
				for ip in follower_ips:
					send_message(post_message, (ip, config.PORT))
				peer_manager.issued_tokens.append(token)
				logger.log_send("POST", get_local_ip(), post_message)

			# 'dm' command to send a direct message to a peer
			elif cmd == "dm":
				recipient = input("Recipient (user_id@ip): ").strip()
				content = input("Message: ").strip()
				if not recipient or not content:
					print("Recipient and content cannot be empty.")
					continue

				if "@" not in recipient or recipient.count("@") != 1:
					print("Invalid recipient format. Use user@ip.")
					continue
				
				import time, random
				now = int(time.time())
				ttl = config.TTL
				sender = peer_manager.own_profile["USER_ID"]
				message_id = f"{random.getrandbits(64):016x}"
				token = f"{sender}|{now + ttl}|chat"

				dm_message = {
					"TYPE": "DM",
					"FROM": sender,
					"TO": recipient,
					"CONTENT": content,
					"TIMESTAMP": now,
					"MESSAGE_ID": message_id,
					"TOKEN": token
				}

				# check if token is valid
				is_valid, error = validate_token(dm_message["TOKEN"], "chat", peer_manager.revoked_tokens)
				if not is_valid:
					logger.log("REJECT", f"DM rejected: {error}")
					return
				
				# Extract IP from recipient (format: user@ip)
				try:
					_, ip = recipient.split("@")
					send_message(dm_message, (ip, config.PORT))
					peer_manager.issued_tokens.append(token)
					logger.log_send("DM", ip, dm_message, peer_manager)

					# track for retransmission if needed
					peer_manager.pending_acks[message_id] = {
						"message": dm_message,
						"addr": (ip, config.PORT),
						"timestamp": time.time(),
						"attempts": 1
					}
				except ValueError:
					print("Invalid recipient format. Use user@ip.")
				except Exception as e:
					print(f"Failed to send DM: {e}")

			# 'follow' command to follow another user
			elif cmd == "follow":
				target_user = input("User to follow (user_id@ip): ").strip()
				if not target_user:
					print("Target user cannot be empty.")
					continue

				if not peer_manager.own_profile or "USER_ID" not in peer_manager.own_profile:
					print("Profile not set. Please set your profile first using the 'profile' command.")
					continue

				import time, random
				now = int(time.time())
				sender = peer_manager.own_profile["USER_ID"]
				message_id = f"{random.getrandbits(64):016x}"
				token = f"{sender}|{now + config.TTL}|follow"

				follow_message = {
					"TYPE": "FOLLOW",
					"FROM": sender,
					"TO": target_user,
					"MESSAGE_ID": message_id,
					"TIMESTAMP": now,
					"TOKEN": token
				}
				
				# check if token is valid
				is_valid, error = validate_token(follow_message["TOKEN"], "follow", peer_manager.revoked_tokens)
				if not is_valid:
					logger.log("REJECT", f"FOLLOW rejected: {error}")
					return
				
				# Extract IP from target user (format: user@ip)
				try:
					_, ip = target_user.split("@")
					send_message(follow_message, (ip, config.PORT))
					
					peer_manager.issued_tokens.append(token)
					# Add to local following list
					peer_manager.follow(target_user)
					# print(f"Follow request sent to {target_user}.")
					logger.log_send("FOLLOW", ip, follow_message, peer_manager)
				except ValueError:
					print("Invalid user format. Use user@ip.")

			# 'unfollow' command to unfollow a user
			elif cmd == "unfollow":
				target_user = input("User to unfollow (user_id@ip): ").strip()
				if not target_user:
					print("Target user cannot be empty.")
					continue

				if not peer_manager.own_profile or "USER_ID" not in peer_manager.own_profile:
					print("Profile not set. Please set your profile first using the 'profile' command.")
					continue

				if not peer_manager.is_following(target_user):
					print(f"You are not following {target_user}.")
					continue

				import time, random
				now = int(time.time())
				sender = peer_manager.own_profile["USER_ID"]
				message_id = f"{random.getrandbits(64):016x}"
				token = f"{sender}|{now + config.TTL}|follow"

				unfollow_message = {
					"TYPE": "UNFOLLOW",
					"FROM": sender,
					"TO": target_user,
					"MESSAGE_ID": message_id,
					"TIMESTAMP": now,
					"TOKEN": token
				}

				# check if token is valid
				is_valid, error = validate_token(unfollow_message["TOKEN"], "follow", peer_manager.revoked_tokens)
				if not is_valid:
					logger.log("REJECT", f"UNFOLLOW rejected: {error}")
					return
				
				# Extract IP from target user (format: user@ip)
				try:
					_, ip = target_user.split("@")
					send_message(unfollow_message, (ip, config.PORT))
					
					peer_manager.issued_tokens.append(token)
					# Remove from local following list
					peer_manager.following.discard(target_user)
					# print(f"Unfollow request sent to {target_user}.")
					logger.log_send("UNFOLLOW", ip, unfollow_message)
				except ValueError:
					print("Invalid user format. Use user@ip.")

			# 'list' command to show peers and following status
			elif cmd == "list":
				print("\n--- Known Peers ---")
				peers = peer_manager.list_peers()
				if peers:
					for user_id, display_name in peers:
						following_status = " (Following)" if peer_manager.is_following(user_id) else ""
						print(f"  {display_name} ({user_id}){following_status}")
				else:
					print("  No peers discovered yet.")
				
				print(f"\n--- Following ({len(peer_manager.following)}) ---")
				if peer_manager.following:
					for user_id in peer_manager.following:
						display_name = peer_manager.get_display_name(user_id)
						print(f"  {display_name} ({user_id})")
				else:
					print("  Not following anyone.")

			# 'show' command to show detailed peer information with posts and DMs
			elif cmd == "show":
				target_user = input("Enter user ID to show details (or 'all' for all peers): ").strip()
				
				if target_user.lower() == "all":
					print("\n=== ALL KNOWN PEERS WITH POSTS AND DMs ===")
					peers = peer_manager.list_peers()
					if not peers:
						print("No peers discovered yet.")
					else:
						for user_id, display_name in peers:
							peer_manager.show_peer_details(user_id, display_name)
							print("-" * 50)
				else:
					if not target_user:
						print("User ID cannot be empty.")
						continue
					
					# Check if peer exists
					peer_info = peer_manager.peers.get(target_user)
					if not peer_info:
						print(f"Peer '{target_user}' not found.")
						print("Available peers:")
						peers = peer_manager.list_peers()
						for user_id, display_name in peers:
							print(f"  {display_name} ({user_id})")
						continue
					
					print(f"\n=== PEER DETAILS: {target_user} ===")
					peer_manager.show_peer_details(target_user, peer_info['display_name'])

			# switching verbose/non-verbose mode
			elif cmd.startswith("verbose"):
				parts = cmd.split()
				if len(parts) == 2 and parts[1] in ["on", "off"]:
					logger.set_verbose(parts[1] == "on")
				else:
					print("Usage: verbose [on|off]")

			# simulate sending a message
			elif cmd == "simulate":
				msg_type = input("Message type: ").strip()
				if msg_type == "profile":
					msg_type = "PROFILE"
					username = input("Username: ").strip()
					display_name = input("Display name: ").strip()
					status = input("Status: ").strip()

					user_id = f"{username}@{get_local_ip()}"
					message = {
						"TYPE": "PROFILE",
						"USER_ID": user_id,
						"DISPLAY_NAME": display_name,
						"STATUS": status,
						"AVATAR_TYPE": None,
						"AVATAR_ENCODING": None,
						"AVATAR_DATA": None,
					}
					print("\nCrafted Message:\n")
					print(craft_message(message))
					print("Parsed Message:\n")
					print(parse_message(craft_message(message)))
					print("\nSender:")
					logger.log_send(msg_type, get_local_ip(), message, peer_manager)
					print("\nReceiver:")
					logger.log_recv(msg_type, get_local_ip(), message, peer_manager)

				elif msg_type == "post":
					msg_type = "POST"
					content = input("Post content: ").strip()
					if not content:
						print("Post content cannot be empty.")
						continue

					ttl = 3600
					import time, random
					now = int(time.time())

					user_id = "example@"+get_local_ip()
					message_id = f"{random.getrandbits(64):016x}"
					token = f"{user_id}|{now + ttl}|broadcast"

					message = {
						"TYPE": "POST",
						"USER_ID": user_id,
						"CONTENT": content,
						"TTL": ttl,
						"MESSAGE_ID": message_id,
						"TOKEN": token
					}

					print("\nCrafted Message:\n")
					print(craft_message(message))
					print("Parsed Message:\n")
					print(parse_message(craft_message(message)))
					print("\nSender:")
					logger.log_send(msg_type, get_local_ip(), message, peer_manager) # Note: this will cause errors in non-verbose mode since it does not store the peer
					print("\nReceiver:")
					logger.log_recv(msg_type, get_local_ip(), message, peer_manager)

				elif msg_type == "dm":
					msg_type = "DM"
					recipient = input("Recipient (user_id@ip): ").strip()
					content = input("Message: ").strip()
					if not recipient or not content:
						print("Recipient and content cannot be empty.")
						continue

					import time, random
					now = int(time.time())
					ttl = 3600
					sender = "example@"+get_local_ip()
					message_id = f"{random.getrandbits(64):016x}"
					token = f"{sender}|{now + ttl}|chat"

					message = {
						"TYPE": "DM",
						"FROM": sender,
						"TO": recipient,
						"CONTENT": content,
						"TIMESTAMP": now,
						"MESSAGE_ID": message_id,
						"TOKEN": token
					}

					print("\nCrafted Message:\n")
					print(craft_message(message))
					print("Parsed Message:\n")
					print(parse_message(craft_message(message)))
					print("\nSender:")
					logger.log_send(msg_type, get_local_ip(), message, peer_manager) # Note: this will cause errors in non-verbose mode since it does not store the peer
					print("\nReceiver:")
					logger.log_recv(msg_type, recipient.strip('@')[1], message, peer_manager)
				else:
					print("Unsupported message type for simulation.")
			
			elif cmd == "ttl":
				user_input = input("Set TTL: ").strip()
				if user_input.isdigit() and int(user_input) > 0:
					config.TTL = int(user_input)
					print(f"TTL set to {config.TTL}")
				else:
					print("TTL must be a positive integer")
			
			elif cmd == "help":
				print("Available commands:")
				print("  profile    - Set your user profile")
				print("  post       - Create a new post")
				print("  dm         - Send a direct message")
				print("  follow     - Follow another user")
				print("  unfollow   - Unfollow a user")
				print("  list       - Show known peers and following status")
				print("  show       - Show detailed peer information with posts and DMs")
				print("  tictactoe invite - invite a peer to a tic tac toe game")
				print("  tictactoe move   - make a move ")
				print("  verbose [on|off] - Toggle verbose logging")
				print("  ttl        - Set TTL")
				print("  exit       - Quit the application")
			
			elif cmd == "tictactoe invite":
				recipient = input("User ID (e.g. user@ip): ").strip()

				import time, random
				now = int(time.time())
				ttl = config.TTL
				sender = peer_manager.own_profile["USER_ID"]
				token = f"{sender}|{now + ttl}|game"
				game_id = str(uuid.uuid4())[:8]
				message_id = f"{random.getrandbits(64):016x}"
				symbol = "X"

				invite_message = {
					"TYPE": "TICTACTOE_INVITE",
					"FROM": sender,
					"RECIPIENT": recipient,
					"MESSAGE_ID": message_id,
					"GAMEID": game_id,
					"SYMBOL": symbol,
					"TIMESTAMP": now,
					"TOKEN": token
				}

				try:
					_, ip = recipient.split("@")
				except ValueError:
					print("Invalid recipient format. Use user@ip.")
					continue

				is_valid, error = validate_token(invite_message["TOKEN"], "game", peer_manager.revoked_tokens)
				if not is_valid:
					logger.log("REJECT", f"TICTACTOE_INVITE rejected: {error}")
					return

				peer_manager.create_game(game_id, recipient, is_host=True, token=token, my_symbol="X", opponent_symbol="O")
				send_message(invite_message, (ip, config.PORT))
				peer_manager.issued_tokens.append(token)
				print(f"Invitation sent to {recipient} with GAMEID {game_id}")

			elif cmd == "tictactoe move":
				game_id = input("GAMEID: ").strip()
				position_input = input("Position (0-8): ").strip()

				try:
					position = int(position_input)
					assert 0 <= position <= 8
				except:
					print("Invalid position. Must be an integer from 0 to 8.")
					continue
				
				import time, random
				now = int(time.time())
				ttl = config.TTL
				sender = peer_manager.own_profile["USER_ID"]
				token = f"{sender}|{now + ttl}|game"
				game = peer_manager.games.get(game_id)
				message_id = f"{random.getrandbits(64):016x}"

				if not game:
					print("No such game found.")
					continue

				if not game['my_turn']:
					print("It's not your turn!")
					continue

				move_message = {
					"TYPE": "TICTACTOE_MOVE",
					"FROM": sender,
					"RECIPIENT": game['opponent_id'],
					"GAMEID": game_id,
					"MESSAGE_ID": message_id,
					"TURN": game['turn'],
					"POSITION": position,
					"SYMBOL": game["symbol"],
					"TOKEN": token
				}

				_, ip = game['opponent_id'].split("@")

				is_valid, error = validate_token(move_message["TOKEN"], "game", peer_manager.revoked_tokens)
				if not is_valid:
					logger.log("REJECT", f"TICTACTOE_MOVE rejected: {error}")
					return

				peer_manager.apply_move(game_id, position, is_self=True)
				print_board(game["board"])
				send_message(move_message, (ip, config.PORT))
				peer_manager.issued_tokens.append(token)
				print(f"Move sent to {game['opponent_id']} at position {position}")

			else:
				print("Unknown command. Type 'help'.")

		except Exception as e:
			logger.log("SHELL ERROR", str(e))
