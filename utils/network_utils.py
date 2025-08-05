import socket
from parser.message_parser import craft_message
import ipaddress
import psutil
import struct
import time
import mimetypes
import random
import uuid
import base64
import config
import os

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


# compute the broadcast address from an IP and netmask
def compute_broadcast_address(ip_str, netmask_str):
    ip = struct.unpack('!I', socket.inet_aton(ip_str))[0]
    netmask = struct.unpack('!I', socket.inet_aton(netmask_str))[0]
    broadcast = ip | ~netmask & 0xFFFFFFFF
    return socket.inet_ntoa(struct.pack('!I', broadcast))

# testing if this works better
def get_manual_broadcast():
    for iface_name, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if (
                addr.family == socket.AF_INET and
                not addr.address.startswith("127.") and
                not addr.address.startswith("169.254.")  # Skip loopback and link-local
            ):
                ip = addr.address
                netmask = addr.netmask
                if ip and netmask:
                    return compute_broadcast_address(ip, netmask)
    return "255.255.255.255"

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

# func for validating token
def validate_token(token, required_scope, revoked_tokens):
    try:
        user_id, expiry, scope = token.split("|")
        expiry = int(expiry)

        if time.time() > expiry:
            return False, "Expired token"
        if scope != required_scope:
            return False, f"Scope mismatch: expected '{required_scope}', got '{scope}'"
        if token in revoked_tokens:
            return False, "Token has been revoked"

        return True, None
    except Exception as e:
        return False, f"Invalid token format: {e}"

# func for sending file offer
def send_file_offer(peer_manager, ttl):
	from_id = peer_manager.get_own_profile().get("USER_ID")
	to_user = input("Enter recipient (user_id@ip): ").strip()
	file_path = input("Enter full file path: ").strip()

	if not os.path.isfile(file_path):
		print("File not found.")
		return

	filename = os.path.basename(file_path)
	filesize = os.path.getsize(file_path)
	filetype = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
	file_id = uuid.uuid4().hex[:8]
	description = input("Enter file description (optional): ").strip()

	import time
	now = int(time.time())
	token = f"{from_id}|{now + ttl}|file"

	offer_msg = {
		"TYPE": "FILE_OFFER",
		"FROM": from_id,
		"TO": to_user,
		"FILENAME": filename,
		"FILESIZE": filesize,
		"FILETYPE": filetype,
		"FILEID": file_id,
		"DESCRIPTION": description,
		"TIMESTAMP": now,
		"TOKEN": token
	}

	ip = to_user.split("@")[1]
	send_message(offer_msg, (ip, config.PORT))
	peer_manager.logger.log_send("FILE_OFFER", to_user, offer_msg)

	print(f"File offer sent to {to_user} for '{filename}' ({filesize} bytes)")
	peer_manager.add_pending_file(file_id, file_path, token)

	# return these for use in sending FILE_CHUNK later
	return {
		"file_path": file_path,
		"file_id": file_id,
		"to_user": to_user,
		"token": token
	}

# func for handling file offer
def handle_file_offer(message, peer_manager):
	from_user = message["FROM"]
	file_id = message["FILEID"]
	filename = message["FILENAME"]
	filesize = int(message["FILESIZE"])
	filetype = message["FILETYPE"]
	description = message.get("DESCRIPTION", "")
	token = message["TOKEN"]

	# Non-verbose prompt
	display_name = peer_manager.get_display_name(from_user)
	print(f"User {display_name} is sending you a file. Do you accept? (yes/no)")

	response = input("> ").strip().lower()
	if response != "yes":
		print("You ignored the file offer.")
		peer_manager.file_transfer_context[file_id] = {"accepted": False}
		return
	elif response == "yes":
		import time
		now = int(time.time())

		accepted_msg = {
		"TYPE": "FILE_ACCEPTED",
		"FROM": peer_manager.get_own_profile()["USER_ID"],
		"TO": from_user,
		"FILEID": file_id,
		"TIMESTAMP": now
		}
		send_message(accepted_msg, (from_user.split('@')[1], config.PORT))
		peer_manager.logger.log_send("FILE_ACCEPTED", from_user, accepted_msg)

	# Store offer context
	peer_manager.file_transfer_context[file_id] = {
		"accepted": True,
		"from": from_user,
		"filename": filename,
		"filesize": filesize,
		"filetype": filetype,
		"description": description,
		"token": token,
		"received_chunks": {},
		"total_chunks": None,
	}

	print(f"Accepted file offer for: {filename} ({filesize} bytes)")

def handle_file_chunk(message, peer_manager):
	file_id = message["FILEID"]
	from_user = message["FROM"]
	token = message["TOKEN"]
	
	if file_id not in peer_manager.file_transfer_context:
		return  # No matching FILE_OFFER
	if not peer_manager.file_transfer_context[file_id].get("accepted", False):
		return  # User rejected the offer
	
	# Validate token
	if not validate_token(token, "file", peer_manager.revoked_tokens):
		return  # Invalid or expired token

	# Extract chunk info
	chunk_index = int(message["CHUNK_INDEX"])
	total_chunks = int(message["TOTAL_CHUNKS"])
	chunk_data = base64.b64decode(message["DATA"])
	
	# Prepare metadata context
	context = peer_manager.file_transfer_context[file_id]
	context["total_chunks"] = total_chunks
	context["received_chunks"][chunk_index] = chunk_data

	# Check if all chunks are received
	if len(context["received_chunks"]) == total_chunks:
		filename = context["filename"]
		chunks = [context["received_chunks"][i] for i in range(total_chunks)]
		full_data = b''.join(chunks)

		# Save file (simulate or write)
		with open(filename, "wb") as f:
			f.write(full_data)

		print(f"File transfer of {filename} is complete")

		# Send FILE_RECEIVED
		file_received_msg = {
			"TYPE": "FILE_RECEIVED",
			"FROM": peer_manager.get_own_profile().get("USER_ID"),
			"TO": from_user,
			"FILEID": file_id,
			"STATUS": "COMPLETE",
			"TIMESTAMP": int(time.time())
		}
		send_message(file_received_msg, (from_user.split("@")[1], config.PORT))

def send_file_chunks(file_id, filepath, receiver_id, token, peer_manager):
	CHUNK_SIZE = 4096
	total_size = os.path.getsize(filepath)
	total_chunks = (total_size + CHUNK_SIZE - 1) // CHUNK_SIZE  # ceil division
	sender_id = peer_manager.get_own_profile()["USER_ID"]
	receiver_ip = receiver_id.split("@")[1]

	with open(filepath, "rb") as f:
		for chunk_index in range(total_chunks):
			chunk_data = f.read(CHUNK_SIZE)
			encoded_data = base64.b64encode(chunk_data).decode()

			message = {
				"TYPE": "FILE_CHUNK",
				"FROM": sender_id,
				"TO": receiver_id,
				"FILEID": file_id,
				"CHUNK_INDEX": chunk_index,
				"TOTAL_CHUNKS": total_chunks,
				"CHUNK_SIZE": CHUNK_SIZE,
				"DATA": encoded_data,
				"TOKEN": token,
				"TIMESTAMP": int(time.time())
			}

			send_message(message, (receiver_ip, config.PORT))
			peer_manager.logger.log_send("FILE_CHUNK", receiver_id, message)