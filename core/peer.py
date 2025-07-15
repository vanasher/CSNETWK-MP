# keeps track of all known peers and their data in a dictionary
class PeerManager:
	def __init__(self, logger):
		self.logger = logger
		self.peers = {} # stores disctionary of peers by USER_ID
						# user_id -> {display_name, status, posts: [], dms: []}
						
	# add or update a peer's profile info
	def add_peer(self, user_id, display_name, status, avatar_type=None, avatar_data=None):
		if user_id not in self.peers:
			self.peers[user_id] = {
				'display_name': display_name,
				'status': status,
				'avatar_type': avatar_type,
				'avatar_data': avatar_data,
				'posts': [],
				'dms': []
			}
		else:
			self.peers[user_id]['display_name'] = display_name
			self.peers[user_id]['status'] = status
			if avatar_type and avatar_data:
				self.peers[user_id]['avatar_type'] = avatar_type
				self.peers[user_id]['avatar_data'] = avatar_data

	# add a new post to the peer's post list
	def add_post(self, user_id, content, timestamp=None, ttl=None, message_id=None):
		if user_id in self.peers:
			self.peers[user_id]['posts'].append({
			'content': content,
			'timestamp': timestamp,
			'ttl': ttl,
			'message_id': message_id
		})

	# add a new dm to the peer's dm list
	def add_dm(self, user_id, content, timestamp=None, message_id=None):
		if user_id in self.peers:
			self.peers[user_id]['dms'].append({
				'content': content,
				'timestamp': timestamp,
				'message_id': message_id
			})
		else: # this else block handles previously unknown peers (have not yet recevied a PROFILE message from)
			self.peers[user_id] = {
				'display_name': user_id,
				'status': '',
				'posts': [],
				'dms': [{
					'content': content,
					'timestamp': timestamp,
					'message_id': message_id
				}]
			}

	# returns a list of (user_id, display_name) for all known peers
	def list_peers(self):
		return [(uid, info['display_name']) for uid, info in self.peers.items()]