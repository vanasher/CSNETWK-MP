# keeps track of all known peers and their data in a dictionary
class PeerManager:
    def __init__(self, logger):
        self.logger = logger
        self.peers = {} # stores disctionary of peers by USER_ID
        				# user_id -> {display_name, status, posts: [], dms: []}
                        
	# add or update a peer's profile info
    def add_peer(self, user_id, display_name, status):
        if user_id not in self.peers:
            self.peers[user_id] = {
                'display_name': display_name,
                'status': status,
                'posts': [],
                'dms': []
            }
        else:
            self.peers[user_id]['display_name'] = display_name
            self.peers[user_id]['status'] = status

	# add a new post to the peer's post list
    def add_post(self, user_id, content):
        if user_id in self.peers:
            self.peers[user_id]['posts'].append(content)

	# add a new dm to the peer's dm list
    def add_dm(self, user_id, content):
        if user_id in self.peers:
            self.peers[user_id]['dms'].append(content)

	# returns a list of (user_id, display_name) for all known peers
    def list_peers(self):
        return [(uid, info['display_name']) for uid, info in self.peers.items()]