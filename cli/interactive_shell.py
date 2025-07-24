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

				ip = get_local_ip()
				user_id = f"{username}@{ip}"

				peer_manager.set_own_profile(user_id, display_name, status)
				logger.log("SHELL", f"Profile set for {user_id} and will be broadcast periodically.")

			elif cmd.startswith("verbose"):
				parts = cmd.split()
				if len(parts) == 2 and parts[1] in ["on", "off"]:
					logger.set_verbose(parts[1] == "on")
				else:
					print("Usage: verbose [on|off]")

			elif cmd == "help":
				print("Available commands:\n  profile\n  verbose [on|off]\n  exit")

			else:
				print("Unknown command. Type 'help'.")

		except Exception as e:
			logger.log("SHELL ERROR", str(e))
