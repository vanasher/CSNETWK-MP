from utils.network_utils import send_message, get_local_ip
from core.peer import PeerManager
import json
import config
import time
import random
from parser.message_parser import craft_message
from parser.message_parser import parse_message
from utils.network_utils import validate_token

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
				print("  groups     - Show all groups you belong to")
				print("  group_create - Create a new group")
				print("  group_update - Update group membership")
				print("  group_message - Send message to a group")
				print("  group_show - Show detailed group information")
				print("  verbose [on|off] - Toggle verbose logging")
				print("  ttl        - Set TTL")
				print("  exit       - Quit the application")

			# ===== GROUP COMMANDS =====
			elif cmd == "groups":
				groups = peer_manager.list_groups()
				if not groups:
					print("You are not a member of any groups.")
				else:
					print(f"\nYour groups ({len(groups)}):")
					for group_id, group_name, member_count in groups:
						print(f"  {group_name} ({group_id}) - {member_count} members")

			elif cmd == "group_create":
				if not peer_manager.own_profile:
					print("Profile not set. Please set your profile first using the 'profile' command.")
					continue

				group_id = input("Group ID: ").strip()
				if not group_id:
					print("Group ID cannot be empty.")
					continue

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

			elif cmd == "group_update":
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

				except Exception as e:
					print(f"Failed to update group: {e}")

			elif cmd == "group_message":
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

			elif cmd == "group_show":
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
