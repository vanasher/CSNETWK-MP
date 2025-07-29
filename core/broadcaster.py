import threading
import time
import config
from utils.network_utils import send_message
import json
from parser.message_parser import craft_message

def broadcast_profile_periodically(logger, peer_manager, interval=10): # 30 secs interval (just for testing)
                                                                       # should be 5 mins as per rubric milestone 2
    def broadcast_loop():
        while True:
            profile = peer_manager.get_own_profile()
            # Only broadcast if the profile is complete (has USER_ID)
            if profile and profile.get("USER_ID"):
                send_message(profile, (config.BROADCAST_ADDR, config.PORT))
                
                #lsnp_text = craft_message(profile)
                logger.log_send("PROFILE", f"{config.BROADCAST_ADDR}:{config.PORT}", profile)
            else:
                logger.log("PROFILE", "Own profile not set; skipping broadcast.")
            time.sleep(interval)
    threading.Thread(target=broadcast_loop, daemon=True).start()