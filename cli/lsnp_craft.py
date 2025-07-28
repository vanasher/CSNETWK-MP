# do not think this file will be used anymore

#just testing a CLI for the LSNP protocol for now

# tool for crafting and sending LSNP messages manually for testing compliance
# useful for isolated protocol validation. Not meant to replace peer behavior.
import argparse
import json
from utils.network_utils import send_message
from utils.logger import Logger

def craft_profile(args):
	msg = {
		"TYPE": "PROFILE",
		"USER_ID": args.user_id,
		"DISPLAY_NAME": args.display_name,
		"STATUS": args.status
	}
	if args.avatar_type and args.avatar_data:
		msg["AVATAR_TYPE"] = args.avatar_type
		msg["AVATAR_ENCODING"] = "base64"
		msg["AVATAR_DATA"] = args.avatar_data
	return msg

# Additional crafting functions: craft_post, craft_follow, etc.

def main():
	parser = argparse.ArgumentParser(description="LSNP Protocol Test CLI")
	subparsers = parser.add_subparsers(dest="command")

	# PROFILE command
	profile_parser = subparsers.add_parser("profile", help="Send a PROFILE message")
	profile_parser.add_argument("--user-id", required=True)
	profile_parser.add_argument("--display-name", required=True)
	profile_parser.add_argument("--status", required=True)
	profile_parser.add_argument("--avatar-type")
	profile_parser.add_argument("--avatar-data")
	profile_parser.add_argument("--send-to")  # Format: ip:port
	profile_parser.add_argument("--verbose", action="store_true")

	args = parser.parse_args()
	
	logger = Logger(verbose=args.verbose)

	if args.command == "profile":
		msg = craft_profile(args)
		if args.verbose:
			logger.log_send(msg["TYPE"], args.send_to if args.send_to else "N/A", json.dumps(msg, indent=2))
		else:
			print(f"{msg['DISPLAY_NAME']}: {msg['STATUS']}")
		if args.send_to:
			ip, port = args.send_to.split(":")
			send_message(msg, (ip, int(port)))
		else:
			logger.log_drop("No --send-to provided; message not sent.")

if __name__ == "__main__":
	main()