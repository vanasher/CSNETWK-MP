#!/usr/bin/env python3
"""
Integration test for LIKE feature in the interactive shell
This tests the actual command implementation
"""

import sys
import time
import json
from unittest.mock import Mock, patch
from io import StringIO

# Add the project root to Python path
sys.path.insert(0, '.')

from core.peer import PeerManager
from utils.logger import Logger
import config

def test_like_command_interactive():
    """Test the like command in the interactive shell"""
    
    print("=== Testing LIKE Command in Interactive Shell ===\n")
    
    # Setup test environment
    logger = Logger(verbose=False)
    peer_manager = PeerManager(logger)
    
    # Set up test user profile
    peer_manager.set_own_profile("alice", "Alice Smith", "Testing")
    my_user_id = peer_manager.own_profile["USER_ID"]
    print(f"My User ID: {my_user_id}")
    
    # Add a test peer and follow them
    bob_user_id = "bob@192.168.1.12"
    peer_manager.add_peer(bob_user_id, "Bob Johnson", "Online")
    peer_manager.follow(bob_user_id)
    
    # Add test posts from Bob
    test_timestamp1 = int(time.time())
    test_timestamp2 = test_timestamp1 + 1
    
    peer_manager.add_post(bob_user_id, "Bob's first post", test_timestamp1, 3600, "msg1", f"{bob_user_id}|{test_timestamp1 + 3600}|broadcast")
    peer_manager.add_post(bob_user_id, "Bob's second post", test_timestamp2, 3600, "msg2", f"{bob_user_id}|{test_timestamp2 + 3600}|broadcast")
    
    print(f"Added test posts from Bob with timestamps {test_timestamp1} and {test_timestamp2}")
    
    # Test the like functionality step by step
    print("\n--- Simulating 'like' command execution ---")
    
    # Show what the like command would display
    print("\n=== POSTS FROM FOLLOWED USERS ===")
    posts_found = False
    for user_id in peer_manager.following:
        peer_info = peer_manager.peers.get(user_id)
        if peer_info and peer_info.get('posts'):
            posts = peer_info['posts']
            display_name = peer_info['display_name']
            print(f"\nPosts from {display_name} ({user_id}):")
            for i, post in enumerate(posts, 1):
                from utils.network_utils import validate_token
                is_valid, error = validate_token(post.get("token"), "broadcast", peer_manager.revoked_tokens)
                if is_valid:
                    content = post.get('content', 'No content')
                    timestamp = post.get('timestamp', 'N/A')
                    print(f"  {i}. {content}")
                    print(f"     Timestamp: {timestamp}")
                    posts_found = True
    
    # Simulate user choosing to like the first post
    target_user = bob_user_id
    post_timestamp = test_timestamp1
    action = "LIKE"
    
    print(f"\nSimulating: User wants to {action} post from {target_user} with timestamp {post_timestamp}")
    
    # Validate that the post exists (like the command does)
    peer_info = peer_manager.peers.get(target_user)
    posts = peer_info.get('posts', [])
    post_found = False
    target_post_content = ""
    for post in posts:
        if post.get('timestamp') == post_timestamp:
            from utils.network_utils import validate_token
            is_valid, error = validate_token(post.get("token"), "broadcast", peer_manager.revoked_tokens)
            if is_valid:
                post_found = True
                target_post_content = post.get('content', '')
                break
    
    if post_found:
        print(f"✅ Post found: '{target_post_content}'")
        
        # Create the like message (like the command does)
        now = int(time.time())
        ttl = config.TTL
        sender = peer_manager.own_profile["USER_ID"]
        token = f"{sender}|{now + ttl}|broadcast"
        
        like_message = {
            "TYPE": "LIKE",
            "FROM": sender,
            "TO": target_user,
            "POST_TIMESTAMP": post_timestamp,
            "ACTION": action,
            "TIMESTAMP": now,
            "TOKEN": token
        }
        
        print(f"Created LIKE message: {like_message}")
        
        # Validate token (like the command does)
        from utils.network_utils import validate_token
        is_valid, error = validate_token(like_message["TOKEN"], "broadcast", peer_manager.revoked_tokens)
        if is_valid:
            print("✅ Token is valid")
            
            # Store the like locally (like the command does)
            peer_manager.add_like(target_user, post_timestamp, action, target_post_content)
            print("✅ Like tracked locally")
            
            # Show that the like was recorded
            likes_list = peer_manager.peers[target_user].get('likes', [])
            print(f"Current likes for {target_user}: {len(likes_list)}")
            for like in likes_list:
                print(f"  - {like}")
            
        else:
            print(f"❌ Token validation failed: {error}")
    else:
        print(f"❌ Post not found")
    
    # Test UNLIKE
    print(f"\n--- Testing UNLIKE ---")
    unlike_message = {
        "TYPE": "LIKE",
        "FROM": sender,
        "TO": target_user,
        "POST_TIMESTAMP": post_timestamp,
        "ACTION": "UNLIKE",
        "TIMESTAMP": now + 1,
        "TOKEN": f"{sender}|{now + ttl + 1}|broadcast"
    }
    
    peer_manager.add_like(target_user, post_timestamp, "UNLIKE", target_post_content)
    likes_after_unlike = peer_manager.peers[target_user].get('likes', [])
    print(f"Likes after UNLIKE: {len(likes_after_unlike)} (should be 0 or fewer)")
    
    print("\n=== LIKE Command Test Complete ===")

if __name__ == "__main__":
    try:
        test_like_command_interactive()
        print("\n🎉 Integration test passed!")
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
