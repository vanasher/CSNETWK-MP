import socket
import json

def send_message(msg_dict, addr, udp_socket=None):
    if udp_socket is None:
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    msg_json = json.dumps(msg_dict).encode('utf-8')
    udp_socket.sendto(msg_json, addr)