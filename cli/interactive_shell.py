from utils.network_utils import send_message, get_local_ip
from core.peer import PeerManager
import json
import config
import time
import random
import string
from parser.message_parser import craft_message
from parser.message_parser import parse_message
from utils.network_utils import validate_token
from utils.game_utils import print_board
from utils.game_utils import check_game_result, send_result_message
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
				
				# Avatar support
				avatar_type = None
				avatar_encoding = None
				avatar_data = None
				
				avatar_choice = input("Do you want to set a profile picture? (y/n): ").strip().lower()
				if avatar_choice == 'y':
					avatar_path = input("Enter path to image file (or press Enter to skip): ").strip()
					if avatar_path:
						try:
							import base64
							import os
							import mimetypes
							
							if not os.path.exists(avatar_path):
								print("File not found. Skipping avatar.")
							else:
								# Check file size (limit to ~20KB as per spec)
								file_size = os.path.getsize(avatar_path)
								if file_size > 20480:  # 20KB
									print(f"File too large ({file_size} bytes). Avatar must be under 20KB. Skipping avatar.")
								else:
									# Determine MIME type
									mime_type, _ = mimetypes.guess_type(avatar_path)
									if not mime_type or not mime_type.startswith('image/'):
										print("Not a valid image file. Skipping avatar.")
									else:
										# Read and encode file
										with open(avatar_path, 'rb') as f:
											image_data = f.read()
										avatar_data = base64.b64encode(image_data).decode('utf-8')
										avatar_type = mime_type
										avatar_encoding = "base64"
										print(f"Avatar loaded: {mime_type}, {len(avatar_data)} characters")
						except Exception as e:
							print(f"Error loading avatar: {e}. Skipping avatar.")

				peer_manager.set_own_profile(username, display_name, status, avatar_type, avatar_encoding, avatar_data)
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
					"TIMESTAMP": now,
					"TOKEN": token
				}

				# check if token is valid
				is_valid, error = validate_token(post_message["TOKEN"], "broadcast", peer_manager.revoked_tokens)
				if not is_valid:
					logger.log("REJECT", f"POST rejected: {error}")
					return
				
				# Track our own post
				peer_manager.add_own_post(content, now, ttl, message_id, token)
				
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
						avatar_info = ""
						peer_info = peer_manager.peers.get(user_id)
						if peer_info and peer_info.get('avatar_type') and peer_info.get('avatar_data'):
							avatar_info = f" [Avatar: {peer_info.get('avatar_type')}]"
						print(f"  {display_name} ({user_id}){following_status}{avatar_info}")
				else:
					print("  No peers discovered yet.")
				
				print(f"\n--- Following ({len(peer_manager.following)}) ---")
				if peer_manager.following:
					for user_id in peer_manager.following:
						display_name = peer_manager.get_display_name(user_id)
						avatar_info = ""
						peer_info = peer_manager.peers.get(user_id)
						if peer_info and peer_info.get('avatar_type') and peer_info.get('avatar_data'):
							avatar_info = f" [Avatar: {peer_info.get('avatar_type')}]"
						print(f"  {display_name} ({user_id}){avatar_info}")
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
					
					# Avatar support for simulation
					avatar_type = None
					avatar_encoding = None
					avatar_data = None
					
					avatar_choice = input("Include test avatar? (y/n): ").strip().lower()
					if avatar_choice == 'y':
						avatar_path = input("Enter path to image file: ").strip()
						if avatar_path:
							try:
								import base64
								import os
								import mimetypes
								
								if os.path.exists(avatar_path):
									file_size = os.path.getsize(avatar_path)
									if file_size <= 20480:  # 20KB limit
										mime_type, _ = mimetypes.guess_type(avatar_path)
										if mime_type and mime_type.startswith('image/'):
											with open(avatar_path, 'rb') as f:
												image_data = f.read()
											avatar_data = base64.b64encode(image_data).decode('utf-8')
											avatar_type = mime_type
											avatar_encoding = "base64"
											print(f"Test avatar loaded: {mime_type}")
										else:
											print("Not a valid image file.")
									else:
										print("File too large (>20KB).")
								else:
									print("File not found.")
							except Exception as e:
								print(f"Error loading test avatar: {e}")

					user_id = f"{username}@{get_local_ip()}"
					message = {
						"TYPE": "PROFILE",
						"USER_ID": user_id,
						"DISPLAY_NAME": display_name,
						"STATUS": status,
						"AVATAR_TYPE": avatar_type,
						"AVATAR_ENCODING": avatar_encoding,
						"AVATAR_DATA": avatar_data,
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
				print("  profile    - Set your user profile (with optional avatar)")
				print("  post       - Create a new post")
				print("  dm         - Send a direct message")
				print("  follow     - Follow another user")
				print("  unfollow   - Unfollow a user")
				print("  list       - Show known peers and following status")
				print("  show       - Show detailed peer information with posts and DMs")
				print("  avatar     - Save a peer's avatar to file")
				print("  like       - Like or unlike a post")
				print("  tictactoe invite - invite a peer to a tic tac toe game")
				print("  tictactoe move   - make a move ")
				print("  groups     - Show all groups you belong to")
				print("  group create - Create a new group")
				print("  group update - Update group membership")
				print("  group message - Send message to a group")
				print("  group show - Show detailed group information")
				print("  verbose [on|off] - Toggle verbose logging")
				print("  ttl        - Set TTL")
				print("  exit       - Quit the application")
			
			elif cmd == "avatar":
				# Show available peers with avatars
				print("\n--- Peers with Profile Pictures ---")
				peers_with_avatars = []
				for user_id, peer_info in peer_manager.peers.items():
					if peer_info.get('avatar_type') and peer_info.get('avatar_data'):
						display_name = peer_info.get('display_name', 'Unknown')
						avatar_type = peer_info.get('avatar_type')
						avatar_size = len(peer_info.get('avatar_data', ''))
						peers_with_avatars.append((user_id, display_name, avatar_type, avatar_size))
						print(f"  {display_name} ({user_id}) - {avatar_type}")
				
				if not peers_with_avatars:
					print("  No peers with profile pictures found.")
				else:
					target_user = input("\nEnter user ID to save avatar: ").strip()
					peer_info = peer_manager.peers.get(target_user)
					
					if not peer_info:
						print("Peer not found.")
					elif not peer_info.get('avatar_data'):
						print("This peer has no profile picture.")
					else:
						try:
							import base64
							import os
							
							avatar_data = peer_info.get('avatar_data')
							avatar_type = peer_info.get('avatar_type', 'image/png')
							
							# Determine file extension from MIME type
							extension = '.png'  # default
							if 'jpeg' in avatar_type or 'jpg' in avatar_type:
								extension = '.jpg'
							elif 'gif' in avatar_type:
								extension = '.gif'
							elif 'bmp' in avatar_type:
								extension = '.bmp'
							
							# Create filename
							username = target_user.split('@')[0]
							filename = f"avatar_{username}{extension}"
							
							# Decode and save
							image_bytes = base64.b64decode(avatar_data)
							with open(filename, 'wb') as f:
								f.write(image_bytes)
							
							print(f"Avatar saved as '{filename}' ({len(image_bytes)} bytes)")
							
						except Exception as e:
							print(f"Error saving avatar: {e}")
			
			elif cmd == "like":
				# Show all posts from followed users first
				print("\n=== POSTS FROM FOLLOWED USERS ===")
				posts_found = False
				for user_id in peer_manager.following:
					peer_info = peer_manager.peers.get(user_id)
					if peer_info and peer_info.get('posts'):
						posts = peer_info['posts']
						display_name = peer_info['display_name']
						print(f"\nPosts from {display_name} ({user_id}):")
						for i, post in enumerate(posts, 1):
							# Check if post is still valid
							is_valid, error = validate_token(post.get("token"), "broadcast", peer_manager.revoked_tokens)
							if is_valid:
								content = post.get('content', 'No content')
								timestamp = post.get('timestamp', 'N/A')
								print(f"  {i}. {content}")
								print(f"     Timestamp: {timestamp}")
								posts_found = True
				
				if not posts_found:
					print("No posts available from followed users.")
					continue
				
				# Get input for like action
				target_user = input("\nEnter the user ID of the post author: ").strip()
				if not target_user:
					print("User ID cannot be empty.")
					continue
				
				if target_user not in peer_manager.following:
					print(f"You are not following {target_user}. You can only like posts from users you follow.")
					continue
				
				try:
					post_timestamp = int(input("Enter the post timestamp: ").strip())
				except ValueError:
					print("Invalid timestamp. Must be a number.")
					continue
				
				action = input("Action (LIKE/UNLIKE): ").strip().upper()
				if action not in ["LIKE", "UNLIKE"]:
					print("Action must be either LIKE or UNLIKE.")
					continue
				
				# Validate that the post exists
				peer_info = peer_manager.peers.get(target_user)
				if not peer_info:
					print(f"Peer '{target_user}' not found.")
					continue
				
				posts = peer_info.get('posts', [])
				post_found = False
				target_post_content = ""
				for post in posts:
					if post.get('timestamp') == post_timestamp:
						is_valid, error = validate_token(post.get("token"), "broadcast", peer_manager.revoked_tokens)
						if is_valid:
							post_found = True
							target_post_content = post.get('content', '')
							break
				
				if not post_found:
					print(f"Post with timestamp {post_timestamp} not found for user {target_user}.")
					continue
				
				# Create and send the like message
				import time, random
				now = int(time.time())
				ttl = config.TTL
				sender = peer_manager.own_profile["USER_ID"]
				token = f"{sender}|{now + ttl}|broadcast"
				
				like_message = {
					"TYPE": "LIKE",
					"FROM": sender,
					"TO": target_user,
					"POST_TIMESTAMP": post_timestamp,
					"ACTION": action,
					"TIMESTAMP": now,
					"TOKEN": token
				}
				
				# Validate token
				is_valid, error = validate_token(like_message["TOKEN"], "broadcast", peer_manager.revoked_tokens)
				if not is_valid:
					logger.log("REJECT", f"LIKE rejected: {error}")
					continue
				
				# Extract IP from target user
				try:
					_, ip = target_user.split("@")
					send_message(like_message, (ip, config.PORT))
					peer_manager.issued_tokens.append(token)
					logger.log_send("LIKE", ip, like_message, peer_manager)
					
					# Store the like locally for tracking
					peer_manager.add_like(target_user, post_timestamp, action, target_post_content)
					
				except ValueError:
					print("Invalid user ID format. Expected user@ip.")
				except Exception as e:
					print(f"Failed to send like: {e}")
			
			elif cmd == "tictactoe invite":
				recipient = input("User ID (e.g. user@ip): ").strip()

				import time, random
				now = int(time.time())
				ttl = config.TTL
				sender = peer_manager.own_profile["USER_ID"]
				token = f"{sender}|{now + ttl}|game"
				game_id = f"g{random.randint(0, 255)}"
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

				peer_manager.create_game(game_id, recipient, is_initiator=True, token=token, my_symbol="X", opponent_symbol="O")
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
				
				# check if position is already taken
				board = peer_manager.games[game_id]["board"]
				if board[position] != " ":
					print("Invalid move. That position is already occupied.")
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

				result, winning_line = check_game_result(game["board"])
				if result:
					import time, random
					now = int(time.time())
					ttl = config.TTL
					token = f"{sender}|{now + ttl}|game"
					my_user_id = peer_manager.own_profile["USER_ID"]
					send_result_message(
						peer_manager,
						token,
						game_id,
						result,
						game["opponent_id"],
						winner_id=my_user_id if result == "WIN" else None,
						winning_symbol=game["symbol"] if result == "WIN" else None,
						winning_line=winning_line
					)
			# ===== GROUP COMMANDS =====
			elif cmd == "groups":
				groups = peer_manager.list_groups()
				if not groups:
					print("You are not a member of any groups.")
				else:
					print(f"\nYour groups ({len(groups)}):")
					for group_id, group_name, member_count in groups:
						print(f"  {group_name} ({group_id}) - {member_count} members")

			elif cmd == "group create":
				if not peer_manager.own_profile:
					print("Profile not set. Please set your profile first using the 'profile' command.")
					continue

				# Automatically generate random case-sensitive group ID
				import random
				chars = string.ascii_letters + string.digits
				group_id = ''.join(random.choice(chars) for _ in range(8))
				print(f"Generated Group ID: {group_id}")

				group_name = input("Group name: ").strip()
				if not group_name:
					print("Group name cannot be empty.")
					continue

				members_input = input("Members (comma-separated user@ip): ").strip()
				if not members_input:
					print("At least one member must be specified.")
					continue

				members = [m.strip() for m in members_input.split(",") if m.strip()]
				
				# Add creator to members if not already included
				creator_id = peer_manager.own_profile["USER_ID"]
				if creator_id not in members:
					members.append(creator_id)

				try:
					message = peer_manager.create_group(group_id, group_name, members)
					
					# Validate token
					is_valid, error = validate_token(message["TOKEN"], "group", peer_manager.revoked_tokens)
					if not is_valid:
						print(f"Failed to create group: {error}")
						continue

					# Send to all members
					member_ips = peer_manager.get_group_member_ips(group_id)
					for ip in member_ips:
						send_message(message, (ip, config.PORT))
					
					peer_manager.issued_tokens.append(message["TOKEN"])
					logger.log_send("GROUP_CREATE", get_local_ip(), message)

				except Exception as e:
					print(f"Failed to create group: {e}")

			elif cmd == "group update":
				if not peer_manager.own_profile:
					print("Profile not set. Please set your profile first using the 'profile' command.")
					continue

				# Show available groups
				groups = peer_manager.list_groups()
				if not groups:
					print("You are not a member of any groups.")
					continue

				print("Available groups:")
				for group_id, group_name, member_count in groups:
					print(f"  {group_id} - {group_name}")

				group_id = input("Group ID to update: ").strip()
				if group_id not in peer_manager.groups:
					print("Group not found.")
					continue

				add_members_input = input("Add members (comma-separated user@ip, or press Enter to skip): ").strip()
				remove_members_input = input("Remove members (comma-separated user@ip, or press Enter to skip): ").strip()

				if not add_members_input and not remove_members_input:
					print("No changes specified.")
					continue

				add_members = [m.strip() for m in add_members_input.split(",") if m.strip()] if add_members_input else None
				remove_members = [m.strip() for m in remove_members_input.split(",") if m.strip()] if remove_members_input else None

				try:
					message = peer_manager.update_group(group_id, add_members, remove_members)
					
					# Validate token
					is_valid, error = validate_token(message["TOKEN"], "group", peer_manager.revoked_tokens)
					if not is_valid:
						print(f"Failed to update group: {error}")
						continue

					# Send to all current members
					member_ips = peer_manager.get_group_member_ips(group_id)
					for ip in member_ips:
						send_message(message, (ip, config.PORT))
					
					peer_manager.issued_tokens.append(message["TOKEN"])
					logger.log_send("GROUP_UPDATE", get_local_ip(), message)
					
					# Success message
					success_parts = []
					if add_members:
						success_parts.append(f"Added: {', '.join(add_members)}")
					if remove_members:
						success_parts.append(f"Removed: {', '.join(remove_members)}")
					print(f"Group '{group_id}' updated successfully. {'; '.join(success_parts)}")

				except Exception as e:
					print(f"Failed to update group: {e}")

			elif cmd == "group message":
				if not peer_manager.own_profile:
					print("Profile not set. Please set your profile first using the 'profile' command.")
					continue

				# Show available groups
				groups = peer_manager.list_groups()
				if not groups:
					print("You are not a member of any groups.")
					continue

				print("Available groups:")
				for group_id, group_name, member_count in groups:
					print(f"  {group_id} - {group_name}")

				group_id = input("Group ID: ").strip()
				if group_id not in peer_manager.groups:
					print("Group not found.")
					continue

				content = input("Message: ").strip()
				if not content:
					print("Message cannot be empty.")
					continue

				try:
					message = peer_manager.send_group_message(group_id, content)
					
					# Validate token
					is_valid, error = validate_token(message["TOKEN"], "group", peer_manager.revoked_tokens)
					if not is_valid:
						print(f"Failed to send group message: {error}")
						continue

					# Send to all group members
					member_ips = peer_manager.get_group_member_ips(group_id)
					for ip in member_ips:
						send_message(message, (ip, config.PORT))
					
					peer_manager.issued_tokens.append(message["TOKEN"])
					logger.log_send("GROUP_MESSAGE", get_local_ip(), message)

				except Exception as e:
					print(f"Failed to send group message: {e}")

			elif cmd == "group show":
				# Show available groups
				groups = peer_manager.list_groups()
				if not groups:
					print("You are not a member of any groups.")
					continue

				print("Available groups:")
				for group_id, group_name, member_count in groups:
					print(f"  {group_id} - {group_name}")

				group_id = input("Group ID to show: ").strip()
				group_details = peer_manager.get_group_details(group_id)
				
				if not group_details:
					print("Group not found.")
					continue

				print(f"\n=== GROUP DETAILS: {group_details['name']} ===")
				print(f"ID: {group_details['id']}")
				print(f"Creator: {group_details['creator']}")
				print(f"Created: {group_details['created']}")
				print(f"Members ({len(group_details['members'])}):")
				for member in group_details['members']:
					print(f"  {member}")
				
				if group_details['messages']:
					print(f"\nRecent messages ({len(group_details['messages'])}):")
					for msg in group_details['messages'][-10:]:  # Show last 10 messages
						import datetime
						timestamp = datetime.datetime.fromtimestamp(msg['timestamp']).strftime("%H:%M:%S")
						print(f"  [{timestamp}] {msg['from']}: {msg['content']}")
				else:
					print("\nNo messages yet.")

			else:
				print("Unknown command. Type 'help'.")

		except Exception as e:
			logger.log("SHELL ERROR", str(e))
