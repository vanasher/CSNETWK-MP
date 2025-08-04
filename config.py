from utils.network_utils import get_broadcast_address
from utils.network_utils import get_manual_broadcast

PORT = 50999
BROADCAST_ADDR = get_manual_broadcast()
VERBOSE = True
TTL = 3600 # default is 3600