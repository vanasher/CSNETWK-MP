from network.udp_handler import UDPHandler
from parser.message_parser import parse_message
from utils.logger import Logger
from core.peer import PeerManager

if __name__ == "__main__":
    logger = Logger(verbose=True)
    peer_manager = PeerManager(logger)
    udp = UDPHandler(logger, peer_manager)
    udp.start()