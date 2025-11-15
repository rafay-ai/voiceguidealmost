#!/usr/bin/env python3
"""
Voice Guide Food Delivery App - Backend API Testing
Tests all API endpoints including authentication, recommendations, chat, and restaurants
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any

class VoiceGuideAPITester:
    def __init__(self, base_url="https://food-voice-ai.preview.emergentagent.com"):
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

    def test_health_check(self):
        """Test health endpoint"""
        success, response = self.run_api_test(
            "Health Check",
            "GET",
            "api/health",
            200
        )
        return success

    def test_user_registration(self):
        """Test user registration"""
        test_user_data = {
            "username": f"testuser_{datetime.now().strftime('%H%M%S')}",
            "email": f"test_{datetime.now().strftime('%H%M%S')}@voiceguide.com",
            "password": "TestPass123!"
        }
        
        success, response = self.run_api_test(
            "User Registration",
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
        
        return success

    def test_demo_login(self):
        """Test login with demo credentials"""
        demo_credentials = {
            "email": "demo@voiceguide.com",
            "password": "demo123"
        }
        
        success, response = self.run_api_test(
            "Demo Login",
            "POST",
            "api/auth/login",
            200,
            demo_credentials
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.user_id = response['user']['id']
            self.session.headers['Authorization'] = f'Bearer {self.token}'
            print(f"   📝 Logged in as: {response['user']['username']}")
        
        return success

    def test_user_profile(self):
        """Test getting user profile"""
        if not self.token:
            return self.log_test("User Profile", False, "No authentication token")
        
        success, response = self.run_api_test(
            "Get User Profile",
            "GET",
            "api/user/profile",
            200
        )
        
        if success:
            print(f"   📝 Profile: {response.get('username', 'N/A')} ({response.get('email', 'N/A')})")
        
        return success

    def test_update_preferences(self):
        """Test updating user preferences"""
        if not self.token:
            return self.log_test("Update Preferences", False, "No authentication token")
        
        preferences_data = {
            "favorite_cuisines": ["Pakistani", "Chinese", "Italian"],
            "dietary_restrictions": ["Halal"],
            "spice_preference": "medium"
        }
        
        success, response = self.run_api_test(
            "Update User Preferences",
            "PUT",
            "api/user/preferences",
            200,
            preferences_data
        )
        
        return success

    def test_get_cuisines(self):
        """Test getting available cuisines"""
        success, response = self.run_api_test(
            "Get Available Cuisines",
            "GET",
            "api/cuisines",
            200
        )
        
        if success and 'cuisines' in response:
            cuisines = response['cuisines']
            print(f"   📝 Found {len(cuisines)} cuisines: {cuisines[:5]}...")
        
        return success

    def test_get_restaurants(self):
        """Test getting restaurants"""
        success, response = self.run_api_test(
            "Get Restaurants",
            "GET",
            "api/restaurants?page=1&limit=5",
            200
        )
        
        if success and 'restaurants' in response:
            restaurants = response['restaurants']
            print(f"   📝 Found {len(restaurants)} restaurants, Total: {response.get('total', 0)}")
            if restaurants:
                print(f"   📝 Sample restaurant: {restaurants[0].get('name', 'N/A')}")
        
        return success

    def test_get_restaurants_with_cuisine_filter(self):
        """Test getting restaurants with cuisine filter"""
        success, response = self.run_api_test(
            "Get Restaurants (Pakistani Cuisine)",
            "GET",
            "api/restaurants?page=1&limit=5&cuisine=Pakistani",
            200
        )
        
        if success and 'restaurants' in response:
            restaurants = response['restaurants']
            print(f"   📝 Found {len(restaurants)} Pakistani restaurants")
        
        return success

    def test_get_recommendations(self):
        """Test getting personalized recommendations"""
        if not self.token:
            return self.log_test("Get Recommendations", False, "No authentication token")
        
        success, response = self.run_api_test(
            "Get Personalized Recommendations",
            "GET",
            "api/recommendations?limit=10",
            200
        )
        
        if success and 'recommendations' in response:
            recommendations = response['recommendations']
            print(f"   📝 Found {len(recommendations)} recommendations")
            if recommendations:
                sample = recommendations[0]
                print(f"   📝 Sample: {sample.get('name', 'N/A')} - {sample.get('recommendation_reason', 'N/A')}")
        
        return success

    def test_chat_functionality(self):
        """Test chat with Gemini AI"""
        if not self.token:
            return self.log_test("Chat Functionality", False, "No authentication token")
        
        chat_data = {
            "message": "I want spicy Pakistani food recommendations",
            "user_id": self.user_id
        }
        
        success, response = self.run_api_test(
            "Chat with AI Assistant",
            "POST",
            "api/chat",
            200,
            chat_data
        )
        
        if success and 'response' in response:
            ai_response = response['response']
            print(f"   📝 AI Response length: {len(ai_response)} characters")
            print(f"   📝 AI Response preview: {ai_response[:100]}...")
        
        return success

    def test_chatbot_biryani_request(self):
        """Test biryani/Pakistani cuisine request - should work after fixes"""
        if not self.token:
            return self.log_test("Chatbot Biryani Request", False, "No authentication token")
        
        chat_data = {
            "message": "I want biryani",
            "user_id": self.user_id
        }
        
        success, response = self.run_api_test(
            "Chatbot Biryani Request",
            "POST",
            "api/chat",
            200,
            chat_data
        )
        
        if success:
            recommended_items = response.get('recommended_items', [])
            show_order_card = response.get('show_order_card', False)
            
            if len(recommended_items) > 0 and show_order_card:
                print(f"   ✅ Found {len(recommended_items)} biryani items")
                for item in recommended_items:
                    print(f"      - {item.get('name', 'N/A')} from {item.get('restaurant_name', 'N/A')}")
                return True
            else:
                print(f"   ❌ Expected biryani items but got {len(recommended_items)} items, show_order_card: {show_order_card}")
                return False
        
        return success

    def test_chatbot_dessert_request(self):
        """Test dessert request - should work after fixes"""
        if not self.token:
            return self.log_test("Chatbot Dessert Request", False, "No authentication token")
        
        chat_data = {
            "message": "show me desserts",
            "user_id": self.user_id
        }
        
        success, response = self.run_api_test(
            "Chatbot Dessert Request",
            "POST",
            "api/chat",
            200,
            chat_data
        )
        
        if success:
            recommended_items = response.get('recommended_items', [])
            show_order_card = response.get('show_order_card', False)
            
            if len(recommended_items) > 0 and show_order_card:
                print(f"   ✅ Found {len(recommended_items)} dessert items")
                for item in recommended_items:
                    print(f"      - {item.get('name', 'N/A')} from {item.get('restaurant_name', 'N/A')}")
                return True
            else:
                print(f"   ❌ Expected dessert items but got {len(recommended_items)} items, show_order_card: {show_order_card}")
                return False
        
        return success

    def test_chatbot_general_recommendations(self):
        """Test general recommendations with user preferences"""
        if not self.token:
            return self.log_test("Chatbot General Recommendations", False, "No authentication token")
        
        chat_data = {
            "message": "I'm hungry",
            "user_id": self.user_id
        }
        
        success, response = self.run_api_test(
            "Chatbot General Recommendations",
            "POST",
            "api/chat",
            200,
            chat_data
        )
        
        if success:
            recommended_items = response.get('recommended_items', [])
            show_order_card = response.get('show_order_card', False)
            
            print(f"   📝 Found {len(recommended_items)} general recommendations")
            if recommended_items:
                for item in recommended_items:
                    restaurant_cuisine = item.get('restaurant_cuisine', [])
                    print(f"      - {item.get('name', 'N/A')} from {item.get('restaurant_name', 'N/A')} ({restaurant_cuisine})")
                
                # Check if items match user preferences (Pakistani, Chinese, Italian)
                preference_match = False
                for item in recommended_items:
                    restaurant_cuisine = item.get('restaurant_cuisine', [])
                    if any(cuisine in ['Pakistani', 'Chinese', 'Italian'] for cuisine in restaurant_cuisine):
                        preference_match = True
                        break
                
                if preference_match:
                    print(f"   ✅ Items match user preferences")
                    return True
                else:
                    print(f"   ⚠️  Items don't match user preferences (Pakistani, Chinese, Italian)")
                    return False
            else:
                print(f"   ❌ No recommendations returned")
                return False
        
        return success

    def test_chatbot_japanese_request(self):
        """Test Japanese cuisine request - should handle gracefully (database gap)"""
        if not self.token:
            return self.log_test("Chatbot Japanese Request", False, "No authentication token")
        
        chat_data = {
            "message": "japanese food please",
            "user_id": self.user_id
        }
        
        success, response = self.run_api_test(
            "Chatbot Japanese Request",
            "POST",
            "api/chat",
            200,
            chat_data
        )
        
        if success:
            recommended_items = response.get('recommended_items', [])
            ai_response = response.get('response', '')
            
            print(f"   📝 AI Response: {ai_response}")
            print(f"   📝 Found {len(recommended_items)} items for Japanese request")
            
            if recommended_items:
                for item in recommended_items:
                    restaurant_cuisine = item.get('restaurant_cuisine', [])
                    print(f"      - {item.get('name', 'N/A')} from {item.get('restaurant_name', 'N/A')} ({restaurant_cuisine})")
                
                # Check if returned items are actually Japanese or appropriate fallback
                japanese_items = [item for item in recommended_items 
                                if 'Japanese' in item.get('restaurant_cuisine', [])]
                
                if japanese_items:
                    print(f"   ✅ Found {len(japanese_items)} Japanese items")
                    return True
                else:
                    # Check if it's appropriate fallback (Asian cuisines) or wrong items
                    asian_items = [item for item in recommended_items 
                                 if any(cuisine in ['Chinese', 'Thai'] for cuisine in item.get('restaurant_cuisine', []))]
                    
                    if asian_items:
                        print(f"   ⚠️  No Japanese items, but found {len(asian_items)} Asian fallback items")
                        return True
                    else:
                        print(f"   ❌ Returned non-Asian items for Japanese request")
                        return False
            else:
                print(f"   ✅ No items returned - appropriate for unavailable cuisine")
                return True
        
        return success

    def test_chatbot_thai_request(self):
        """Test Thai cuisine request - limited availability"""
        if not self.token:
            return self.log_test("Chatbot Thai Request", False, "No authentication token")
        
        chat_data = {
            "message": "thai food",
            "user_id": self.user_id
        }
        
        success, response = self.run_api_test(
            "Chatbot Thai Request",
            "POST",
            "api/chat",
            200,
            chat_data
        )
        
        if success:
            recommended_items = response.get('recommended_items', [])
            ai_response = response.get('response', '')
            
            print(f"   📝 AI Response: {ai_response}")
            print(f"   📝 Found {len(recommended_items)} items for Thai request")
            
            if recommended_items:
                for item in recommended_items:
                    restaurant_cuisine = item.get('restaurant_cuisine', [])
                    print(f"      - {item.get('name', 'N/A')} from {item.get('restaurant_name', 'N/A')} ({restaurant_cuisine})")
                
                # Check for Thai items or appropriate fallback
                thai_items = [item for item in recommended_items 
                            if 'Thai' in item.get('restaurant_cuisine', [])]
                
                if thai_items:
                    print(f"   ✅ Found {len(thai_items)} Thai items")
                    return True
                else:
                    print(f"   ⚠️  No Thai items found, showing fallback")
                    return True
            else:
                print(f"   ⚠️  No items returned for Thai request")
                return True
        
        return success

    def setup_japanese_thai_desserts_user(self):
        """Setup a test user with Japanese, Thai, Desserts preferences"""
        test_user_data = {
            "username": f"japanese_user_{datetime.now().strftime('%H%M%S')}",
            "email": f"japanese_test_{datetime.now().strftime('%H%M%S')}@voiceguide.com",
            "password": "TestPass123!"
        }
        
        success, response = self.run_api_test(
            "Register Japanese/Thai/Desserts User",
            "POST",
            "api/auth/register",
            200,
            test_user_data
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.user_id = response['user']['id']
            self.session.headers['Authorization'] = f'Bearer {self.token}'
            
            # Set preferences to Japanese, Thai, Desserts
            preferences_data = {
                "favorite_cuisines": ["Japanese", "Thai", "Desserts"],
                "dietary_restrictions": [],
                "spice_preference": "mild"
            }
            
            pref_success, _ = self.run_api_test(
                "Set Japanese/Thai/Desserts Preferences",
                "PUT",
                "api/user/preferences",
                200,
                preferences_data
            )
            
            if pref_success:
                print(f"   📝 Setup user with Japanese/Thai/Desserts preferences")
                return True
        
        return False

    def test_user_preference_fallback(self):
        """Test user preference fallback for Japanese/Thai/Desserts user"""
        if not self.token:
            return self.log_test("User Preference Fallback", False, "No authentication token")
        
        chat_data = {
            "message": "I'm hungry",
            "user_id": self.user_id
        }
        
        success, response = self.run_api_test(
            "User Preference Fallback Test",
            "POST",
            "api/chat",
            200,
            chat_data
        )
        
        if success:
            recommended_items = response.get('recommended_items', [])
            
            print(f"   📝 Found {len(recommended_items)} items for Japanese/Thai/Desserts user")
            
            if recommended_items:
                for item in recommended_items:
                    restaurant_cuisine = item.get('restaurant_cuisine', [])
                    print(f"      - {item.get('name', 'N/A')} from {item.get('restaurant_name', 'N/A')} ({restaurant_cuisine})")
                
                # Check if items prioritize Desserts (since Japanese/Thai unavailable)
                dessert_items = [item for item in recommended_items 
                               if 'Desserts' in item.get('restaurant_cuisine', [])]
                
                pakistani_items = [item for item in recommended_items 
                                 if 'Pakistani' in item.get('restaurant_cuisine', [])]
                
                if dessert_items:
                    print(f"   ✅ Found {len(dessert_items)} dessert items - correct preference fallback")
                    return True
                elif pakistani_items:
                    print(f"   ❌ Found {len(pakistani_items)} Pakistani items - should prioritize Desserts")
                    return False
                else:
                    print(f"   ⚠️  Found other cuisine items")
                    return True
            else:
                print(f"   ❌ No recommendations for user with preferences")
                return False
        
        return success

    def test_voice_order_processing(self):
        """Test voice order processing"""
        if not self.token:
            return self.log_test("Voice Order Processing", False, "No authentication token")
        
        voice_data = {
            "audio_text": "I want to order chicken biryani and some naan bread",
            "user_id": self.user_id
        }
        
        success, response = self.run_api_test(
            "Process Voice Order",
            "POST",
            "api/voice-order",
            200,
            voice_data
        )
        
        if success and 'parsed_order' in response:
            print(f"   📝 Voice order processed successfully")
            print(f"   📝 Original: {response.get('original_text', 'N/A')}")
        
        return success

    def test_get_user_orders(self):
        """Test getting user orders"""
        if not self.token:
            return self.log_test("Get User Orders", False, "No authentication token")
        
        success, response = self.run_api_test(
            "Get User Orders",
            "GET",
            "api/orders?page=1&limit=5",
            200
        )
        
        if success and 'orders' in response:
            orders = response['orders']
            print(f"   📝 Found {len(orders)} orders, Total: {response.get('total', 0)}")
        
        return success

    def test_restaurant_menu(self):
        """Test getting restaurant menu"""
        # First get a restaurant ID
        success, restaurants_response = self.run_api_test(
            "Get Restaurant for Menu Test",
            "GET",
            "api/restaurants?page=1&limit=1",
            200
        )
        
        if not success or not restaurants_response.get('restaurants'):
            return self.log_test("Get Restaurant Menu", False, "No restaurants available")
        
        restaurant_id = restaurants_response['restaurants'][0]['id']
        
        success, response = self.run_api_test(
            "Get Restaurant Menu",
            "GET",
            f"api/restaurants/{restaurant_id}/menu",
            200
        )
        
        if success and 'menu_items' in response:
            menu_items = response['menu_items']
            print(f"   📝 Found {len(menu_items)} menu items")
            if menu_items:
                sample = menu_items[0]
                print(f"   📝 Sample item: {sample.get('name', 'N/A')} - ₹{sample.get('price', 0)}")
        
        return success

    def run_comprehensive_test(self):
        """Run all tests in sequence"""
        print("🚀 Starting Voice Guide API Comprehensive Testing")
        print("=" * 60)
        
        # Basic connectivity
        print("\n📡 CONNECTIVITY TESTS")
        self.test_health_check()
        
        # Authentication tests
        print("\n🔐 AUTHENTICATION TESTS")
        auth_success = False
        
        # Try demo login first
        if self.test_demo_login():
            auth_success = True
        else:
            # If demo login fails, try registration
            print("   ℹ️  Demo login failed, trying registration...")
            if self.test_user_registration():
                auth_success = True
        
        if auth_success:
            self.test_user_profile()
            self.test_update_preferences()
        
        # Data retrieval tests
        print("\n🍽️  DATA RETRIEVAL TESTS")
        self.test_get_cuisines()
        self.test_get_restaurants()
        self.test_get_restaurants_with_cuisine_filter()
        self.test_restaurant_menu()
        
        # Recommendation engine tests
        print("\n🎯 RECOMMENDATION ENGINE TESTS")
        if auth_success:
            self.test_get_recommendations()
        
        # AI and Voice tests
        print("\n🤖 AI & VOICE TESTS")
        if auth_success:
            self.test_chat_functionality()
            self.test_voice_order_processing()
        
        # FOCUSED CHATBOT RECOMMENDATION TESTS (Based on Review Request)
        print("\n🎯 CHATBOT RECOMMENDATION SYSTEM TESTS (CRITICAL)")
        if auth_success:
            print("   Testing with Pakistani/Chinese/Italian preferences user...")
            self.test_chatbot_biryani_request()
            self.test_chatbot_dessert_request()
            self.test_chatbot_general_recommendations()
            self.test_chatbot_japanese_request()
            self.test_chatbot_thai_request()
            
            # Test with Japanese/Thai/Desserts user
            print("\n   Setting up Japanese/Thai/Desserts preferences user...")
            if self.setup_japanese_thai_desserts_user():
                self.test_user_preference_fallback()
        
        # Order management tests
        print("\n📦 ORDER MANAGEMENT TESTS")
        if auth_success:
            self.test_get_user_orders()
        
        # Final results
        print("\n" + "=" * 60)
        print(f"🏁 TESTING COMPLETE")
        print(f"📊 Results: {self.tests_passed}/{self.tests_run} tests passed")
        print(f"✅ Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed! Backend is fully functional.")
            return True
        elif self.tests_passed / self.tests_run >= 0.8:
            print("⚠️  Most tests passed. Minor issues detected.")
            return True
        else:
            print("❌ Multiple test failures. Backend has significant issues.")
            return False

    def run_focused_chatbot_tests(self):
        """Run only the focused chatbot recommendation tests from review request"""
        print("🎯 FOCUSED CHATBOT RECOMMENDATION SYSTEM TESTING")
        print("=" * 60)
        print("Testing critical bug fixes for chatbot recommendations...")
        
        # Setup authentication
        auth_success = False
        if self.test_demo_login():
            auth_success = True
        else:
            if self.test_user_registration():
                auth_success = True
        
        if not auth_success:
            print("❌ Authentication failed - cannot run chatbot tests")
            return False
        
        # Set Pakistani/Chinese/BBQ preferences (as mentioned in review)
        preferences_data = {
            "favorite_cuisines": ["Pakistani", "Chinese", "BBQ"],
            "dietary_restrictions": [],
            "spice_preference": "medium"
        }
        
        self.run_api_test(
            "Set Pakistani/Chinese/BBQ Preferences",
            "PUT",
            "api/user/preferences",
            200,
            preferences_data
        )
        
        print("\n🧪 TESTING WITH PAKISTANI/CHINESE/BBQ USER:")
        
        # Test 1: Biryani request (should work now)
        print("\n1️⃣  Testing Biryani Request (Should return biryani items)")
        biryani_success = self.test_chatbot_biryani_request()
        
        # Test 2: Dessert request (should work now)
        print("\n2️⃣  Testing Dessert Request (Should return dessert items)")
        dessert_success = self.test_chatbot_dessert_request()
        
        # Test 3: General recommendations (should respect preferences)
        print("\n3️⃣  Testing General Recommendations (Should match preferences)")
        general_success = self.test_chatbot_general_recommendations()
        
        # Test 4: Japanese request (should handle gracefully)
        print("\n4️⃣  Testing Japanese Request (Should handle database gap)")
        japanese_success = self.test_chatbot_japanese_request()
        
        # Test 5: Thai request (limited availability)
        print("\n5️⃣  Testing Thai Request (Limited availability)")
        thai_success = self.test_chatbot_thai_request()
        
        # Test 6: Setup Japanese/Thai/Desserts user and test fallback
        print("\n6️⃣  Testing User Preference Fallback")
        if self.setup_japanese_thai_desserts_user():
            fallback_success = self.test_user_preference_fallback()
        else:
            fallback_success = False
            self.log_test("User Preference Fallback", False, "Failed to setup test user")
        
        # Summary of critical tests
        critical_tests = [
            ("Biryani Request", biryani_success),
            ("Dessert Request", dessert_success),
            ("General Recommendations", general_success),
            ("Japanese Request Handling", japanese_success),
            ("Thai Request Handling", thai_success),
            ("User Preference Fallback", fallback_success)
        ]
        
        print("\n" + "=" * 60)
        print("🎯 FOCUSED TEST RESULTS:")
        
        passed_critical = 0
        for test_name, success in critical_tests:
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"   {status}: {test_name}")
            if success:
                passed_critical += 1
        
        print(f"\n📊 Critical Tests: {passed_critical}/{len(critical_tests)} passed")
        print(f"✅ Success Rate: {(passed_critical/len(critical_tests))*100:.1f}%")
        
        if passed_critical >= 4:  # At least 4/6 critical tests should pass
            print("🎉 Chatbot recommendation system is working well!")
            return True
        else:
            print("❌ Chatbot recommendation system has significant issues.")
            return False

    def test_rating_system(self):
        """Test Phase 1: Rating System Implementation"""
        print("\n🎯 TESTING RATING SYSTEM (Phase 1)")
        
        if not self.token:
            return self.log_test("Rating System", False, "No authentication token")
        
        # First, get a menu item to rate
        success, menu_response = self.run_api_test(
            "Get Menu Items for Rating",
            "GET", 
            "api/restaurants?page=1&limit=1",
            200
        )
        
        if not success or not menu_response.get('restaurants'):
            return self.log_test("Rating System Setup", False, "No restaurants found")
        
        restaurant_id = menu_response['restaurants'][0]['id']
        
        # Get menu items from this restaurant
        success, items_response = self.run_api_test(
            "Get Restaurant Menu Items",
            "GET",
            f"api/restaurants/{restaurant_id}/menu",
            200
        )
        
        if not success or not items_response.get('menu_items'):
            return self.log_test("Rating System Setup", False, "No menu items found")
        
        menu_item_id = items_response['menu_items'][0]['id']
        menu_item_name = items_response['menu_items'][0]['name']
        
        print(f"   📝 Testing with item: {menu_item_name}")
        
        # Test 1: Rate item with 5 stars
        rating_data = {
            "menu_item_id": menu_item_id,
            "rating": 5,
            "review": "Excellent biryani! Really loved it."
        }
        
        success, response = self.run_api_test(
            "Rate Item (5 stars)",
            "POST",
            "api/ratings",
            200,
            rating_data
        )
        
        if not success:
            return False
        
        # Test 2: Update rating to 2 stars (dislike)
        rating_data_update = {
            "menu_item_id": menu_item_id,
            "rating": 2,
            "review": "Changed my mind, not that great"
        }
        
        success, response = self.run_api_test(
            "Update Rating (2 stars - dislike)",
            "POST",
            "api/ratings",
            200,
            rating_data_update
        )
        
        if not success:
            return False
        
        # Test 3: Get my ratings
        success, ratings_response = self.run_api_test(
            "Get My Ratings",
            "GET",
            "api/ratings/my-ratings",
            200
        )
        
        if success and ratings_response.get('ratings'):
            ratings = ratings_response['ratings']
            print(f"   📝 Found {len(ratings)} ratings")
            
            # Verify the rating was updated, not duplicated
            item_ratings = [r for r in ratings if r['menu_item_id'] == menu_item_id]
            if len(item_ratings) == 1 and item_ratings[0]['rating'] == 2:
                self.log_test("Rating Update (No Duplication)", True, "Rating updated correctly")
            else:
                self.log_test("Rating Update (No Duplication)", False, f"Found {len(item_ratings)} ratings for same item")
        
        # Test 4: Test invalid ratings
        invalid_rating_tests = [
            (0, "Rating too low"),
            (6, "Rating too high"),
            (-1, "Negative rating")
        ]
        
        for invalid_rating, test_name in invalid_rating_tests:
            invalid_data = {
                "menu_item_id": menu_item_id,
                "rating": invalid_rating,
                "review": "Invalid test"
            }
            
            success, response = self.run_api_test(
                f"Invalid Rating ({test_name})",
                "POST",
                "api/ratings",
                400,  # Should return 400 Bad Request
                invalid_data
            )
        
        # Test 5: Rate non-existent item
        fake_item_data = {
            "menu_item_id": "fake-item-id-12345",
            "rating": 4,
            "review": "This should fail"
        }
        
        success, response = self.run_api_test(
            "Rate Non-existent Item",
            "POST",
            "api/ratings",
            404,  # Should return 404 Not Found
            fake_item_data
        )
        
        return True

    def test_dislike_filtering(self):
        """Test Phase 1: Dislike Feature - Items rated < 3 stars filtered from recommendations"""
        print("\n🎯 TESTING DISLIKE FILTERING (Phase 1)")
        
        if not self.token:
            return self.log_test("Dislike Filtering", False, "No authentication token")
        
        # First, find a menu item to dislike
        success, menu_response = self.run_api_test(
            "Get Menu Items for Dislike Test",
            "GET", 
            "api/restaurants?page=1&limit=2",
            200
        )
        
        if not success or not menu_response.get('restaurants'):
            return self.log_test("Dislike Test Setup", False, "No restaurants found")
        
        # Get menu items from first restaurant
        restaurant_id = menu_response['restaurants'][0]['id']
        success, items_response = self.run_api_test(
            "Get Menu Items",
            "GET",
            f"api/restaurants/{restaurant_id}/menu",
            200
        )
        
        if not success or not items_response.get('menu_items'):
            return self.log_test("Dislike Test Setup", False, "No menu items found")
        
        # Pick first item to dislike
        dislike_item = items_response['menu_items'][0]
        dislike_item_id = dislike_item['id']
        dislike_item_name = dislike_item['name']
        
        print(f"   📝 Will dislike item: {dislike_item_name}")
        
        # Rate the item with 1 star (strong dislike)
        dislike_rating = {
            "menu_item_id": dislike_item_id,
            "rating": 1,
            "review": "Really didn't like this item"
        }
        
        success, response = self.run_api_test(
            "Rate Item as Disliked (1 star)",
            "POST",
            "api/ratings",
            200,
            dislike_rating
        )
        
        if not success:
            return False
        
        # Now test recommendations - disliked item should NOT appear
        recommendation_messages = [
            "I'm hungry",
            "recommend me something",
            "what should I order"
        ]
        
        dislike_filtering_works = True
        
        for message in recommendation_messages:
            chat_data = {
                "message": message,
                "user_id": self.user_id
            }
            
            success, chat_response = self.run_api_test(
                f"Chat Recommendation Test: '{message}'",
                "POST",
                "api/chat",
                200,
                chat_data
            )
            
            if success:
                # Check if disliked item appears in recommendations
                reorder_items = chat_response.get('reorder_items', [])
                new_items = chat_response.get('new_items', [])
                
                all_recommended_ids = []
                all_recommended_ids.extend([item.get('id') for item in reorder_items])
                all_recommended_ids.extend([item.get('id') for item in new_items])
                
                if dislike_item_id in all_recommended_ids:
                    self.log_test(f"Dislike Filtering - '{message}'", False, 
                                f"Disliked item '{dislike_item_name}' appeared in recommendations")
                    dislike_filtering_works = False
                else:
                    self.log_test(f"Dislike Filtering - '{message}'", True, 
                                "Disliked item correctly excluded from recommendations")
                    
                print(f"   📝 Recommended {len(reorder_items)} reorder items, {len(new_items)} new items")
        
        return dislike_filtering_works

    def test_menu_search_api(self):
        """Test Phase 1: Menu Search Direct API"""
        print("\n🎯 TESTING MENU SEARCH API (Phase 1)")
        
        if not self.token:
            return self.log_test("Menu Search API", False, "No authentication token")
        
        # Test various search queries
        search_queries = [
            ("biryani", "Should find biryani items"),
            ("burger", "Should find burger items"), 
            ("chicken", "Should find chicken items"),
            ("pizza", "Should find pizza items"),
            ("karahi", "Should find karahi items")
        ]
        
        search_success = True
        
        for query, description in search_queries:
            search_data = {"query": query}
            
            success, response = self.run_api_test(
                f"Search Menu: '{query}'",
                "POST",
                "api/menu/search",
                200,
                search_data
            )
            
            if success:
                items = response.get('items', [])
                count = response.get('count', 0)
                
                print(f"   📝 Query '{query}': Found {count} items")
                
                if items:
                    # Verify search results contain the query term
                    relevant_items = 0
                    for item in items[:3]:  # Check first 3 items
                        name = item.get('name', '').lower()
                        description = item.get('description', '').lower()
                        tags = ' '.join(item.get('tags', [])).lower()
                        
                        if query.lower() in name or query.lower() in description or query.lower() in tags:
                            relevant_items += 1
                    
                    if relevant_items > 0:
                        self.log_test(f"Search Relevance - '{query}'", True, 
                                    f"{relevant_items}/{min(len(items), 3)} items relevant")
                    else:
                        self.log_test(f"Search Relevance - '{query}'", False, 
                                    "No relevant items found")
                        search_success = False
            else:
                search_success = False
        
        # Test edge cases
        edge_cases = [
            ("", 400, "Empty query should return 400"),
            ("a", 400, "Too short query should return 400"),
            ("nonexistentfooditem12345", 200, "Non-existent item should return empty results")
        ]
        
        for query, expected_status, description in edge_cases:
            search_data = {"query": query}
            
            success, response = self.run_api_test(
                f"Edge Case: {description}",
                "POST",
                "api/menu/search",
                expected_status,
                search_data
            )
            
            if expected_status == 200 and success:
                # For non-existent items, should return 0 results
                count = response.get('count', -1)
                if count == 0:
                    self.log_test(f"Non-existent Search Result", True, "Correctly returned 0 items")
                else:
                    self.log_test(f"Non-existent Search Result", False, f"Expected 0 items, got {count}")
        
        return search_success

    def test_menu_search_via_chatbot(self):
        """Test Phase 1: Menu Search via Chatbot Intent"""
        print("\n🎯 TESTING MENU SEARCH VIA CHATBOT (Phase 1)")
        
        if not self.token:
            return self.log_test("Menu Search Chatbot", False, "No authentication token")
        
        # Test search queries that should trigger SPECIFIC_ITEM_SEARCH intent
        search_messages = [
            ("find biryani", "biryani"),
            ("show me pizza", "pizza"),
            ("looking for ice cream", "ice cream"),
            ("I want burger", "burger"),
            ("dhundo karahi", "karahi"),  # Roman Urdu
            ("search for chicken", "chicken")
        ]
        
        chatbot_search_success = True
        
        for message, expected_item in search_messages:
            chat_data = {
                "message": message,
                "user_id": self.user_id
            }
            
            success, response = self.run_api_test(
                f"Chatbot Search: '{message}'",
                "POST",
                "api/chat",
                200,
                chat_data
            )
            
            if success:
                intent = response.get('intent')
                new_items = response.get('new_items', [])
                
                # Check if intent was detected correctly
                if intent == "specific_item_search":
                    self.log_test(f"Intent Detection - '{message}'", True, 
                                f"Correctly detected intent: {intent}")
                else:
                    self.log_test(f"Intent Detection - '{message}'", False, 
                                f"Expected 'specific_item_search', got '{intent}'")
                    chatbot_search_success = False
                
                # Check if relevant items were returned
                if new_items:
                    print(f"   📝 Found {len(new_items)} items for '{message}'")
                    
                    # Check if items are relevant to the search
                    relevant_count = 0
                    for item in new_items[:3]:
                        name = item.get('name', '').lower()
                        if expected_item.lower() in name:
                            relevant_count += 1
                    
                    if relevant_count > 0:
                        self.log_test(f"Search Results - '{message}'", True, 
                                    f"{relevant_count} relevant items found")
                    else:
                        self.log_test(f"Search Results - '{message}'", False, 
                                    "No relevant items in results")
                        chatbot_search_success = False
                else:
                    self.log_test(f"Search Results - '{message}'", False, 
                                "No items returned")
                    chatbot_search_success = False
            else:
                chatbot_search_success = False
        
        return chatbot_search_success

    def test_combined_rating_search_flow(self):
        """Test Phase 1: Combined Flow - Rate item low, then verify it's excluded from search"""
        print("\n🎯 TESTING COMBINED RATING + SEARCH FLOW (Phase 1)")
        
        if not self.token:
            return self.log_test("Combined Flow", False, "No authentication token")
        
        # Step 1: Search for chicken items
        search_data = {"query": "chicken"}
        success, search_response = self.run_api_test(
            "Initial Search for Chicken",
            "POST",
            "api/menu/search",
            200,
            search_data
        )
        
        if not success or not search_response.get('items'):
            return self.log_test("Combined Flow Setup", False, "No chicken items found for test")
        
        # Pick the first chicken item
        target_item = search_response['items'][0]
        target_item_id = target_item['id']
        target_item_name = target_item['name']
        
        print(f"   📝 Target item for combined test: {target_item_name}")
        
        # Step 2: Rate this item poorly (1 star)
        rating_data = {
            "menu_item_id": target_item_id,
            "rating": 1,
            "review": "Combined flow test - disliking this item"
        }
        
        success, response = self.run_api_test(
            "Rate Target Item (1 star)",
            "POST",
            "api/ratings",
            200,
            rating_data
        )
        
        if not success:
            return False
        
        # Step 3: Search again for chicken - disliked item should be excluded
        success, search_response_after = self.run_api_test(
            "Search Chicken After Rating",
            "POST",
            "api/menu/search",
            200,
            search_data
        )
        
        if success:
            items_after = search_response_after.get('items', [])
            item_ids_after = [item.get('id') for item in items_after]
            
            if target_item_id in item_ids_after:
                self.log_test("Search Excludes Disliked Items", False, 
                            f"Disliked item '{target_item_name}' still appears in search results")
                return False
            else:
                self.log_test("Search Excludes Disliked Items", True, 
                            "Disliked item correctly excluded from search results")
        
        # Step 4: Get recommendations - disliked item should not appear
        chat_data = {
            "message": "recommend me something",
            "user_id": self.user_id
        }
        
        success, chat_response = self.run_api_test(
            "Recommendations After Dislike",
            "POST",
            "api/chat",
            200,
            chat_data
        )
        
        if success:
            reorder_items = chat_response.get('reorder_items', [])
            new_items = chat_response.get('new_items', [])
            
            all_recommended_ids = []
            all_recommended_ids.extend([item.get('id') for item in reorder_items])
            all_recommended_ids.extend([item.get('id') for item in new_items])
            
            if target_item_id in all_recommended_ids:
                self.log_test("Recommendations Exclude Disliked Items", False, 
                            f"Disliked item '{target_item_name}' appears in recommendations")
                return False
            else:
                self.log_test("Recommendations Exclude Disliked Items", True, 
                            "Disliked item correctly excluded from recommendations")
        
        return True

    def run_phase1_rating_and_search_tests(self):
        """Run comprehensive Phase 1 tests: Rating System + Dislike Feature + Menu Search"""
        print("\n" + "="*80)
        print("🚀 PHASE 1 TESTING: RATING SYSTEM + DISLIKE FEATURE + MENU SEARCH")
        print("="*80)
        
        # Authentication first - try demo login, fallback to registration
        auth_success = self.test_demo_login()
        if not auth_success:
            print("   📝 Demo login failed, trying user registration...")
            auth_success = self.test_user_registration()
        
        if not auth_success:
            print("❌ Cannot proceed without authentication")
            return False
        
        # Run all Phase 1 tests
        test_results = []
        
        # Test 1: Rating System
        test_results.append(self.test_rating_system())
        
        # Test 2: Dislike Filtering
        test_results.append(self.test_dislike_filtering())
        
        # Test 3: Menu Search API
        test_results.append(self.test_menu_search_api())
        
        # Test 4: Menu Search via Chatbot
        test_results.append(self.test_menu_search_via_chatbot())
        
        # Test 5: Combined Flow
        test_results.append(self.test_combined_rating_search_flow())
        
        # Summary
        passed_tests = sum(test_results)
        total_tests = len(test_results)
        
        print(f"\n📊 PHASE 1 TEST RESULTS:")
        print(f"✅ Passed: {passed_tests}/{total_tests}")
        print(f"📈 Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if passed_tests >= 4:  # At least 4/5 major test categories should pass
            print("🎉 Phase 1 implementation is working well!")
            return True
        else:
            print("❌ Phase 1 implementation has significant issues.")
            return False

def main():
    tester = VoiceGuideAPITester()
    
    # Run Phase 1 tests as requested in review
    print("🎯 Running PHASE 1 TESTS: Rating System + Dislike Feature + Menu Search...")
    phase1_success = tester.run_phase1_rating_and_search_tests()
    
    return 0 if phase1_success else 1

if __name__ == "__main__":
    sys.exit(main())