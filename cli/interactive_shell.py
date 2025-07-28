from utils.network_utils import send_message, get_local_ip
from core.peer import PeerManager
import json
import config

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

				own_profile = peer_manager.own_profile
				if not own_profile or "USER_ID" not in own_profile:
					print("Profile not set. Please set your profile first using the 'profile' command.")
					continue

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
					print("Direct message sent.")
				except ValueError:
					print("Invalid recipient format. Use user@ip.")

			# switching verbose/non-verbose mode
			elif cmd.startswith("verbose"):
				parts = cmd.split()
				if len(parts) == 2 and parts[1] in ["on", "off"]:
					logger.set_verbose(parts[1] == "on")
				else:
					print("Usage: verbose [on|off]")

			elif cmd == "help":
				print("Available commands:\n  profile\n  verbose [on|off]\n  post\n  dm\n  exit")

			else:
				print("Unknown command. Type 'help'.")

		except Exception as e:
			logger.log("SHELL ERROR", str(e))
