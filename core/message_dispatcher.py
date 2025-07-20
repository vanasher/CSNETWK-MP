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
		ttl = message.get("TTL")
		message_id = message.get("MESSAGE_ID")
		token = message.get("TOKEN")
		if user_id and content:
			peer_manager.add_post(user_id, content, ttl, message_id, token)

	elif msg_type == "DM":
		from_user = message.get("FROM")
		to_user = message.get("TO")
		timestamp = message.get("TIMESTAMP")
		content = message.get("CONTENT")
		message_id = message.get("MESSAGE_ID")
		token = message.get("TOKEN")
		if from_user and to_user and content:
			peer_manager.add_dm(from_user, content, timestamp, message_id, token)

			# sends ACK message back to sender after processing DM
			ack_message = {
				"TYPE": "ACK",
				"MESSAGE_ID": message_id,
				"STATUS": "RECEIVED"
			}
			send_message(ack_message, addr)

	elif msg_type == "PING":
		user_id = message.get("USER_ID")
		if peer_manager.logger.verbose:
			print(f"[PING] Received ping from {user_id}")

		# resgister peer if not already known (optional)
		if user_id and user_id not in peer_manager.peers:
				peer_manager.add_peer(user_id, user_id, "", None, None)

	elif msg_type == "ACK":
		message_id = message.get("MESSAGE_ID")
		status = message.get("STATUS")

		if peer_manager.logger.verbose:
			print(f"[ACK] Received ACK for message ID {message_id} with status {status}")

	elif msg_type == "FOLLOW":
		message_id = message.get("MESSAGE_ID")
		from_user = message.get("FROM")
		to_user = message.get("TO")
		timestamp = message.get("TIMESTAMP")
		token = message.get("TOKEN")

		if from_user and to_user:
			peer_manager.add_follower(message_id, to_user, from_user, timestamp, token)

	elif msg_type == "UNFOLLOW":
		from_user = message.get("FROM")
		to_user = message.get("TO")
		message_id = message.get("MESSAGE_ID")
		timestamp = message.get("TIMESTAMP")
		token = message.get("TOKEN")

		peer_manager.remove_follower(to_user, from_user, token, timestamp, message_id)

		if not peer_manager.logger.verbose:
			print(f"User {from_user} has unfollowed you")