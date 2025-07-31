from utils.network_utils import get_local_ip
from utils.network_utils import send_message
import config
import threading
import time

#  keeps track of all known peers and their data in a dictionary
class PeerManager:
	def __init__(self, logger):
		self.profile_updated = False # flag to indicate if the profile was updated
		self.profile_created = False # flag to indicate if the profile was created
		self.logger = logger
		self.peers = {} # stores disctionary of peers by USER_ID
						# user_id -> {display_name, status, posts: [], dms: []}
		self.own_profile = None
		self.following = set()
		self.pending_acks = {}  # KEY: MESSAGE_ID, VALUE: {message, addr, timestamp, attempts}
	
	# set the user's profile data
	def set_own_profile(self, username, display_name, status, avatar_type=None, avatar_encoding=None, avatar_data=None):
		ip = get_local_ip()
		user_id = f"{username}@{ip}"

		is_first_time = not self.own_profile # check if it's the first time setting the profile

		self.own_profile = {
			"TYPE": "PROFILE",
			"USER_ID": user_id,
			"DISPLAY_NAME": display_name,
			"STATUS": status,
			"AVATAR_TYPE": avatar_type,
			"AVATAR_ENCODING": avatar_encoding,
			"AVATAR_DATA": avatar_data
		}
		self.profile_updated = not is_first_time
		self.profile_created = True

		self.logger.log("PEER", f"Own profile {'created' if is_first_time else 'updated'} with USER_ID {user_id}.")

		# initial broadcast (broadcast a profile immediately after setting it)
		# added this so peers would immediately add the new user to known peers
		# after initial broadcast, the message will be broadcast periodically
		if is_first_time:
			profile = self.get_own_profile()
			self.logger.log_send("PROFILE", f"{config.BROADCAST_ADDR}:{config.PORT}", profile)
			send_message(profile, (config.BROADCAST_ADDR, config.PORT))

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

	# add a new post to the peer's post list
	def add_post(self, user_id, content, timestamp=None, ttl=None, message_id=None):
		if user_id in self.peers:
			self.peers[user_id]['posts'].append({
			'content': content,
			'ttl': ttl,
			'message_id': message_id
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
				ttl = post.get('ttl', 'N/A')
				print(f"  {i}. {content}")
				print(f"     ID: {message_id} | TTL: {ttl}")
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

	# start a background thread for watching ACKs
	def start_ack_watcher(self):
		def retransmit_loop():
			while True:
				now = time.time()
				for message_id, entry in list(self.pending_acks.items()):
					if now - entry["timestamp"] > 2:
						if entry["attempts"] < 5:
							send_message(entry["message"], entry["addr"])
							entry["timestamp"] = now
							entry["attempts"] += 1
							self.logger.log("RETRY", f"Retransmitted {message_id} (attempt {entry['attempts']})")
						else:
							self.logger.log("DROP", f"Gave up on {message_id} after 5 attempts")
							del self.pending_acks[message_id]
				time.sleep(0.5)

		threading.Thread(target=retransmit_loop, daemon=True).start()