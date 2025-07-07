from datetime import datetime

peer_log = {}

def log_peer(ip, port):
    timestamp = datetime.now().isoformat()
    peer_log[(ip, port)] = timestamp
    print(f"Logged peer {ip}:{port} at {timestamp}")