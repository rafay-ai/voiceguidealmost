#!/usr/bin/env python3
"""
Chatbot Recommendation System Test
Tests the specific issue: chatbot should use user preferences instead of defaulting to "Student Biryani"
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any

class ChatbotRecommendationTester:
    def __init__(self, base_url="https://newuser-fix.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})

    def log_test(self, name: str, success: bool, details: str = ""):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED {details}")
        else:
            print(f"❌ {name} - FAILED {details}")
        return success

    def run_api_test(self, name: str, method: str, endpoint: str, expected_status: int, 
                     data: Dict = None, headers: Dict = None) -> tuple:
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        test_headers = self.session.headers.copy()
        if headers:
            test_headers.update(headers)
        
        try:
            if method == 'GET':
                response = self.session.get(url, headers=test_headers)
            elif method == 'POST':
                response = self.session.post(url, json=data, headers=test_headers)
            elif method == 'PUT':
                response = self.session.put(url, json=data, headers=test_headers)
            elif method == 'DELETE':
                response = self.session.delete(url, headers=test_headers)
            else:
                raise ValueError(f"Unsupported method: {method}")

            success = response.status_code == expected_status
            details = f"Status: {response.status_code}"
            
            if not success:
                try:
                    error_detail = response.json()
                    details += f", Error: {error_detail}"
                except:
                    details += f", Response: {response.text[:200]}"
            
            self.log_test(name, success, details)
            
            return success, response.json() if success and response.content else {}

        except Exception as e:
            self.log_test(name, False, f"Exception: {str(e)}")
            return False, {}

    def setup_test_user(self):
        """Register and setup test user with specific preferences"""
        timestamp = datetime.now().strftime('%H%M%S')
        test_user_data = {
            "username": f"testuser_{timestamp}",
            "email": f"testuser_{timestamp}@example.com",
            "password": "test123"
        }
        
        success, response = self.run_api_test(
            "Register Test User",
            "POST",
            "api/auth/register",
            200,
            test_user_data
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.user_id = response['user']['id']
            self.session.headers['Authorization'] = f'Bearer {self.token}'
            print(f"   📝 Registered user: {response['user']['username']}")
            return True
        
        return False

    def set_user_preferences(self, favorite_cuisines, spice_preference="mild"):
        """Set user preferences to specific cuisines"""
        if not self.token:
            return self.log_test("Set User Preferences", False, "No authentication token")
        
        preferences_data = {
            "favorite_cuisines": favorite_cuisines,
            "dietary_restrictions": [],
            "spice_preference": spice_preference
        }
        
        success, response = self.run_api_test(
            f"Set User Preferences to {favorite_cuisines}",
            "PUT",
            "api/user/preferences",
            200,
            preferences_data
        )
        
        if success:
            print(f"   📝 Set preferences: {favorite_cuisines}, spice: {spice_preference}")
        
        return success

    def test_general_recommendation(self, message, expected_cuisines):
        """Test general recommendation requests"""
        if not self.token:
            return self.log_test(f"General Recommendation: '{message}'", False, "No authentication token")
        
        chat_data = {
            "message": message,
            "user_id": self.user_id
        }
        
        success, response = self.run_api_test(
            f"Chat: '{message}'",
            "POST",
            "api/chat",
            200,
            chat_data
        )
        
        if not success:
            return False
        
        # Check if recommended_items are returned
        recommended_items = response.get('recommended_items', [])
        show_order_card = response.get('show_order_card', False)
        
        if not recommended_items:
            return self.log_test(f"Items for '{message}'", False, "No recommended_items returned")
        
        if not show_order_card:
            return self.log_test(f"Order Card for '{message}'", False, "show_order_card is False")
        
        # Check if items match expected cuisines
        cuisine_match = False
        item_details = []
        
        for item in recommended_items:
            item_name = item.get('name', 'Unknown')
            item_tags = item.get('tags', [])
            item_category = item.get('category', '')
            restaurant_name = item.get('restaurant_name', 'Unknown')
            
            item_details.append(f"{item_name} ({restaurant_name})")
            
            # Check if item matches any expected cuisine
            for cuisine in expected_cuisines:
                if (cuisine.lower() in item_name.lower() or 
                    cuisine.lower() in item_category.lower() or
                    any(cuisine.lower() in tag.lower() for tag in item_tags)):
                    cuisine_match = True
                    break
        
        # Check for "Student Biryani" specifically (the reported issue)
        has_student_biryani = any("student biryani" in item.get('name', '').lower() 
                                 for item in recommended_items)
        
        if has_student_biryani and "Pakistani" not in expected_cuisines:
            return self.log_test(f"No Student Biryani for '{message}'", False, 
                               f"Found Student Biryani when user prefers {expected_cuisines}")
        
        if cuisine_match:
            return self.log_test(f"Cuisine Match for '{message}'", True, 
                               f"Items: {', '.join(item_details[:2])}")
        else:
            return self.log_test(f"Cuisine Match for '{message}'", False, 
                               f"Items don't match {expected_cuisines}. Got: {', '.join(item_details[:2])}")

    def test_specific_cuisine_request(self, message, expected_cuisine):
        """Test specific cuisine requests"""
        if not self.token:
            return self.log_test(f"Specific Cuisine: '{message}'", False, "No authentication token")
        
        chat_data = {
            "message": message,
            "user_id": self.user_id
        }
        
        success, response = self.run_api_test(
            f"Chat: '{message}'",
            "POST",
            "api/chat",
            200,
            chat_data
        )
        
        if not success:
            return False
        
        recommended_items = response.get('recommended_items', [])
        show_order_card = response.get('show_order_card', False)
        
        if not recommended_items:
            return self.log_test(f"Items for '{message}'", False, "No recommended_items returned")
        
        # Check if items match the specific cuisine
        cuisine_match = False
        item_details = []
        
        for item in recommended_items:
            item_name = item.get('name', 'Unknown')
            item_tags = item.get('tags', [])
            item_category = item.get('category', '')
            restaurant_name = item.get('restaurant_name', 'Unknown')
            
            item_details.append(f"{item_name} ({restaurant_name})")
            
            # Check if item matches expected cuisine
            if (expected_cuisine.lower() in item_name.lower() or 
                expected_cuisine.lower() in item_category.lower() or
                any(expected_cuisine.lower() in tag.lower() for tag in item_tags)):
                cuisine_match = True
        
        if cuisine_match:
            return self.log_test(f"Specific Cuisine '{expected_cuisine}' for '{message}'", True, 
                               f"Items: {', '.join(item_details[:2])}")
        else:
            return self.log_test(f"Specific Cuisine '{expected_cuisine}' for '{message}'", False, 
                               f"Items don't match {expected_cuisine}. Got: {', '.join(item_details[:2])}")

    def test_response_quality(self, message, expected_keywords):
        """Test that response text is appropriate"""
        if not self.token:
            return self.log_test(f"Response Quality: '{message}'", False, "No authentication token")
        
        chat_data = {
            "message": message,
            "user_id": self.user_id
        }
        
        success, response = self.run_api_test(
            f"Response Quality: '{message}'",
            "POST",
            "api/chat",
            200,
            chat_data
        )
        
        if not success:
            return False
        
        ai_response = response.get('response', '')
        
        # Check if response contains expected keywords
        keyword_match = any(keyword.lower() in ai_response.lower() for keyword in expected_keywords)
        
        if keyword_match:
            return self.log_test(f"Response Keywords for '{message}'", True, 
                               f"Response: {ai_response[:50]}...")
        else:
            return self.log_test(f"Response Keywords for '{message}'", False, 
                               f"Expected {expected_keywords}, got: {ai_response[:50]}...")

    def run_chatbot_recommendation_tests(self):
        """Run comprehensive chatbot recommendation tests"""
        print("🤖 Starting Chatbot Recommendation System Testing")
        print("=" * 60)
        
        # Setup Phase
        print("\n🔧 SETUP PHASE")
        if not self.setup_test_user():
            print("❌ Failed to setup test user. Aborting tests.")
            return False
        
        # Set user preferences to Japanese, Thai, Desserts (as per the issue report)
        if not self.set_user_preferences(["Japanese", "Thai", "Desserts"], "mild"):
            print("❌ Failed to set user preferences. Aborting tests.")
            return False
        
        # Test General Recommendations (Core Issue)
        print("\n🍽️ GENERAL RECOMMENDATION TESTS (Core Issue)")
        self.test_general_recommendation("I'm hungry", ["Japanese", "Thai", "Desserts"])
        self.test_general_recommendation("recommend me something", ["Japanese", "Thai", "Desserts"])
        self.test_general_recommendation("what should I eat?", ["Japanese", "Thai", "Desserts"])
        
        # Test Specific Cuisine Requests
        print("\n🎯 SPECIFIC CUISINE TESTS")
        self.test_specific_cuisine_request("show me desserts", "Desserts")
        self.test_specific_cuisine_request("japanese food please", "Japanese")
        self.test_specific_cuisine_request("thai food", "Thai")
        self.test_specific_cuisine_request("I want biryani", "Pakistani")
        
        # Test Response Quality
        print("\n💬 RESPONSE QUALITY TESTS")
        self.test_response_quality("show me desserts", ["dessert", "sweet", "cake"])
        self.test_response_quality("japanese food please", ["japanese", "sushi"])
        self.test_response_quality("thai food", ["thai", "curry"])
        
        # Test with Different User Preferences
        print("\n🔄 DIFFERENT PREFERENCES TEST")
        if self.set_user_preferences(["Pakistani", "Chinese", "BBQ"], "medium"):
            self.test_general_recommendation("I'm hungry", ["Pakistani", "Chinese", "BBQ"])
        
        # Final results
        print("\n" + "=" * 60)
        print(f"🏁 CHATBOT TESTING COMPLETE")
        print(f"📊 Results: {self.tests_passed}/{self.tests_run} tests passed")
        print(f"✅ Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All chatbot tests passed! Recommendation system is working correctly.")
            return True
        elif self.tests_passed / self.tests_run >= 0.8:
            print("⚠️  Most chatbot tests passed. Minor issues detected.")
            return True
        else:
            print("❌ Multiple chatbot test failures. Recommendation system has significant issues.")
            return False

def main():
    tester = ChatbotRecommendationTester()
    success = tester.run_chatbot_recommendation_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())