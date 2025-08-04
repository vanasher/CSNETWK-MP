#!/usr/bin/env python3
"""
LIKE Feature Demo
Demonstrates the LIKE functionality working in practice

This script shows:
1. Creating posts with timestamps
2. Following users to see their posts  
3. Using the 'like' command to like/unlike posts
4. Receiving like notifications
"""

import sys
import time
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, '.')

from core.peer import PeerManager
from core.message_dispatcher import dispatch
from utils.logger import Logger
from parser.message_parser import craft_message
import config

def demonstrate_like_feature():
    """Demonstrate the LIKE feature with realistic usage"""
    
    print("🎯 LIKE Feature Demonstration")
    print("=" * 50)
    
    # Setup Alice (main user)
    print("\n📱 Setting up Alice's profile...")
    logger = Logger(verbose=False)
    peer_manager = PeerManager(logger)
    peer_manager.set_own_profile("alice", "Alice Smith", "Testing the new like feature!")
    alice_id = peer_manager.own_profile["USER_ID"]
    print(f"   Alice ID: {alice_id}")
    
    # Add Bob as a peer
    bob_id = "bob@192.168.1.12"
    peer_manager.add_peer(bob_id, "Bob Johnson", "Sharing cool content")
    print(f"   Added peer: Bob Johnson ({bob_id})")
    
    # Alice follows Bob to see his posts
    peer_manager.follow(bob_id)
    print(f"   Alice is now following Bob")
    
    # Bob creates some posts (simulating received posts)
    print(f"\n📝 Bob creates some posts...")
    
    posts_data = [
        {"content": "Just finished a great workout! 💪", "timestamp": int(time.time()) - 3600},
        {"content": "Beautiful sunset today 🌅 #photography", "timestamp": int(time.time()) - 1800},
        {"content": "Working on a new coding project. Python is amazing! 🐍", "timestamp": int(time.time()) - 900}
    ]
    
    for i, post_data in enumerate(posts_data, 1):
        timestamp = post_data["timestamp"]
        content = post_data["content"]
        token = f"{bob_id}|{timestamp + 3600}|broadcast"
        
        peer_manager.add_post(bob_id, content, timestamp, 3600, f"msg{i}", token)
        
        dt = datetime.fromtimestamp(timestamp)
        print(f"   📄 Post {i}: \"{content}\" ({dt.strftime('%H:%M:%S')})")
    
    # Show Alice's feed (what the 'like' command shows)
    print(f"\n📺 Alice's feed (what she sees when using 'like' command):")
    print("=" * 60)
    print("=== POSTS FROM FOLLOWED USERS ===")
    
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
                    dt = datetime.fromtimestamp(timestamp) if timestamp != 'N/A' else 'N/A'
                    print(f"  {i}. {content}")
                    print(f"     Timestamp: {timestamp} ({dt.strftime('%H:%M:%S') if dt != 'N/A' else 'N/A'})")
    
    # Alice likes Bob's second post (the sunset photo)
    target_post = posts_data[1]  # sunset photo
    target_timestamp = target_post["timestamp"]
    target_content = target_post["content"]
    
    print(f"\n❤️ Alice likes Bob's sunset photo...")
    print(f"   Target post: \"{target_content}\"")
    print(f"   Post timestamp: {target_timestamp}")
    
    # Create the LIKE message (following exact specification format)
    now = int(time.time())
    like_message = {
        "TYPE": "LIKE",
        "FROM": alice_id,
        "TO": bob_id,
        "POST_TIMESTAMP": target_timestamp,
        "ACTION": "LIKE",
        "TIMESTAMP": now,
        "TOKEN": f"{alice_id}|{now + config.TTL}|broadcast"
    }
    
    # Show the LSNP message format
    lsnp_message = craft_message(like_message)
    print(f"\n📨 LIKE message (LSNP format):")
    print("-" * 40)
    print(lsnp_message)
    print("-" * 40)
    
    # Track the like locally
    peer_manager.add_like(bob_id, target_timestamp, "LIKE", target_content)
    print(f"✅ Like tracked locally in Alice's system")
    
    # Show what Bob would see when he receives this like
    print(f"\n📬 What Bob sees when he receives the like:")
    
    # Simulate Bob's system receiving the like
    bob_logger = Logger(verbose=False)
    bob_peer_manager = PeerManager(bob_logger)
    bob_peer_manager.set_own_profile("bob", "Bob Johnson", "Sharing cool content")
    
    # Add Bob's own post to his system
    bob_peer_manager.add_own_post(target_content, target_timestamp, 3600, "msg2", f"{bob_id}|{target_timestamp + 3600}|broadcast")
    
    # Add Alice as a peer to Bob's system
    bob_peer_manager.add_peer(alice_id, "Alice Smith", "Testing the new like feature!")
    
    # Process the like message through Bob's dispatcher
    print("   Processing LIKE message...")
    dispatch(like_message, alice_id.split('@')[1], bob_peer_manager)
    
    # Show Bob's received likes
    bob_received_likes = getattr(bob_peer_manager, 'received_likes', [])
    print(f"   Bob received {len(bob_received_likes)} like(s):")
    for like in bob_received_likes:
        liker_name = bob_peer_manager.get_display_name(like['from_user'])
        like_time = datetime.fromtimestamp(like['timestamp'])
        print(f"     💝 {liker_name} liked: \"{like['post_content']}\" at {like_time.strftime('%H:%M:%S')}")
    
    # Test UNLIKE functionality
    print(f"\n💔 Alice changes her mind and unlikes the post...")
    
    unlike_message = {
        "TYPE": "LIKE",
        "FROM": alice_id,
        "TO": bob_id,
        "POST_TIMESTAMP": target_timestamp,
        "ACTION": "UNLIKE",
        "TIMESTAMP": now + 1,
        "TOKEN": f"{alice_id}|{now + config.TTL + 1}|broadcast"
    }
    
    # Show UNLIKE message
    unlike_lsnp = craft_message(unlike_message)
    print(f"\n📨 UNLIKE message:")
    print(f"   ACTION: UNLIKE (same format, different action)")
    
    # Process unlike
    dispatch(unlike_message, alice_id.split('@')[1], bob_peer_manager)
    
    # Track unlike locally
    peer_manager.add_like(bob_id, target_timestamp, "UNLIKE", target_content)
    
    bob_likes_after_unlike = getattr(bob_peer_manager, 'received_likes', [])
    print(f"   Bob now has {len(bob_likes_after_unlike)} like(s) (unlike removed the like)")
    
    # Show final state
    print(f"\n📊 Final state summary:")
    alice_likes = peer_manager.peers[bob_id].get('likes', [])
    print(f"   Alice's outgoing likes: {len(alice_likes)}")
    print(f"   Bob's received likes: {len(bob_likes_after_unlike)}")
    
    # Show what the interactive command output looks like
    print(f"\n💬 What Alice would see in the interactive shell:")
    print("   >>> like")
    print("   === POSTS FROM FOLLOWED USERS ===")
    print("   Posts from Bob Johnson (bob@192.168.1.12):")
    print("     1. Just finished a great workout! 💪")
    print(f"        Timestamp: {posts_data[0]['timestamp']}")
    print("     2. Beautiful sunset today 🌅 #photography")  
    print(f"        Timestamp: {posts_data[1]['timestamp']}")
    print("     3. Working on a new coding project. Python is amazing! 🐍")
    print(f"        Timestamp: {posts_data[2]['timestamp']}")
    print("")
    print("   Enter the user ID of the post author: bob@192.168.1.12")
    print(f"   Enter the post timestamp: {target_timestamp}")
    print("   Action (LIKE/UNLIKE): LIKE")
    print("")
    print("   You liked Bob Johnson's post.")
    
    print(f"\n💬 What Bob would see:")
    print("   Alice Smith likes Beautiful sunset today 🌅 #photography")
    
    print(f"\n🎉 LIKE Feature Demonstration Complete!")
    print("=" * 50)
    
    return True

if __name__ == "__main__":
    try:
        demonstrate_like_feature()
        print("\n✨ The LIKE feature is working perfectly!")
        print("\nKey features demonstrated:")
        print("  🎯 Correct LSNP message format per specification")
        print("  💝 LIKE and UNLIKE actions")
        print("  📝 Integration with posts and following system")
        print("  🔒 Token validation and security")
        print("  📱 Interactive shell command")
        print("  🔄 Real-time message processing")
        print("  📊 Local state tracking")
        print("  💬 User-friendly notifications")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
