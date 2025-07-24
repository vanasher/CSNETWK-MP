import socket
from parser.message_parser import craft_message
import ipaddress

def send_message(msg_dict, addr, udp_socket=None):
    if udp_socket is None:
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    msg_text = craft_message(msg_dict)
    udp_socket.sendto(msg_text.encode('utf-8'), addr)

def get_local_ip():
    # This tries to connect to an external host, but doesn't actually send data,
    # just to get the outbound interface IP address.
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # This IP is arbitrary; 8.8.8.8 is Google DNS
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def get_broadcast_address():
    # Get local IP address
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = '127.0.0.1'
    finally:
        s.close()

    # Assume common subnet mask (e.g., /24 = 255.255.255.0)
    # You can adjust this logic to read actual subnet if you want
    interface = ipaddress.IPv4Interface(f'{local_ip}/24')
    return str(interface.network.broadcast_address)