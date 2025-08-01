import datetime
from parser.message_parser import craft_message

# logger class that supports verbose mode
class Logger:
	def __init__(self, verbose):
		self.verbose = verbose

	# def set_verbose(self, verbose):
	# 	"""Toggle verbose mode on/off"""
	# 	self.verbose = verbose
	# 	mode = "enabled" if verbose else "disabled"
	# 	print(f"Verbose logging {mode}.")

	def log(self, tag, message):
		if self.verbose:
			now = datetime.datetime.now().strftime("%H:%M:%S")
			print(f"\n[{now}] \n[{tag}] \n{message}")
		else:
			print(f"\n{message}")

	def log_send(self, msg_type, ip, msg=None, peer_manager=None):
		if self.verbose:
			if msg:
				if isinstance(msg, dict):
					lsnp_text = craft_message(msg)
					self.log("SEND >", lsnp_text)

		# non-verbose mode (sending messages)
		else:
			if msg_type == "PROFILE":
				print(f"\n\nBroadcasting profile...")

			elif msg_type == "POST":
				print(f"\n\nSuccessfully created post.")

			elif msg_type == "DM":
				to_user_id = msg.get("TO")
				if peer_manager:
					display_name = peer_manager.get_display_name(to_user_id)
					print(f"\n\nSent message to {display_name}")

			elif msg_type == "FOLLOW":
				to_user_id = msg.get("TO")
				if peer_manager:
					display_name = peer_manager.get_display_name(to_user_id)
					print(f"\n\nYou are now following {display_name}")

			elif msg_type == "UNFOLLOW":
				to_user_id = msg.get("TO")
				if peer_manager:
					display_name = peer_manager.get_display_name(to_user_id)
					print(f"\n\nYou have unfollowed {display_name}")

	def log_recv(self, msg_type, ip, msg=None, peer_manager=None):
		#self.log("RECV <", f"From {ip} | TYPE: {msg_type}")
		if self.verbose:
			if msg:
				# if msg is a dict (parsed message), convert to LSNP text
				if isinstance(msg, dict):
					lsnp_text = craft_message(msg)
					self.log("RECV <", lsnp_text)
				else:
					self.log("RECV <", msg)

		# non-verbose mode (receving messages)
		else:
			if msg.get("TYPE") == "PROFILE":
				print(f"\n\nName: {msg.get('DISPLAY_NAME', 'Unknown')} | Status: {msg.get('STATUS', 'N/A')}")

			if msg.get("TYPE") == "POST":
				user_id = msg.get("USER_ID")
				if peer_manager:
					display_name = peer_manager.get_display_name(user_id)
					print(f"\n\nNew post from {display_name}: \n{msg.get('CONTENT', 'No content')}")

			if msg.get("TYPE") == "DM":
				user_id = msg.get("FROM")
				if peer_manager:
					display_name = peer_manager.get_display_name(user_id)
					print(f"\n\nFrom {display_name}: \n{msg.get('CONTENT', 'No content')}")
			
			if msg.get("TYPE") == "FOLLOW":
				user_id = msg.get("FROM")
				if peer_manager:
					display_name = peer_manager.get_display_name(user_id)
					print(f"\n\nUser {display_name} has followed you")
			
			if msg.get("TYPE") == "UNFOLLOW":
				user_id = msg.get("FROM")
				if peer_manager:
					display_name = peer_manager.get_display_name(user_id)
					print(f"\n\nUser {display_name} has unfollowed you")

	def log_token(self, valid, reason=""):
		status = "✅ VALID" if valid else f"❌ INVALID: {reason}"
		self.log("TOKEN", status)

	def log_ack(self, msg_id):
		self.log("ACK", f"Received ACK for message ID: {msg_id}")

	def log_drop(self, reason=""):
		self.log("DROP !", reason)

	def log_retry(self, attempt, context=""):
		self.log("RETRY", f"Attempt {attempt} {context}")

	def set_verbose(self, state: bool):
		self.verbose = state
		print(f"\nVerbose mode {'enabled' if state else 'disabled'}.")