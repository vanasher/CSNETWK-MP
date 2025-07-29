import unittest
import sys
import os

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parser.message_parser import parse_message, craft_message
from utils.logger import Logger

class TestLSNPProtocol(unittest.TestCase):
    """Minimal test suite for deployment"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.logger = Logger(verbose=False)
        
    def test_basic_functionality(self):
        """Basic test to ensure core functionality works"""
        # Test basic message parsing
        test_msg = "TYPE: PROFILE\nUSER_ID: test@192.168.1.1\nSTATUS: Online"
        parsed = parse_message(test_msg)
        self.assertEqual(parsed["TYPE"], "PROFILE")
        
        # Test basic message crafting
        test_dict = {"TYPE": "PROFILE", "USER_ID": "test@192.168.1.1"}
        crafted = craft_message(test_dict)
        self.assertTrue(crafted.endswith('\n\n'))

if __name__ == '__main__':
    unittest.main()