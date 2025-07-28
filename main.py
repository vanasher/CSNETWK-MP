import argparse
from network.udp_handler import UDPHandler
from parser.message_parser import parse_message
from utils.logger import Logger
from core.peer import PeerManager
from core.message_dispatcher import dispatch
from cli.interactive_shell import run_shell
from core.broadcaster import broadcast_profile_periodically

if __name__ == "__main__":
	
	logger = Logger(verbose=True)
	peer_manager = PeerManager(logger)
	udp = UDPHandler(logger, peer_manager, dispatch)
	udp.start()

	broadcast_profile_periodically(logger, peer_manager)
	# start interactive shell
	try:
		run_shell(logger, peer_manager)
	except KeyboardInterrupt:
		print("\nShutting down...")