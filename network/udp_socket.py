import socket

UDP_PORT = 54321
BUFFER_SIZE = 1024

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('', UDP_PORT)) # binds to all interfaces on the given port

print(f"Listening for UDP packets on port {UDP_PORT}")

while True:
	data, addr = sock.recvfrom(BUFFER_SIZE)
	print(f"Received message from {addr}: {data.decode()}")
