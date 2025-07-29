import socket
from parser.message_parser import craft_message
import ipaddress
import psutil

def send_message(msg_dict, addr, udp_socket=None):
	if udp_socket is None:
		udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	msg_text = craft_message(msg_dict)
	udp_socket.sendto(msg_text.encode('utf-8'), addr)

# def get_local_ip():
#     # This tries to connect to an external host, but doesn't actually send data,
#     # just to get the outbound interface IP address.
#     s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#     try:
#         # This IP is arbitrary; 8.8.8.8 is Google DNS
#         s.connect(('8.8.8.8', 80))
#         ip = s.getsockname()[0]
#     except Exception:
#         ip = '127.0.0.1'
#     finally:
#         s.close()
#     return ip

def get_local_ip():
	import socket
	hostname = socket.gethostname()
	IPAddr = socket.gethostbyname(hostname)
	return IPAddr

# # Get the broadcast address for the local network.
# def get_broadcast_address():
#     for iface, addrs in psutil.net_if_addrs().items():
#         for addr in addrs:
#             if addr.family == socket.AF_INET and not addr.address.startswith("127."):
#                 ip = addr.address
#                 netmask = addr.netmask
#                 interface = ipaddress.IPv4Interface(f"{ip}/{netmask}")
#                 return str(interface.network.broadcast_address)
#     return "255.255.255.255"  # fallback


def get_broadcast_address():
	for iface_name, addrs in psutil.net_if_addrs().items():
		for addr in addrs:
			if (
				addr.family == socket.AF_INET and
				not addr.address.startswith("127.") and
				not addr.address.startswith("169.254.")  # Skip link-local
			):
				ip = addr.address
				netmask = addr.netmask
				if ip and netmask:
					interface = ipaddress.IPv4Interface(f"{ip}/{netmask}")
					return str(interface.network.broadcast_address)
	return "255.255.255.255"

# this function is commented out because it requires the netifaces library,
'''
def get_broadcast_address():
	interfaces = ni.interfaces()
	for iface in interfaces:
		ifaddresses = ni.ifaddresses(iface)
		if ni.AF_INET in ifaddresses:
			for link in ifaddresses[ni.AF_INET]:
				ip = link.get('addr')
				netmask = link.get('netmask')
				if ip and netmask and not ip.startswith('127.'):
					interface = ipaddress.IPv4Interface(f"{ip}/{netmask}")
					return str(interface.network.broadcast_address)
	return '255.255.255.255'
'''