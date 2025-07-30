from utils.network_utils import send_message, get_local_ip
from core.peer import PeerManager
from utils.image_utils import encode_image_to_base64, get_supported_extensions, is_valid_image_file
import json
import config
from parser.message_parser import craft_message

def run_shell(logger, peer_manager):
	print("LSNP Interactive Shell. Type 'help' for commands.")

	while True:
		try:
			cmd = input(">>> ").strip()

			if cmd == "exit":
				print("Exiting...")
				break
			
			# 'profile' command to set own profile
			elif cmd == "profile":
				username = input("Username: ").strip()
				display_name = input("Display name: ").strip()
				status = input("Status: ").strip()
				
				# Ask for profile picture
				avatar_type = None
				avatar_encoding = None
				avatar_data = None
				
				use_avatar = input("Add profile picture? (y/n): ").strip().lower()
				if use_avatar in ['y', 'yes']:
					image_path = input("Enter path to image file: ").strip()
					if image_path:
						try:
							if not is_valid_image_file(image_path):
								print("Invalid image file or file not found.")
								supported = get_supported_extensions()
								print(f"Supported formats: {', '.join(supported)}")
							else:
								mime_type, base64_data, size_bytes = encode_image_to_base64(image_path)
								avatar_type = mime_type
								avatar_encoding = "base64"
								avatar_data = base64_data
								print(f"Profile picture added: {mime_type} ({size_bytes} bytes)")
						except Exception as e:
							print(f"Error processing image: {e}")

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

				ttl_input = input("TTL (in seconds, default 3600): ").strip()
				try:
					ttl = int(ttl_input) if ttl_input else 3600
					if ttl <= 0:
						raise ValueError
				except ValueError:
					print("Invalid TTL. Must be a positive integer.")
					continue

				import time, random
				now = int(time.time())

				user_id = own_profile["USER_ID"]
				message_id = f"{random.getrandbits(64):016x}"
				token = f"{user_id}|{now + ttl}|broadcast"

				post_message = {
					"TYPE": "POST",
					"USER_ID": user_id,
					"CONTENT": content,
					"TIMESTAMP": now,
					"TTL": ttl,
					"MESSAGE_ID": message_id,
					"TOKEN": token
				}

				# send only to followers
				follower_ips = peer_manager.get_follower_ips()
				for user_id, ip in follower_ips:
					send_message(post_message, (ip, config.PORT))
					logger.log_send("POST", ip, post_message)

			# 'dm' command to send a direct message to a peer
			elif cmd == "dm":
				recipient = input("Recipient (user_id@ip): ").strip()
				content = input("Message: ").strip()
				if not recipient or not content:
					print("Recipient and content cannot be empty.")
					continue

				import time, random
				now = int(time.time())
				ttl = 3600
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

				# Extract IP from recipient (format: user@ip)
				try:
					_, ip = recipient.split("@")
					send_message(dm_message, (ip, config.PORT))
					logger.log_send("DM", ip, dm_message, peer_manager)
				except ValueError:
					print("Invalid recipient format. Use user@ip.")

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
				token = f"{sender}|{now + 3600}|social"

				follow_message = {
					"TYPE": "FOLLOW",
					"FROM": sender,
					"TO": target_user,
					"MESSAGE_ID": message_id,
					"TIMESTAMP": now,
					"TOKEN": token
				}

				# Extract IP from target user (format: user@ip)
				try:
					_, ip = target_user.split("@")
					send_message(follow_message, (ip, config.PORT))
					
					# Add to local following list
					peer_manager.follow(target_user)
					print(f"Follow request sent to {target_user}.")
					logger.log_send("FOLLOW", ip, follow_message)
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
				token = f"{sender}|{now + 3600}|social"

				unfollow_message = {
					"TYPE": "UNFOLLOW",
					"FROM": sender,
					"TO": target_user,
					"MESSAGE_ID": message_id,
					"TIMESTAMP": now,
					"TOKEN": token
				}

				# Extract IP from target user (format: user@ip)
				try:
					_, ip = target_user.split("@")
					send_message(unfollow_message, (ip, config.PORT))
					
					# Remove from local following list
					peer_manager.following.discard(target_user)
					print(f"Unfollow request sent to {target_user}.")
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

			# 'like' command to like a post
			elif cmd == "like":
				if not peer_manager.own_profile or "USER_ID" not in peer_manager.own_profile:
					print("Profile not set. Please set your profile first using the 'profile' command.")
					continue
				
				post_timestamp = input("Enter post timestamp to like: ").strip()
				if not post_timestamp:
					print("Post timestamp cannot be empty.")
					continue
				
				# Find the post by timestamp and its author
				post_author = None
				post_found = False
				post_content = None
				
				for user_id, peer_info in peer_manager.peers.items():
					for post in peer_info.get('posts', []):
						if str(post.get('timestamp')) == post_timestamp:
							post_author = user_id
							post_found = True
							post_content = post.get('content', '')
							break
					if post_found:
						break
				
				if not post_found:
					print(f"Post with timestamp '{post_timestamp}' not found.")
					continue
				
				import time, random
				now = int(time.time())
				sender = peer_manager.own_profile["USER_ID"]
				token = f"{sender}|{now + 3600}|broadcast"
				
				like_message = {
					"TYPE": "LIKE",
					"FROM": sender,
					"TO": post_author,
					"POST_TIMESTAMP": post_timestamp,
					"ACTION": "LIKE",
					"TIMESTAMP": now,
					"TOKEN": token
				}
				
				# Send like to post author
				try:
					_, author_ip = post_author.split("@")
					send_message(like_message, (author_ip, config.PORT))
					print(f"Like sent for post at timestamp {post_timestamp}")
					logger.log_send("LIKE", author_ip, like_message)
				except ValueError:
					print("Invalid post author format.")

			# 'unlike' command to unlike a post
			elif cmd == "unlike":
				if not peer_manager.own_profile or "USER_ID" not in peer_manager.own_profile:
					print("Profile not set. Please set your profile first using the 'profile' command.")
					continue
				
				post_timestamp = input("Enter post timestamp to unlike: ").strip()
				if not post_timestamp:
					print("Post timestamp cannot be empty.")
					continue
				
				# Find the post by timestamp and its author
				post_author = None
				post_found = False
				post_content = None
				
				for user_id, peer_info in peer_manager.peers.items():
					for post in peer_info.get('posts', []):
						if str(post.get('timestamp')) == post_timestamp:
							post_author = user_id
							post_found = True
							post_content = post.get('content', '')
							break
					if post_found:
						break
				
				if not post_found:
					print(f"Post with timestamp '{post_timestamp}' not found.")
					continue
				
				import time, random
				now = int(time.time())
				sender = peer_manager.own_profile["USER_ID"]
				token = f"{sender}|{now + 3600}|broadcast"
				
				unlike_message = {
					"TYPE": "LIKE",
					"FROM": sender,
					"TO": post_author,
					"POST_TIMESTAMP": post_timestamp,
					"ACTION": "UNLIKE",
					"TIMESTAMP": now,
					"TOKEN": token
				}
				
				# Send unlike to post author
				try:
					_, author_ip = post_author.split("@")
					send_message(unlike_message, (author_ip, config.PORT))
					print(f"Unlike sent for post at timestamp {post_timestamp}")
					logger.log_send("LIKE", author_ip, unlike_message)
				except ValueError:
					print("Invalid post author format.")

			# switching verbose/non-verbose mode
			elif cmd.startswith("verbose"):
				parts = cmd.split()
				if len(parts) == 2 and parts[1] in ["on", "off"]:
					logger.set_verbose(parts[1] == "on")
				else:
					print("Usage: verbose [on|off]")

			elif cmd == "help":
				print("Available commands:")
				print("  profile    - Set your user profile (with optional profile picture)")
				print("  post       - Create a new post")
				print("  dm         - Send a direct message")
				print("  follow     - Follow another user")
				print("  unfollow   - Unfollow a user")
				print("  like       - Like a post by timestamp")
				print("  unlike     - Unlike a post by timestamp")
				print("  list       - Show known peers and following status")
				print("  show       - Show detailed peer information with posts and DMs")
				print("  verbose [on|off] - Toggle verbose logging")
				print("  exit       - Quit the application")

			else:
				print("Unknown command. Type 'help'.")

		except Exception as e:
			logger.log("SHELL ERROR", str(e))
