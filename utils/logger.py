import datetime
from parser.message_parser import craft_message

# logger class that supports verbose mode
class Logger:
	def __init__(self, verbose=False):
		self.verbose = verbose

	def log(self, tag, message):
		if self.verbose:
			now = datetime.datetime.now().strftime("%H:%M:%S")
			print(f"\n[{now}] \n[{tag}] \n{message}")
			
	def log_send(self, msg_type, ip, msg=None):
		if msg_type != "PROFILE":
			self.log("SEND >", f"To {ip} | TYPE: {msg_type}")
		if msg:
			self.log("SEND >", msg)

	def log_recv(self, msg_type, ip, msg=None):
		self.log("RECV <", f"From {ip} | TYPE: {msg_type}")
		if msg:
			# if msg is a dict (parsed message), convert to LSNP text
			if isinstance(msg, dict):
				lsnp_text = craft_message(msg)
				self.log("RECV <", lsnp_text.strip())
			else:
				self.log("RECV <", msg)

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
		self.log("LOGGER", f"Verbose mode {'enabled' if state else 'disabled'}.")
		self.verbose = state