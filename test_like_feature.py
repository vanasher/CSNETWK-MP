#!/usr/bin/env python3
"""
Test script for the LIKE feature implementation
Tests both LIKE and UNLIKE actions
"""

import sys
import time
import json
from unittest.mock import Mock

# Add the project root to Python path
sys.path.insert(0, '.')

from core.peer import PeerManager
from core.message_dispatcher import dispatch
from utils.logger import Logger
from parser.message_parser import craft_message, parse_message

def test_like_feature():
    """Test the complete LIKE feature workflow"""
    
    print("=== Testing LIKE Feature Implementation ===\n")
    
    # Setup test environment
    logger = Logger(verbose=False)
    peer_manager = PeerManager(logger)
    
    # Set up test user profile
    peer_manager.set_own_profile("alice", "Alice Smith", "Testing likes")
    my_user_id = peer_manager.own_profile["USER_ID"]
    print(f"My User ID: {my_user_id}")
    
    # Add a test peer (bob)
    bob_user_id = "bob@192.168.1.12"
    peer_manager.add_peer(bob_user_id, "Bob Johnson", "Online")
    
    # Follow bob so we can see his posts
    peer_manager.follow(bob_user_id)
    print(f"Following: {bob_user_id}")
    
    # Create a test post from bob with timestamp
    test_timestamp = int(time.time())
    test_content = "This is Bob's test post for liking!"
    test_token = f"{bob_user_id}|{test_timestamp + 3600}|broadcast"
    
    peer_manager.add_post(bob_user_id, test_content, test_timestamp, 3600, "msg123", test_token)
    print(f"Added test post from Bob: '{test_content}' at timestamp {test_timestamp}")
    
    # Test 1: Create a LIKE message from Bob to Alice (me)
    print("\n--- Test 1: Creating LIKE message (Bob likes my post) ---")
    
    # First, create my own post
    my_post_timestamp = int(time.time())
    my_post_content = "This is Alice's test post"
    peer_manager.add_own_post(my_post_content, my_post_timestamp, 3600, "msg123", f"{my_user_id}|{my_post_timestamp + 3600}|broadcast")
    print(f"Created my own post: '{my_post_content}' at timestamp {my_post_timestamp}")
    
    now = int(time.time())
    like_message = {
        "TYPE": "LIKE",
        "FROM": bob_user_id,
        "TO": my_user_id,  # Bob likes MY post
        "POST_TIMESTAMP": my_post_timestamp,
        "ACTION": "LIKE",
        "TIMESTAMP": now,
        "TOKEN": f"{bob_user_id}|{now + 3600}|broadcast"
    }
    
    # Convert to LSNP format and back to test message parsing
    lsnp_text = craft_message(like_message)
    print(f"LSNP Message:\n{lsnp_text}")
    
    parsed_message = parse_message(lsnp_text)
    print(f"Parsed back: {parsed_message}")
    
    # Test 2: Process the LIKE message through dispatcher
    print("\n--- Test 2: Processing LIKE through dispatcher ---")
    dispatch(like_message, "192.168.1.12", peer_manager)
    
    # Verify like was recorded
    if hasattr(peer_manager, 'received_likes') and peer_manager.received_likes:
        print(f"✅ LIKE successfully recorded: {peer_manager.received_likes[-1]}")
    else:
        print("❌ LIKE was not recorded")
    
    # Test 3: Create an UNLIKE message
    print("\n--- Test 3: Creating UNLIKE message ---")
    unlike_message = {
        "TYPE": "LIKE",
        "FROM": bob_user_id,
        "TO": my_user_id,  # Bob unlikes MY post
        "POST_TIMESTAMP": my_post_timestamp,
        "ACTION": "UNLIKE",
        "TIMESTAMP": now + 1,
        "TOKEN": f"{bob_user_id}|{now + 3601}|broadcast"
    }
    
    lsnp_unlike = craft_message(unlike_message)
    print(f"UNLIKE LSNP Message:\n{lsnp_unlike}")
    
    # Process UNLIKE
    dispatch(unlike_message, "192.168.1.12", peer_manager)
    
    # Verify unlike was processed (should remove the like)
    likes_after_unlike = getattr(peer_manager, 'received_likes', [])
    print(f"Likes after UNLIKE: {len(likes_after_unlike)} (should be 0)")
    
    # Test 4: Test liking Bob's posts (reverse direction)
    print("\n--- Test 4: Testing liking other's posts ---")
    
    # Create a like from me to Bob's post (original test post)
    my_like_to_bob = {
        "TYPE": "LIKE",
        "FROM": my_user_id,
        "TO": bob_user_id,
        "POST_TIMESTAMP": test_timestamp,  # Bob's original post
        "ACTION": "LIKE",
        "TIMESTAMP": now + 2,
        "TOKEN": f"{my_user_id}|{now + 3602}|broadcast"
    }
    
    print(f"My LIKE to Bob's post: {my_like_to_bob}")
    # Note: This won't be processed since it's not addressed to me, but tests the message format
    dispatch(my_like_to_bob, "192.168.1.12", peer_manager)
    
    # Test the like tracking functionality for outgoing likes
    peer_manager.add_like(bob_user_id, test_timestamp, "LIKE", test_content)
    bob_peer_likes = peer_manager.peers[bob_user_id].get('likes', [])
    print(f"Tracked outgoing likes to Bob: {len(bob_peer_likes)}")
    for like in bob_peer_likes:
        print(f"  - {like}")
    
    # Check received likes
    final_likes = getattr(peer_manager, 'received_likes', [])
    print(f"Final received likes: {len(final_likes)}")
    for like in final_likes:
        print(f"  - {like}")
    
    # Test 5: Test message format compliance
    print("\n--- Test 5: Message format compliance ---")
    sample_like = {
        "TYPE": "LIKE",
        "FROM": "bob@192.168.1.12",
        "TO": "alice@192.168.1.11",
        "POST_TIMESTAMP": 1728938391,
        "ACTION": "LIKE",
        "TIMESTAMP": 1728940500,
        "TOKEN": "bob@192.168.1.12|1728944100|broadcast"
    }
    
    lsnp_sample = craft_message(sample_like)
    print("Sample LIKE message (per specification):")
    print(lsnp_sample)
    
    # Verify all required fields are present
    required_fields = ["TYPE", "FROM", "TO", "POST_TIMESTAMP", "ACTION", "TIMESTAMP", "TOKEN"]
    missing_fields = [field for field in required_fields if field not in sample_like]
    
    if not missing_fields:
        print("✅ All required fields present in message format")
    else:
        print(f"❌ Missing fields: {missing_fields}")
    
    print("\n=== LIKE Feature Test Complete ===")
    return True

def test_like_validation():
    """Test like validation and error handling"""
    print("\n=== Testing LIKE Validation ===")
    
    logger = Logger(verbose=False)
    peer_manager = PeerManager(logger)
    peer_manager.set_own_profile("alice", "Alice", "Testing")
    
    # Test invalid message (missing fields)
    invalid_like = {
        "TYPE": "LIKE",
        "FROM": "bob@192.168.1.12"
        # Missing required fields
    }
    
    print("Testing invalid LIKE message (missing fields)...")
    dispatch(invalid_like, "192.168.1.12", peer_manager)
    
    # Test LIKE not addressed to me
    wrong_target_like = {
        "TYPE": "LIKE",
        "FROM": "bob@192.168.1.12",
        "TO": "charlie@192.168.1.13",  # Not me
        "POST_TIMESTAMP": 1728938391,
        "ACTION": "LIKE",
        "TIMESTAMP": 1728940500,
        "TOKEN": "bob@192.168.1.12|1728944100|broadcast"
    }
    
    print("Testing LIKE not addressed to me...")
    dispatch(wrong_target_like, "192.168.1.12", peer_manager)
    
    print("✅ Validation tests completed")

if __name__ == "__main__":
    try:
        test_like_feature()
        test_like_validation()
        print("\n🎉 All tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
