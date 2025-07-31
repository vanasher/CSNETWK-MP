import socket
import threading
from parser.message_parser import parse_message
import config
from utils.network_utils import get_broadcast_address

# sets up a UDP socket for LSNP communication.
# listens for incoming messages in a background thread, decodes, parses, logs, and dispatches them
class UDPHandler:
	def __init__(self, logger, peer_manager, dispatcher):
		self.logger = logger
		self.peer_manager = peer_manager
		self.dispatch = dispatcher
		self.running = True

		# set up UDP socket with broadcast capability
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
		self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.sock.bind(("", config.PORT)) # when testing on multiple terminals on the same device,
				                          # you have to change the port to a different one
	
	# start background listener thread
	def start(self):
		threading.Thread(target=self.listen, daemon=True).start()
		self.logger.log("UDPHandler", "Listening for messages...")

	# blocking loop to listen for incoming UDP packets
	# each message is parsed and dispatched
	def listen(self):
		own_ip = socket.gethostbyname(socket.gethostname())
		while self.running:
			try:
				data, addr = self.sock.recvfrom(65535) # 65535 -> maximum size of a UDP datagram
				# if addr[0] == own_ip: # skip messages from self
				# 	continue
				raw = data.decode("utf-8")
				message = parse_message(raw)
				self.logger.log_recv(message.get("TYPE", "UNKNOWN"), addr[0], message, self.peer_manager)
				self.dispatch(message, addr[0], self.peer_manager)
			except Exception as e:
				self.logger.log("ERROR", str(e))