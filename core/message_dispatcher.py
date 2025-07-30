from utils.network_utils import send_message

# Routes incoming LSNP messages to appropriate PeerManager handlers based on the message type
def dispatch(message: dict, addr: str, peer_manager):
	msg_type = message.get("TYPE")

	if msg_type == "PROFILE":
		user_id = message.get("USER_ID")
		name = message.get("DISPLAY_NAME")
		status = message.get("STATUS")
		avatar_type = message.get("AVATAR_TYPE")
		avatar_encoding = message.get("AVATAR_ENCODING")
		avatar_data = message.get("AVATAR_DATA")
		if user_id and name:
			peer_manager.add_peer(user_id, name, status, avatar_type, avatar_encoding, avatar_data)

	elif msg_type == "POST":
		user_id = message.get("USER_ID")
		content = message.get("CONTENT")
		timestamp = message.get("TIMESTAMP")
		ttl = int(message.get("TTL", 3600)) # default is 3600 per RFC
		message_id = message.get("MESSAGE_ID")
		token = message.get("TOKEN")
		if user_id and content:
			# Only store posts from users we're following
			if peer_manager.is_following(user_id):
				peer_manager.add_post(user_id, content, timestamp, ttl, message_id)
				peer_manager.logger.log("POST", f"Received post from {user_id}: {content[:50]}...")
			else:
				peer_manager.logger.log("POST", f"Ignored post from unfollowed user: {user_id}")

	elif msg_type == "DM":
		from_user = message.get("FROM")
		to_user = message.get("TO")
		timestamp = message.get("TIMESTAMP")
		content = message.get("CONTENT")
		message_id = message.get("MESSAGE_ID")
		token = message.get("TOKEN")

		# validate input fields
		if not (from_user and to_user and content and message_id and timestamp and token):
			peer_manager.logger.log_drop("Malformed DM message.")
			return

		# makes sure this message is intended for the user
		my_user_id = peer_manager.own_profile.get("USER_ID")
		if to_user != my_user_id:
			peer_manager.logger.log_drop(f"Ignored DM not addressed to me: {to_user}")
			return

		# store the DM
		peer_manager.add_dm(from_user, content, timestamp, message_id, token)
		# peer_manager.logger.log("DM", f"Received DM from {from_user}: {content[:50]}...")

	elif msg_type == "PING":
		user_id = message.get("USER_ID")
		# if peer_manager.logger.verbose:
		# 	print(f"[PING] Received ping from {user_id}")

		# resgister peer if not already known (optional)
		# if user_id and user_id not in peer_manager.peers:
		# 		peer_manager.add_peer(user_id, user_id, "", None, None)

	elif msg_type == "ACK":
		message_id = message.get("MESSAGE_ID")
		status = message.get("STATUS")

		# if peer_manager.logger.verbose:
		# 	print(f"[ACK] Received ACK for message ID {message_id} with status {status}")

	elif msg_type == "FOLLOW":
		message_id = message.get("MESSAGE_ID")
		from_user = message.get("FROM")
		to_user = message.get("TO")
		timestamp = message.get("TIMESTAMP")
		token = message.get("TOKEN")

		if from_user and to_user:
			peer_manager.add_follower(to_user, from_user, token, timestamp, message_id)
			peer_manager.logger.log("FOLLOW", f"{from_user} is now following {to_user}")

	elif msg_type == "UNFOLLOW":
		from_user = message.get("FROM")
		to_user = message.get("TO")
		message_id = message.get("MESSAGE_ID")
		timestamp = message.get("TIMESTAMP")
		token = message.get("TOKEN")

		peer_manager.remove_follower(to_user, from_user, token, timestamp, message_id)

		# Only show unfollow notification in non-verbose mode
		if not peer_manager.logger.verbose:
			print(f"User {from_user} has unfollowed you")

	elif msg_type == "LIKE":
		from_user = message.get("FROM")
		to_user = message.get("TO")
		post_timestamp = message.get("POST_TIMESTAMP")
		action = message.get("ACTION")
		timestamp = message.get("TIMESTAMP")
		token = message.get("TOKEN")

		# Validate required fields
		if not (from_user and to_user and post_timestamp and action and timestamp and token):
			peer_manager.logger.log_drop("Malformed LIKE message.")
			return

		# Check if this like is for our post
		my_user_id = peer_manager.own_profile.get("USER_ID")
		if to_user != my_user_id:
			peer_manager.logger.log_drop(f"Ignored LIKE not for my post: {to_user}")
			return

		# Validate action
		if action not in ["LIKE", "UNLIKE"]:
			peer_manager.logger.log_drop(f"Invalid LIKE action: {action}")
			return

		# Add the like/unlike to the post
		success = peer_manager.add_like_to_post(to_user, post_timestamp, from_user, action, timestamp, token)
		if success:
			peer_manager.logger.log("LIKE", f"Received {action.lower()} from {from_user} on post at timestamp {post_timestamp}")
			
			# Show notification in non-verbose mode
			if not peer_manager.logger.verbose:
				liker_name = peer_manager.get_display_name(from_user)
				
				# Find the post content for the notification
				post_content = ""
				if to_user in peer_manager.peers:
					for post in peer_manager.peers[to_user].get('posts', []):
						if str(post.get('timestamp')) == str(post_timestamp):
							post_content = post.get('content', '')[:50]  # First 50 chars
							if len(post.get('content', '')) > 50:
								post_content += "..."
							break
				
				if action == "LIKE":
					print(f"\n{liker_name} likes your post: {post_content}")
				else:
					print(f"\n{liker_name} unliked your post: {post_content}")