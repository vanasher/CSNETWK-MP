# Routes incoming LSNP messages to appropriate PeerManager handlers based on the message type
def dispatch(message: dict, addr: str, peer_manager):
	msg_type = message.get("TYPE")

	if msg_type == "PROFILE":
		user_id = message.get("USER_ID")
		name = message.get("DISPLAY_NAME")
		status = message.get("STATUS")
		avatar_type = message.get("AVATAR_TYPE")
		avatar_data = message.get("AVATAR_DATA")
		if user_id and name:
			peer_manager.add_peer(user_id, name, status, avatar_type, avatar_data)

	elif msg_type == "POST":
		user_id = message.get("USER_ID")
		content = message.get("CONTENT")
		timestamp = message.get("TIMESTAMP")
		ttl = message.get("TTL")
		message_id = message.get("MESSAGE_ID")
		if user_id and content:
			peer_manager.add_post(user_id, content, timestamp, ttl, message_id)

	elif msg_type == "DM":
		from_user = message.get("FROM")
		to_user = message.get("TO")
		content = message.get("CONTENT")
		if from_user and to_user and content:
			peer_manager.add_dm(from_user, content)