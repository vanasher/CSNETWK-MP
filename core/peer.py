from utils.network_utils import get_local_ip
from utils.network_utils import send_message
import config
import threading
import time
from utils.network_utils import validate_token

#  keeps track of all known peers and their data in a dictionary
class PeerManager:
	def __init__(self, logger):
		self.profile_updated = False # flag to indicate if the profile was updated
		self.profile_created = False # flag to indicate if the profile was created
		self.logger = logger
		self.peers = {} # stores disctionary of peers by USER_ID
						# user_id -> {display_name, status, posts: [], dms: []}
		self.own_profile = None
		self.own_posts = [] # track our own posts for like reference
		self.following = set()
		self.pending_acks = {}  # KEY: MESSAGE_ID, VALUE: {message, addr, timestamp, attempts}
		self.followers = [] # composed of user_id of followers
		self.revoked_tokens = set()
		self.issued_tokens = [] # token is added everytime the user sends a message with a token
		self.games = {}  # key = GAMEID, value = game info dict
		
		# Group functionality data structures
		self.groups = {} # GROUP_ID -> {group_name, members: [], creator, created_timestamp, messages: []}
		self.owned_groups = set() # GROUP_IDs that this user created
	
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

		# broadcast profile everytime peer sets profile
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
	def add_post(self, user_id, content, timestamp=None, ttl=None, message_id=None, token=None):
		if user_id in self.peers:
			self.peers[user_id]['posts'].append({
			'content': content,
			'timestamp': timestamp,
			'ttl': ttl,
			'message_id': message_id,
			'token': token
		})

	# add our own post for tracking purposes (for likes)
	def add_own_post(self, content, timestamp, ttl, message_id, token):
		"""Track our own posts for like functionality"""
		self.own_posts.append({
			'content': content,
			'timestamp': timestamp,
			'ttl': ttl,
			'message_id': message_id,
			'token': token
		})

	# add a new follower to a peer's followers list
	def add_follower(self, to_user, from_user, token=None, timestamp=None, message_id=None):
		follower_ips = self.get_follower_ips()
		if from_user in self.peers:
			ip = from_user.split('@')[1]  # Extract IP from user_id
			if ip not in follower_ips:
				self.followers.append(from_user)

	# remove a follower from a peer's followers list
	def remove_follower(self, to_user, from_user, token=None, timestamp=None, message_id=None):
		if from_user in self.peers and from_user in self.followers:
			self.followers.remove(from_user)
		else:
			print(f"Peer {from_user} not found or invalid message.")
	
	# func for following a user
	def follow(self, user_id):
		self.following.add(user_id)
		# self.logger.log("FOLLOW", f"You are now following {user_id}")
	
	# func for checking if following a user
	def is_following(self, user_id):
		return user_id in self.following
	
	def get_display_name(self, user_id):
		if user_id == self.own_profile.get("USER_ID"):
			return self.own_profile.get("DISPLAY_NAME", user_id)
		peer = self.peers.get(user_id)
		return peer.get("display_name", user_id) if peer else user_id

	# return a list of ip address of peers who follow the current user
	def get_follower_ips(self):
		followers = []
		
		for user_id in self.followers:
			ip = user_id.split('@')[1]  # Extract IP from user_id
			followers.append(ip)
		return followers
	
	def get_known_peer_ips(self):
		known_peers = []
		for peer in self.peers:
			ip = peer.get["USER_ID"].split('@')[1]
			known_peers.append(ip)
		return known_peers

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
		
		#i don't think we need to show followers of the chosen peer (?)
		# Show followers count
		# followers_count = len(peer_info.get('followers', []))
		# print(f"Followers: {followers_count}")
		
		# Show Posts
		posts = peer_info.get('posts', [])
		print(f"\nPosts ({len(posts)}):")
		if posts:
			# checks if a valid post exists
			valid_exists = False
			for i, post in enumerate([posts], 1):
				is_valid, error = validate_token(post.get("token"), "broadcast", self.revoked_tokens)
				if is_valid:
					valid_exists = True
					break
			if valid_exists:
				for i, post in enumerate(posts, 1):
					content = post.get('content', 'No content')
					message_id = post.get('message_id', 'N/A')
					ttl = post.get('ttl', 'N/A')
					print(f"  {i}. {content}")
					print(f"     ID: {message_id} | TTL: {ttl}")
			else:
				print("  No posts from this peer.")
		else:
			print("  No posts from this peer.")
		
		# Show DMs
		dms = peer_info.get('dms', [])
		print(f"\nDirect Messages ({len(dms)}):")
		if dms:
			# checks if a valid dm exists
			valid_exists = False
			for i, dm in enumerate(dms, 1):
				is_valid, error = validate_token(dm.get("token"), "chat", self.revoked_tokens)
				if is_valid:
					valid_exists = True
					break
			if valid_exists:
				for i, dm in enumerate(dms, 1):
					is_valid, error = validate_token(dm.get("token"), "chat", self.revoked_tokens)
					if is_valid:
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
		else:
			print("  No direct messages from this peer.")
		
		print()  # Empty line for spacing

	# start a background thread for watching ACKs
	def start_ack_watcher(self):
		def retransmit_loop():
			while True:
				now = time.time()
				for message_id, entry in list(self.pending_acks.items()):
					if now - entry["timestamp"] > 2: # timeout of 2 seconds
						if entry["attempts"] < 3: # 3 attemps max
							send_message(entry["message"], entry["addr"])
							entry["timestamp"] = now
							entry["attempts"] += 1
							self.logger.log("RETRY", f"Retransmitted {message_id} (attempt {entry['attempts']})")
						else:
							self.logger.log("DROP", f"Gave up on {message_id} after 3 attempts")
							del self.pending_acks[message_id]
				time.sleep(0.5)

		threading.Thread(target=retransmit_loop, daemon=True).start()

	# create a new game when sending or receiving a game invite
	def create_game(self, game_id, opponent_id, is_initiator, token, my_symbol=None, opponent_symbol=None):
		if my_symbol is None or opponent_symbol is None:
			symbol = "X" if is_initiator else "O"
			opponent_symbol = "O" if is_initiator else "X"
		else:
			symbol = my_symbol
		
		self.games[game_id] = {
			"board": [" "] * 9,
			"turn": 1,
			"symbol": symbol,
			"opponent_symbol": opponent_symbol,
			"opponent_id": opponent_id,
			"my_turn": is_initiator,
			"last_message_id": None,
			"token": token
		}
	
	def apply_move(self, game_id, position, is_self, symbol=None):
		game = self.games.get(game_id)
		if not game:
			return False

		if position < 0 or position >= 9 or game["board"][position] != " ":
			return False

		if symbol is None:
			symbol = game["symbol"] if is_self else game["opponent_symbol"]

		game["board"][position] = symbol
		game["turn"] += 1
		game["my_turn"] = not is_self  # It will be their turn if is_self is False
		return True
	
	def add_like(self, target_user, post_timestamp, action, post_content):
		"""Add a like/unlike record for tracking purposes"""
		if target_user not in self.peers:
			return False
		
		if 'likes' not in self.peers[target_user]:
			self.peers[target_user]['likes'] = []
		
		# Remove any existing like/unlike for this post from this user
		likes_list = self.peers[target_user]['likes']
		self.peers[target_user]['likes'] = [
			like for like in likes_list 
			if like.get('post_timestamp') != post_timestamp or like.get('from_user') != self.own_profile["USER_ID"]
		]
		
		# Add the new like/unlike
		if action == "LIKE":
			self.peers[target_user]['likes'].append({
				'from_user': self.own_profile["USER_ID"],
				'post_timestamp': post_timestamp,
				'action': action,
				'post_content': post_content,
				'timestamp': int(time.time())
			})
		
		return True
	
	def handle_like_received(self, from_user, post_timestamp, action, post_content):
		"""Handle when someone likes/unlikes our post"""
		if not self.own_profile:
			return False
		
		# Initialize likes structure if it doesn't exist
		if not hasattr(self, 'received_likes'):
			self.received_likes = []
		
		# Remove any existing like/unlike for this post from this user
		self.received_likes = [
			like for like in self.received_likes 
			if not (like.get('from_user') == from_user and like.get('post_timestamp') == post_timestamp)
		]
		
		# Add the new like (but not unlike - unlikes just remove the like)
		if action == "LIKE":
			self.received_likes.append({
				'from_user': from_user,
				'post_timestamp': post_timestamp,
				'action': action,
				'post_content': post_content,
				'timestamp': int(time.time())
			})
		
		return True
	# ===== GROUP MANAGEMENT METHODS =====
	
	def create_group(self, group_id, group_name, members):
		"""Create a new group with initial members"""
		if not self.own_profile:
			raise ValueError("Profile must be set before creating groups")
		
		creator = self.own_profile["USER_ID"]
		timestamp = int(time.time())
		
		# Store group locally
		self.groups[group_id] = {
			"group_name": group_name,
			"members": members.copy(),
			"creator": creator,
			"created_timestamp": timestamp,
			"messages": []
		}
		self.owned_groups.add(group_id)
		
		return {
			"TYPE": "GROUP_CREATE",
			"FROM": creator,
			"GROUP_ID": group_id,
			"GROUP_NAME": group_name,
			"MEMBERS": ",".join(members),
			"TIMESTAMP": str(timestamp),
			"TOKEN": f"{creator}|{timestamp + config.TTL}|group"
		}
	
	def update_group(self, group_id, add_members=None, remove_members=None):
		"""Update group membership"""
		if group_id not in self.groups:
			raise ValueError(f"Group {group_id} not found")
		
		if not self.own_profile:
			raise ValueError("Profile must be set")
		
		creator = self.own_profile["USER_ID"]
		timestamp = int(time.time())
		group = self.groups[group_id]
		
		# Update local membership
		if add_members:
			for member in add_members:
				if member not in group["members"]:
					group["members"].append(member)
		
		if remove_members:
			for member in remove_members:
				if member in group["members"]:
					group["members"].remove(member)
		
		# Create update message
		message = {
			"TYPE": "GROUP_UPDATE",
			"FROM": creator,
			"GROUP_ID": group_id,
			"TIMESTAMP": str(timestamp),
			"TOKEN": f"{creator}|{timestamp + config.TTL}|group"
		}
		
		if add_members:
			message["ADD"] = ",".join(add_members)
		if remove_members:
			message["REMOVE"] = ",".join(remove_members)
		
		return message
	
	def send_group_message(self, group_id, content):
		"""Send a message to all group members"""
		if group_id not in self.groups:
			raise ValueError(f"Group {group_id} not found")
		
		if not self.own_profile:
			raise ValueError("Profile must be set")
		
		sender = self.own_profile["USER_ID"]
		timestamp = int(time.time())
		
		# Store message locally
		message_data = {
			"from": sender,
			"content": content,
			"timestamp": timestamp
		}
		self.groups[group_id]["messages"].append(message_data)
		
		return {
			"TYPE": "GROUP_MESSAGE",
			"FROM": sender,
			"GROUP_ID": group_id,
			"CONTENT": content,
			"TIMESTAMP": str(timestamp),
			"TOKEN": f"{sender}|{timestamp + config.TTL}|group"
		}
	
	def handle_group_create(self, message):
		"""Handle incoming GROUP_CREATE message"""
		group_id = message.get("GROUP_ID")
		group_name = message.get("GROUP_NAME")
		members_str = message.get("MEMBERS", "")
		creator = message.get("FROM")
		timestamp = int(message.get("TIMESTAMP", 0))
		
		members = [m.strip() for m in members_str.split(",") if m.strip()]
		
		# Check if we're in the group
		my_user_id = self.own_profile.get("USER_ID") if self.own_profile else None
		if my_user_id and my_user_id in members:
			self.groups[group_id] = {
				"group_name": group_name,
				"members": members,
				"creator": creator,
				"created_timestamp": timestamp,
				"messages": []
			}
			return True
		return False
	
	def handle_group_update(self, message):
		"""Handle incoming GROUP_UPDATE message"""
		group_id = message.get("GROUP_ID")
		add_members_str = message.get("ADD", "")
		remove_members_str = message.get("REMOVE", "")
		
		if group_id not in self.groups:
			return False
		
		group = self.groups[group_id]
		
		# Add members
		if add_members_str:
			add_members = [m.strip() for m in add_members_str.split(",") if m.strip()]
			for member in add_members:
				if member not in group["members"]:
					group["members"].append(member)
		
		# Remove members
		if remove_members_str:
			remove_members = [m.strip() for m in remove_members_str.split(",") if m.strip()]
			for member in remove_members:
				if member in group["members"]:
					group["members"].remove(member)
		
		return True
	
	def handle_group_message(self, message):
		"""Handle incoming GROUP_MESSAGE"""
		group_id = message.get("GROUP_ID")
		content = message.get("CONTENT")
		sender = message.get("FROM")
		timestamp = int(message.get("TIMESTAMP", 0))
		
		if group_id not in self.groups:
			return False
		
		# Check if sender is a group member
		if sender not in self.groups[group_id]["members"]:
			return False
		
		# Store message
		message_data = {
			"from": sender,
			"content": content,
			"timestamp": timestamp
		}
		self.groups[group_id]["messages"].append(message_data)
		return True
	
	def list_groups(self):
		"""List all groups this user belongs to"""
		return [(gid, gdata["group_name"], len(gdata["members"])) 
				for gid, gdata in self.groups.items()]
	
	def get_group_details(self, group_id):
		"""Get detailed information about a group"""
		if group_id not in self.groups:
			return None
		
		group = self.groups[group_id]
		return {
			"id": group_id,
			"name": group["group_name"],
			"members": group["members"],
			"creator": group["creator"],
			"created": group["created_timestamp"],
			"messages": group["messages"]
		}
	
	def get_group_member_ips(self, group_id):
		"""Get IP addresses of group members for message sending"""
		if group_id not in self.groups:
			return []
		
		member_ips = []
		for member in self.groups[group_id]["members"]:
			if "@" in member:
				ip = member.split("@")[1]
				member_ips.append(ip)
		return member_ips
