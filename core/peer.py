from utils.network_utils import get_local_ip

#  keeps track of all known peers and their data in a dictionary
class PeerManager:
	def __init__(self, logger):
		self.logger = logger
		self.peers = {} # stores disctionary of peers by USER_ID
						# user_id -> {display_name, status, posts: [], dms: []}
		self.own_profile = None
		self.following = set()
	
	# set the user's profile data
	def set_own_profile(self, username, display_name, status, avatar_type=None, avatar_encoding=None, avatar_data=None):
		ip = get_local_ip()
		user_id = f"{username}@{ip}"
		self.own_profile = {
			"TYPE": "PROFILE",
			"USER_ID": user_id,
			"DISPLAY_NAME": display_name,
			"STATUS": status,
			"AVATAR_TYPE": avatar_type,
			"AVATAR_ENCODING": avatar_encoding,
			"AVATAR_DATA": avatar_data
		}
		self.logger.log("PEER", f"Own profile updated with USER_ID {user_id}.")

	# for broadcasting own profile periodically
	def get_own_profile(self):
		return self.own_profile
	
	def has_profile(self):
		return self.own_profile.get("USER_ID") is not None
	
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
			
			# Ensure existing posts have likes lists
			for post in self.peers[user_id].get('posts', []):
				if 'likes' not in post:
					post['likes'] = []

	# add a new post to the peer's post list
	def add_post(self, user_id, content, timestamp=None, ttl=None, message_id=None):
		if user_id in self.peers:
			if timestamp is None:
				import time
				timestamp = int(time.time())
			
			self.peers[user_id]['posts'].append({
			'content': content,
			'timestamp': timestamp,
			'ttl': ttl,
			'message_id': message_id,
			'likes': []  # Initialize likes list for each post
			#token: token
		})

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
			self.logger.log("FOLLOW", f"User {from_user} has followed {to_user}")

	# remove a follower from a peer's followers list
	def remove_follower(self, to_user, from_user, token=None, timestamp=None, message_id=None):
		if to_user in self.peers and 'followers' in self.peers[to_user]:
			original_len = len(self.peers[to_user]['followers'])
			self.peers[to_user]['followers'] = [
				f for f in self.peers[to_user]['followers'] if f['user'] != from_user
			]
			if len(self.peers[to_user]['followers']) < original_len:
				self.logger.log("UNFOLLOW", f"User {from_user} has unfollowed {to_user}")
		else:
			self.logger.log("UNFOLLOW", f"Peer {to_user} not found or has no followers")
	
	# func for following a user
	def follow(self, user_id):
		self.following.add(user_id)
		self.logger.log("FOLLOW", f"You are now following {user_id}")
	
	# func for checking if following a user
	def is_following(self, user_id):
		return user_id in self.following
	
	def get_display_name(self, user_id):
		if user_id == self.own_profile.get("USER_ID"):
			return self.own_profile.get("DISPLAY_NAME", user_id)
		peer = self.peers.get(user_id)
		return peer.get("display_name", user_id) if peer else user_id

	# return a list of (user_id, ip_address) of peers who follow the current user
	def get_follower_ips(self):
		followers = []
		own_id = self.own_profile.get("USER_ID")
		
		for peer_id, peer_info in self.peers.items():
			for follower in peer_info.get("followers", []):
				if follower['user'] == own_id:
					# this means peer_id is someone who follows me
					ip = peer_id.split("@")[-1]
					followers.append((peer_id, ip))
					break

		return followers
	
	def add_dm(self, from_user, content, timestamp, message_id, token):
		if from_user not in self.peers:
			self.peers[from_user] = {}

		if "dms" not in self.peers[from_user]:
			self.peers[from_user]["dms"] = []

		self.peers[from_user]["dms"].append({
			"content": content,
			"timestamp": timestamp,
			"message_id": message_id,
			"token": token
		})
	
	# returns a list of (user_id, display_name) for all known peers
	def list_peers(self):
		return [(uid, info['display_name']) for uid, info in self.peers.items()]
	
	# show detailed information about a peer including posts and DMs
	def show_peer_details(self, user_id, display_name):
		"""Display detailed information about a peer including their posts and DMs"""
		peer_info = self.peers.get(user_id)
		if not peer_info:
			print(f"Peer '{user_id}' not found.")
			return
		
		print(f"\nPeer: {display_name} ({user_id})")
		print(f"Status: {peer_info.get('status', 'No status')}")
		
		# Show following status
		following_status = "Following" if self.is_following(user_id) else "Not Following"
		print(f"Following Status: {following_status}")
		
		# Show followers count
		followers_count = len(peer_info.get('followers', []))
		print(f"Followers: {followers_count}")
		
		# Show Posts
		posts = peer_info.get('posts', [])
		print(f"\nPosts ({len(posts)}):")
		if posts:
			for i, post in enumerate(posts, 1):
				content = post.get('content', 'No content')
				message_id = post.get('message_id', 'N/A')
				timestamp = post.get('timestamp', 'N/A')
				ttl = post.get('ttl', 'N/A')
				likes_count = len(post.get('likes', []))
				
				# Convert timestamp to readable format if it's a number
				try:
					if isinstance(timestamp, (int, float)) or (isinstance(timestamp, str) and timestamp.isdigit()):
						import datetime
						readable_time = datetime.datetime.fromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M:%S')
					else:
						readable_time = str(timestamp)
				except:
					readable_time = str(timestamp)
				
				print(f"  {i}. {content}")
				print(f"     ID: {message_id} | Time: {readable_time} | TTL: {ttl} | Likes: {likes_count}")
				
				# Show likes if any
				if likes_count > 0:
					likes = post.get('likes', [])
					for like in likes[:3]:  # Show first 3 likes
						liker = self.get_display_name(like.get('liker_id', 'Unknown'))
						action = like.get('action', 'LIKE')
						print(f"       {'👍' if action == 'LIKE' else '👎'} {liker}")
					if likes_count > 3:
						print(f"       ... and {likes_count - 3} more")
		else:
			print("  No posts from this peer.")
		
		# Show DMs
		dms = peer_info.get('dms', [])
		print(f"\nDirect Messages ({len(dms)}):")
		if dms:
			for i, dm in enumerate(dms, 1):
				content = dm.get('content', 'No content')
				timestamp = dm.get('timestamp', 'N/A')
				message_id = dm.get('message_id', 'N/A')
				
				# Convert timestamp to readable format if it's a number
				try:
					if isinstance(timestamp, (int, float)) or (isinstance(timestamp, str) and timestamp.isdigit()):
						import datetime
						readable_time = datetime.datetime.fromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M:%S')
					else:
						readable_time = str(timestamp)
				except:
					readable_time = str(timestamp)
				
				print(f"  {i}. {content}")
				print(f"     ID: {message_id} | Time: {readable_time}")
		else:
			print("  No direct messages from this peer.")
		
		print()  # Empty line for spacing
	
	# add a like to a specific post by timestamp
	def add_like_to_post(self, post_author, post_timestamp, liker_id, action, timestamp, token):
		"""Add a like to a specific post by timestamp"""
		if post_author not in self.peers:
			return False
		
		# Find the post by timestamp
		for post in self.peers[post_author].get('posts', []):
			if str(post.get('timestamp')) == str(post_timestamp):
				# Initialize likes list if not present
				if 'likes' not in post:
					post['likes'] = []
				
				if action == "LIKE":
					# Check if user already liked this post
					for like in post['likes']:
						if like.get('liker_id') == liker_id:
							self.logger.log("LIKE", f"User {liker_id} already liked this post")
							return False
					
					# Add the like
					post['likes'].append({
						'liker_id': liker_id,
						'action': action,
						'timestamp': timestamp,
						'token': token
					})
					
					self.logger.log("LIKE", f"User {liker_id} liked post at timestamp {post_timestamp}")
					return True
					
				elif action == "UNLIKE":
					# Remove the like
					original_len = len(post['likes'])
					post['likes'] = [like for like in post['likes'] if like.get('liker_id') != liker_id]
					
					if len(post['likes']) < original_len:
						self.logger.log("LIKE", f"User {liker_id} unliked post at timestamp {post_timestamp}")
						return True
					else:
						self.logger.log("LIKE", f"User {liker_id} tried to unlike post they haven't liked")
						return False
		
		return False