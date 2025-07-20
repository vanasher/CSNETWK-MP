# keeps track of all known peers and their data in a dictionary
class PeerManager:
	def __init__(self, logger):
		self.logger = logger
		self.peers = {} # stores disctionary of peers by USER_ID
						# user_id -> {display_name, status, posts: [], dms: []}
						
	# add or update a peer's profile info
	def add_peer(self, user_id, display_name, status, avatar_type=None, avatar_encoding=None, avatar_data=None):
		if user_id not in self.peers:
			self.peers[user_id] = {
				'display_name': display_name,
				'status': status,
				'avatar_type': avatar_type,
				'avatar_encoding': avatar_encoding,
				'avatar_data': avatar_data,
				'posts': [],
				'dms': [],
				'followers': []
			}
		else:
			self.peers[user_id]['display_name'] = display_name
			self.peers[user_id]['status'] = status
			if avatar_type and avatar_data:
				self.peers[user_id]['avatar_type'] = avatar_type
				self.peers[user_id]['avatar_encoding'] = avatar_encoding
				self.peers[user_id]['avatar_data'] = avatar_data
			if 'followers' not in self.peers[user_id]:
				self.peers[user_id]['followers'] = []

	# add a new post to the peer's post list
	def add_post(self, user_id, content, timestamp=None, ttl=None, message_id=None):
		if user_id in self.peers:
			self.peers[user_id]['posts'].append({
			'content': content,
			'ttl': ttl,
			'message_id': message_id
			#token: token
		})

	# add a new dm to the peer's dm list
	def add_dm(self, user_id, content, timestamp=None, message_id=None):
		if user_id in self.peers:
			self.peers[user_id]['dms'].append({
				'content': content,
				'timestamp': timestamp,
				'message_id': message_id,
				#'token': token
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
					#'token': token
				}]
			}

	# add a new follower to a peer's followers list
	def add_follower(self, to_user, from_user, token=None, timestamp=None, message_id=None):
		if to_user not in self.peers:
			self.peers[to_user] = {
				'display_name': to_user,
				'status': '',
				'posts': [],
				'dms': [],
				'followers': []
			}

		# initialize followers list if not present
		if 'followers' not in self.peers[to_user]:
			self.peers[to_user]['followers'] = []

		# check if already followed by from_user
		existing = next((f for f in self.peers[to_user]['followers'] if f['user'] == from_user), None)
		if not existing:
			self.peers[to_user]['followers'].append({
				'user': from_user,
				'token': token,
				'timestamp': timestamp,
				'message_id': message_id
			})
			self.logger.info(f"User {from_user} has followed {to_user}")

	# remove a follower from a peer's followers list
	def remove_follower(self, to_user, from_user, token=None, timestamp=None, message_id=None):
		if to_user in self.peers and 'followers' in self.peers[to_user]:
			if from_user in self.peers[to_user]['followers']:
				self.peers[to_user]['followers'].remove(from_user)
				self.logger.info(f"User {from_user} has unfollowed {to_user}")
		else:
			self.logger.debug(f"UNFOLLOW: Peer {to_user} not found or has no followers")

	# returns a list of (user_id, display_name) for all known peers
	def list_peers(self):
		return [(uid, info['display_name']) for uid, info in self.peers.items()]