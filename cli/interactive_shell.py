from utils.network_utils import send_message, get_local_ip
from core.peer import PeerManager
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

			# switching verbose/non-verbose mode
			elif cmd.startswith("verbose"):
				parts = cmd.split()
				if len(parts) == 2 and parts[1] in ["on", "off"]:
					logger.set_verbose(parts[1] == "on")
				else:
					print("Usage: verbose [on|off]")

			elif cmd == "help":
				print("Available commands:")
				print("  profile    - Set your user profile")
				print("  post       - Create a new post")
				print("  dm         - Send a direct message")
				print("  follow     - Follow another user")
				print("  unfollow   - Unfollow a user")
				print("  list       - Show known peers and following status")
				print("  verbose [on|off] - Toggle verbose logging")
				print("  exit       - Quit the application")

			else:
				print("Unknown command. Type 'help'.")

		except Exception as e:
			logger.log("SHELL ERROR", str(e))
