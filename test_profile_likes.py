#!/usr/bin/env python3
"""
Comprehensive test for Profile Picture and Likes functionality (10 pts)
Tests AVATAR fields in PROFILE messages and LIKE actions for posts.
"""

import sys
import os
import base64
import time
import random

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parser.message_parser import parse_message, craft_message
from utils.image_utils import encode_image_to_base64, decode_base64_to_image, display_avatar_info
from utils.logger import Logger
from core.peer import PeerManager
from core.message_dispatcher import dispatch
from utils.network_utils import get_local_ip

def create_test_image():
    """Create a small test image for testing"""
    # Create a simple 1x1 PNG image (minimal valid PNG)
    png_data = base64.b64decode(
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=='
    )
    test_image_path = os.path.join(os.path.dirname(__file__), 'test_avatar.png')
    with open(test_image_path, 'wb') as f:
        f.write(png_data)
    return test_image_path

def test_profile_with_avatar():
    """Test 1: PROFILE message with AVATAR fields"""
    print("🔍 Test 1: PROFILE message with AVATAR fields")
    
    # Create test image
    test_image_path = create_test_image()
    
    try:
        # Encode image
        mime_type, base64_data, size_bytes = encode_image_to_base64(test_image_path)
        
        # Create PROFILE message with avatar
        profile_msg = {
            "TYPE": "PROFILE",
            "USER_ID": "testuser@192.168.1.100",
            "DISPLAY_NAME": "Test User",
            "STATUS": "Testing with avatar!",
            "AVATAR_TYPE": mime_type,
            "AVATAR_ENCODING": "base64",
            "AVATAR_DATA": base64_data
        }
        
        # Test message crafting and parsing
        crafted = craft_message(profile_msg)
        parsed = parse_message(crafted)
        
        # Verify all AVATAR fields are present
        assert parsed.get("AVATAR_TYPE") == mime_type, "AVATAR_TYPE not preserved"
        assert parsed.get("AVATAR_ENCODING") == "base64", "AVATAR_ENCODING not preserved"
        assert parsed.get("AVATAR_DATA") == base64_data, "AVATAR_DATA not preserved"
        
        print("✅ PROFILE with AVATAR fields: PASSED")
        print(f"   - AVATAR_TYPE: {parsed.get('AVATAR_TYPE')}")
        print(f"   - AVATAR_ENCODING: {parsed.get('AVATAR_ENCODING')}")
        print(f"   - Avatar size: {size_bytes} bytes")
        
        return True
        
    except Exception as e:
        print(f"❌ PROFILE with AVATAR fields: FAILED - {e}")
        return False
    finally:
        # Clean up test image
        if os.path.exists(test_image_path):
            os.remove(test_image_path)

def test_avatar_display():
    """Test 2: Avatar display in non-verbose mode"""
    print("\n🔍 Test 2: Avatar display in non-verbose mode")
    
    try:
        logger = Logger(verbose=False)
        
        # Test with avatar
        profile_with_avatar = {
            "TYPE": "PROFILE",
            "DISPLAY_NAME": "User With Avatar",
            "STATUS": "Has profile picture",
            "AVATAR_TYPE": "image/png",
            "AVATAR_DATA": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
        }
        
        # Test avatar info display
        avatar_info = display_avatar_info(
            profile_with_avatar.get("AVATAR_TYPE"),
            profile_with_avatar.get("AVATAR_DATA")
        )
        
        assert "Profile picture" in avatar_info, "Avatar info not generated correctly"
        assert "image/png" in avatar_info, "MIME type not in avatar info"
        
        print("✅ Avatar display functionality: PASSED")
        print(f"   - Avatar info: {avatar_info}")
        
        return True
        
    except Exception as e:
        print(f"❌ Avatar display functionality: FAILED - {e}")
        return False

def test_like_message_creation():
    """Test 3: LIKE message creation and parsing"""
    print("\n🔍 Test 3: LIKE message creation and parsing")
    
    try:
        timestamp = int(time.time())
        post_timestamp = timestamp - 100  # Post was created 100 seconds ago
        
        like_msg = {
            "TYPE": "LIKE",
            "FROM": "alice@192.168.1.100",
            "TO": "bob@192.168.1.101",
            "POST_TIMESTAMP": str(post_timestamp),
            "ACTION": "LIKE",
            "TIMESTAMP": timestamp,
            "TOKEN": f"alice@192.168.1.100|{timestamp + 3600}|broadcast"
        }
        
        # Test message crafting and parsing
        crafted = craft_message(like_msg)
        parsed = parse_message(crafted)
        
        # Verify all LIKE fields are present
        assert parsed.get("TYPE") == "LIKE", "LIKE type not preserved"
        assert parsed.get("FROM") == "alice@192.168.1.100", "FROM not preserved"
        assert parsed.get("TO") == "bob@192.168.1.101", "TO not preserved"
        assert parsed.get("POST_TIMESTAMP") == str(post_timestamp), "POST_TIMESTAMP not preserved"
        assert parsed.get("ACTION") == "LIKE", "ACTION not preserved"
        assert parsed.get("TIMESTAMP") == str(timestamp), "TIMESTAMP not preserved"
        
        print("✅ LIKE message creation: PASSED")
        print(f"   - POST_TIMESTAMP: {parsed.get('POST_TIMESTAMP')}")
        print(f"   - ACTION: {parsed.get('ACTION')}")
        
        return True
        
    except Exception as e:
        print(f"❌ LIKE message creation: FAILED - {e}")
        return False

def test_like_functionality():
    """Test 4: LIKE functionality with peer manager"""
    print("\n🔍 Test 4: LIKE functionality with peer manager")
    
    try:
        logger = Logger(verbose=False)
        peer_manager = PeerManager(logger)
        
        # Set up own profile
        peer_manager.set_own_profile("testuser", "Test User", "Testing likes")
        
        # Add a peer with a post
        peer_manager.add_peer("alice@192.168.1.100", "Alice", "Hello world")
        post_timestamp = int(time.time()) - 100  # Post was created 100 seconds ago
        peer_manager.add_post("alice@192.168.1.100", "This is my first post!", post_timestamp, None, "post123")
        
        # Test adding a like using the new LIKE message format
        like_timestamp = int(time.time())
        success = peer_manager.add_like_to_post(
            "alice@192.168.1.100",    # post_author (corrected)
            str(post_timestamp),      # post_timestamp
            "bob@192.168.1.101",      # liker_id
            "LIKE",                   # action
            like_timestamp,           # timestamp
            "bob@192.168.1.101|token|broadcast"  # token
        )
        
        assert success, "Failed to add like to post"
        
        # Verify like was added
        alice_posts = peer_manager.peers["alice@192.168.1.100"]["posts"]
        post = next(p for p in alice_posts if p["timestamp"] == post_timestamp)
        
        assert len(post.get("likes", [])) == 1, "Like not added to post"
        assert post["likes"][0]["liker_id"] == "bob@192.168.1.101", "Incorrect liker ID"
        assert post["likes"][0]["action"] == "LIKE", "Incorrect like action"
        
        # Test unlike (should remove the like)
        unlike_timestamp = int(time.time())
        unlike_success = peer_manager.add_like_to_post(
            "alice@192.168.1.100",    # post_author
            str(post_timestamp),      # post_timestamp
            "bob@192.168.1.101",      # liker_id
            "UNLIKE",                 # action
            unlike_timestamp,         # timestamp
            "bob@192.168.1.101|token2|broadcast"  # token
        )
        
        assert unlike_success, "UNLIKE should succeed"
        assert len(post.get("likes", [])) == 0, "UNLIKE should remove the like"
        
        print("✅ LIKE functionality: PASSED")
        print(f"   - LIKE added successfully")
        print(f"   - UNLIKE removed like properly")
        
        return True
        
    except Exception as e:
        print(f"❌ LIKE functionality: FAILED - {e}")
        return False

def test_like_message_dispatch():
    """Test 5: LIKE message dispatch handling"""
    print("\n🔍 Test 5: LIKE message dispatch handling")
    
    try:
        logger = Logger(verbose=False)
        peer_manager = PeerManager(logger)
        
        # Set up own profile
        peer_manager.set_own_profile("bob", "Bob", "Testing dispatch", None, None, None)
        my_user_id = peer_manager.own_profile["USER_ID"]
        
        # Add myself as a peer to ensure posts structure exists
        peer_manager.add_peer(my_user_id, "Bob", "Testing dispatch")
        
        # Add own post with specific timestamp
        post_timestamp = int(time.time()) - 100
        peer_manager.add_post(my_user_id, "My test post", post_timestamp, None, "mypost123")
        
        # Create LIKE message using new specification format
        like_message = {
            "TYPE": "LIKE",
            "FROM": "alice@192.168.1.100",
            "TO": my_user_id,
            "POST_TIMESTAMP": str(post_timestamp),
            "ACTION": "LIKE",
            "TIMESTAMP": str(int(time.time())),
            "TOKEN": "alice@192.168.1.100|token|broadcast"
        }
        
        # Add the liker as a peer first
        peer_manager.add_peer("alice@192.168.1.100", "Alice", "Likes posts")
        
        # Dispatch the like message
        dispatch(like_message, "192.168.1.100", peer_manager)
        
        # Verify like was processed
        my_posts = peer_manager.peers[my_user_id]["posts"]
        my_post = next(p for p in my_posts if p["timestamp"] == post_timestamp)
        
        assert len(my_post.get("likes", [])) == 1, "LIKE message not processed"
        assert my_post["likes"][0]["liker_id"] == "alice@192.168.1.100", "Incorrect liker in processed like"
        assert my_post["likes"][0]["action"] == "LIKE", "Incorrect action in processed like"
        
        print("✅ LIKE message dispatch: PASSED")
        print(f"   - LIKE message processed correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ LIKE message dispatch: FAILED - {e}")
        return False

def test_avatar_handling_for_non_supporting_hosts():
    """Test 6: Avatar handling for non-supporting hosts"""
    print("\n🔍 Test 6: Avatar handling for non-supporting hosts")
    
    try:
        # Test that hosts can accept messages with AVATAR_* keys but ignore them
        profile_with_avatar = """TYPE: PROFILE
USER_ID: testuser@192.168.1.100
DISPLAY_NAME: Test User
STATUS: Has avatar
AVATAR_TYPE: image/png
AVATAR_ENCODING: base64
AVATAR_DATA: iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==

"""
        
        # Parse message (simulating non-supporting host)
        parsed = parse_message(profile_with_avatar)
        
        # Non-supporting host should still get basic profile info
        assert parsed.get("TYPE") == "PROFILE", "TYPE not parsed"
        assert parsed.get("USER_ID") == "testuser@192.168.1.100", "USER_ID not parsed"
        assert parsed.get("DISPLAY_NAME") == "Test User", "DISPLAY_NAME not parsed"
        assert parsed.get("STATUS") == "Has avatar", "STATUS not parsed"
        
        # AVATAR fields are present but can be ignored
        assert "AVATAR_TYPE" in parsed, "AVATAR_TYPE should be parseable"
        assert "AVATAR_ENCODING" in parsed, "AVATAR_ENCODING should be parseable"
        assert "AVATAR_DATA" in parsed, "AVATAR_DATA should be parseable"
        
        # Create profile without avatar fields (non-supporting host)
        basic_profile = {
            "TYPE": "PROFILE",
            "USER_ID": parsed.get("USER_ID"),
            "DISPLAY_NAME": parsed.get("DISPLAY_NAME"),
            "STATUS": parsed.get("STATUS")
            # AVATAR_* fields intentionally omitted
        }
        
        basic_crafted = craft_message(basic_profile)
        basic_parsed = parse_message(basic_crafted)
        
        assert basic_parsed.get("TYPE") == "PROFILE", "Basic profile type not preserved"
        assert "AVATAR_TYPE" not in basic_parsed, "AVATAR_TYPE should not be present in basic profile"
        
        print("✅ Avatar handling for non-supporting hosts: PASSED")
        print(f"   - Hosts can parse messages with AVATAR fields")
        print(f"   - Hosts can create messages without AVATAR fields")
        
        return True
        
    except Exception as e:
        print(f"❌ Avatar handling for non-supporting hosts: FAILED - {e}")
        return False

def test_large_avatar_rejection():
    """Test 7: Large avatar rejection (>20KB)"""
    print("\n🔍 Test 7: Large avatar rejection (>20KB)")
    
    try:
        # Create a large PNG file (simulate by creating large fake PNG data)
        # Create minimal PNG header + large data
        png_header = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==')
        large_data = png_header + b'A' * 25000  # Add 25KB of data to make it large
        
        test_image_path = os.path.join(os.path.dirname(__file__), 'large_test.png')
        with open(test_image_path, 'wb') as f:
            f.write(large_data)
        
        try:
            # This should raise an exception for large size
            encode_image_to_base64(test_image_path)
            print("❌ Large avatar rejection: FAILED - No exception raised for large file")
            return False
        except ValueError as e:
            if "too large" in str(e).lower():
                print("✅ Large avatar rejection: PASSED")
                print(f"   - Correctly rejected large avatar: {e}")
                return True
            else:
                print(f"❌ Large avatar rejection: FAILED - Wrong exception: {e}")
                return False
        finally:
            if os.path.exists(test_image_path):
                os.remove(test_image_path)
                
    except Exception as e:
        print(f"❌ Large avatar rejection: FAILED - {e}")
        return False

def run_all_tests():
    """Run all profile picture and likes functionality tests"""
    print("🧪 PROFILE PICTURE AND LIKES FUNCTIONALITY TEST SUITE")
    print("=" * 60)
    
    tests = [
        test_profile_with_avatar,
        test_avatar_display,
        test_like_message_creation,
        test_like_functionality,
        test_like_message_dispatch,
        test_avatar_handling_for_non_supporting_hosts,
        test_large_avatar_rejection
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
    
    print("\n" + "=" * 60)
    print(f"🎯 OVERALL RESULT: {passed}/{total} tests passed")
    
    if passed == total:
        print("🏆 PROFILE PICTURE AND LIKES FUNCTIONALITY CRITERIA MET (10/10 pts)")
        print("✅ AVATAR fields correctly implemented in PROFILE messages")
        print("✅ LIKE actions correctly implemented for posts")
        print("✅ Non-verbose mode shows profile pictures appropriately")
        print("✅ Non-supporting hosts can handle AVATAR fields")
    else:
        print("❌ Some tests failed - review implementation")
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
