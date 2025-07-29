# LSNP Protocol Test CLI - Complete implementation for protocol compliance testing
# Useful for isolated protocol validation and testing all message types

import argparse
import json
import time
import random
import sys
import os

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.network_utils import send_message
from utils.logger import Logger

def craft_profile(args):
	"""Craft a PROFILE message"""
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

def craft_post(args):
	"""Craft a POST message"""
	msg = {
		"TYPE": "POST",
		"USER_ID": args.user_id,
		"CONTENT": args.content,
		"TTL": str(args.ttl),
		"MESSAGE_ID": args.message_id if args.message_id else f"{random.getrandbits(64):016x}",
		"TOKEN": args.token if args.token else f"{args.user_id}|{int(time.time()) + args.ttl}|broadcast"
	}
	return msg

def craft_dm(args):
	"""Craft a DM message"""
	timestamp = int(time.time())
	msg = {
		"TYPE": "DM",
		"FROM": args.from_user,
		"TO": args.to_user,
		"CONTENT": args.content,
		"TIMESTAMP": str(timestamp),  
		"MESSAGE_ID": args.message_id if args.message_id else f"{random.getrandbits(64):016x}",
		"TOKEN": args.token if args.token else f"{args.from_user}|{timestamp + 3600}|chat"
	}
	return msg

def craft_follow(args):
	"""Craft a FOLLOW message"""
	timestamp = int(time.time())
	msg = {
		"TYPE": "FOLLOW",
		"FROM": args.from_user,
		"TO": args.to_user,
		"MESSAGE_ID": args.message_id if args.message_id else f"{random.getrandbits(64):016x}",
		"TIMESTAMP": str(timestamp),
		"TOKEN": args.token if args.token else f"{args.from_user}|{timestamp + 3600}|social"
	}
	return msg

def craft_unfollow(args):
	"""Craft an UNFOLLOW message"""
	timestamp = int(time.time())
	msg = {
		"TYPE": "UNFOLLOW",
		"FROM": args.from_user,
		"TO": args.to_user,
		"MESSAGE_ID": args.message_id if args.message_id else f"{random.getrandbits(64):016x}",
		"TIMESTAMP": str(timestamp),
		"TOKEN": args.token if args.token else f"{args.from_user}|{timestamp + 3600}|social"
	}
	return msg

def craft_ping(args):
	"""Craft a PING message"""
	msg = {
		"TYPE": "PING",
		"USER_ID": args.user_id
	}
	return msg

def craft_ack(args):
	"""Craft an ACK message"""
	msg = {
		"TYPE": "ACK",
		"MESSAGE_ID": args.message_id,
		"STATUS": args.status
	}
	return msg

def simulate_message_flow(args):
	"""Simulate a basic message flow for testing"""
	logger = Logger(verbose=args.verbose)
	
	if args.simulation == "profile_discovery":
		profile_msg = {
			"TYPE": "PROFILE",
			"USER_ID": "test_user@192.168.1.100",
			"DISPLAY_NAME": "Test User",
			"STATUS": "Testing protocol"
		}
		logger.log("SIMULATION", "Profile Discovery Test")
		if args.verbose:
			logger.log_send("PROFILE", "broadcast", json.dumps(profile_msg, indent=2))
		
	elif args.simulation == "post_flow":
		post_msg = {
			"TYPE": "POST",
			"USER_ID": "alice@192.168.1.100",
			"CONTENT": "Test post content",
			"TTL": "3600",
			"MESSAGE_ID": f"{random.getrandbits(64):016x}",
			"TOKEN": f"alice@192.168.1.100|{int(time.time()) + 3600}|broadcast"
		}
		logger.log("SIMULATION", "Post Flow Test")
		if args.verbose:
			logger.log_send("POST", "followers", json.dumps(post_msg, indent=2))
		
	elif args.simulation == "dm_exchange":
		timestamp = int(time.time())
		dm_msg = {
			"TYPE": "DM",
			"FROM": "alice@192.168.1.100",
			"TO": "bob@192.168.1.101",
			"CONTENT": "Test direct message",
			"TIMESTAMP": str(timestamp),
			"MESSAGE_ID": f"{random.getrandbits(64):016x}",
			"TOKEN": f"alice@192.168.1.100|{timestamp + 3600}|chat"
		}
		
		logger.log("SIMULATION", "DM Exchange Test")
		if args.verbose:
			logger.log_send("DM", "bob@192.168.1.101", json.dumps(dm_msg, indent=2))

def main():
	parser = argparse.ArgumentParser(description="LSNP Protocol Test CLI - Complete Implementation")
	parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
	subparsers = parser.add_subparsers(dest="command", help="Available commands")

	# PROFILE command
	profile_parser = subparsers.add_parser("profile", help="Send a PROFILE message")
	profile_parser.add_argument("--user-id", required=True, help="User ID (username@ip)")
	profile_parser.add_argument("--display-name", required=True, help="Display name")
	profile_parser.add_argument("--status", required=True, help="Status message")
	profile_parser.add_argument("--avatar-type", help="Avatar MIME type")
	profile_parser.add_argument("--avatar-data", help="Base64 encoded avatar data")
	profile_parser.add_argument("--send-to", help="Target address (ip:port)")

	# POST command
	post_parser = subparsers.add_parser("post", help="Send a POST message")
	post_parser.add_argument("--user-id", required=True, help="User ID (username@ip)")
	post_parser.add_argument("--content", required=True, help="Post content")
	post_parser.add_argument("--ttl", type=int, default=3600, help="Time to live in seconds")
	post_parser.add_argument("--message-id", help="Message ID (auto-generated if not provided)")
	post_parser.add_argument("--token", help="Authentication token (auto-generated if not provided)")
	post_parser.add_argument("--send-to", help="Target address (ip:port)")

	# DM command
	dm_parser = subparsers.add_parser("dm", help="Send a DM message")
	dm_parser.add_argument("--from-user", required=True, help="Sender user ID")
	dm_parser.add_argument("--to-user", required=True, help="Recipient user ID")
	dm_parser.add_argument("--content", required=True, help="Message content")
	dm_parser.add_argument("--message-id", help="Message ID (auto-generated if not provided)")
	dm_parser.add_argument("--token", help="Authentication token (auto-generated if not provided)")
	dm_parser.add_argument("--send-to", help="Target address (ip:port)")

	# FOLLOW command
	follow_parser = subparsers.add_parser("follow", help="Send a FOLLOW message")
	follow_parser.add_argument("--from-user", required=True, help="Follower user ID")
	follow_parser.add_argument("--to-user", required=True, help="User to follow")
	follow_parser.add_argument("--message-id", help="Message ID (auto-generated if not provided)")
	follow_parser.add_argument("--token", help="Authentication token (auto-generated if not provided)")
	follow_parser.add_argument("--send-to", help="Target address (ip:port)")

	# UNFOLLOW command
	unfollow_parser = subparsers.add_parser("unfollow", help="Send an UNFOLLOW message")
	unfollow_parser.add_argument("--from-user", required=True, help="Unfollower user ID")
	unfollow_parser.add_argument("--to-user", required=True, help="User to unfollow")
	unfollow_parser.add_argument("--message-id", help="Message ID (auto-generated if not provided)")
	unfollow_parser.add_argument("--token", help="Authentication token (auto-generated if not provided)")
	unfollow_parser.add_argument("--send-to", help="Target address (ip:port)")

	# PING command
	ping_parser = subparsers.add_parser("ping", help="Send a PING message")
	ping_parser.add_argument("--user-id", required=True, help="User ID (username@ip)")
	ping_parser.add_argument("--send-to", help="Target address (ip:port)")

	# ACK command
	ack_parser = subparsers.add_parser("ack", help="Send an ACK message")
	ack_parser.add_argument("--message-id", required=True, help="Message ID to acknowledge")
	ack_parser.add_argument("--status", default="RECEIVED", help="ACK status")
	ack_parser.add_argument("--send-to", help="Target address (ip:port)")

	# SIMULATE command
	simulate_parser = subparsers.add_parser("simulate", help="Simulate message flows for testing")
	simulate_parser.add_argument("--simulation", required=True, 
								choices=["profile_discovery", "post_flow", "dm_exchange"],
								help="Type of simulation to run")

	args = parser.parse_args()
	
	if not args.command:
		parser.print_help()
		return
	
	logger = Logger(verbose=args.verbose)

	# Message crafting functions mapping
	craft_functions = {
		"profile": craft_profile,
		"post": craft_post,
		"dm": craft_dm,
		"follow": craft_follow,
		"unfollow": craft_unfollow,
		"ping": craft_ping,
		"ack": craft_ack
	}

	if args.command == "simulate":
		simulate_message_flow(args)
		return

	# Craft the message
	if args.command in craft_functions:
		try:
			msg = craft_functions[args.command](args)
			
			# Display message based on verbosity
			if args.verbose:
				logger.log_send(msg["TYPE"], getattr(args, 'send_to', None) or "N/A", 
							   json.dumps(msg, indent=2))
			else:
				if msg["TYPE"] == "PROFILE":
					print(f"{msg['DISPLAY_NAME']}: {msg['STATUS']}")
				elif msg["TYPE"] == "POST":
					print(f"POST by {msg['USER_ID']}: {msg['CONTENT']}")
				elif msg["TYPE"] == "DM":
					print(f"DM from {msg['FROM']} to {msg['TO']}: {msg['CONTENT']}")
				elif msg["TYPE"] in ["FOLLOW", "UNFOLLOW"]:
					print(f"{msg['TYPE']} from {msg['FROM']} to {msg['TO']}")
				elif msg["TYPE"] == "PING":
					print(f"PING from {msg['USER_ID']}")
				elif msg["TYPE"] == "ACK":
					print(f"ACK for message {msg['MESSAGE_ID']}: {msg['STATUS']}")
			
			# Send message if address provided
			send_to = getattr(args, 'send_to', None)
			if send_to:
				try:
					ip, port = send_to.split(":")
					send_message(msg, (ip, int(port)))
					logger.log("SENT", f"Message sent to {send_to}")
				except ValueError:
					logger.log("ERROR", "Invalid address format. Use ip:port")
				except Exception as e:
					logger.log("ERROR", f"Failed to send message: {str(e)}")
			else:
				logger.log("INFO", "No --send-to provided; message crafted but not sent.")
				
		except Exception as e:
			logger.log("ERROR", f"Failed to craft {args.command} message: {str(e)}")
	else:
		logger.log("ERROR", f"Unknown command: {args.command}")

if __name__ == "__main__":
	main()