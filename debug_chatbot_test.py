#!/usr/bin/env python3
"""
Debug Chatbot Recommendation System
Detailed investigation of the chatbot API responses
"""

import requests
import json
from datetime import datetime

class ChatbotDebugger:
    def __init__(self, base_url="https://munchmate-voice.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.user_id = None
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})

    def setup_test_user(self):
        """Register and setup test user"""
        timestamp = datetime.now().strftime('%H%M%S')
        test_user_data = {
            "username": f"debuguser_{timestamp}",
            "email": f"debuguser_{timestamp}@example.com",
            "password": "test123"
        }
        
        response = self.session.post(f"{self.base_url}/api/auth/register", json=test_user_data)
        if response.status_code == 200:
            data = response.json()
            self.token = data['access_token']
            self.user_id = data['user']['id']
            self.session.headers['Authorization'] = f'Bearer {self.token}'
            print(f"✅ Registered user: {data['user']['username']}")
            return True
        else:
            print(f"❌ Registration failed: {response.status_code} - {response.text}")
            return False

    def set_preferences(self, favorite_cuisines, spice_preference="mild"):
        """Set user preferences"""
        preferences_data = {
            "favorite_cuisines": favorite_cuisines,
            "dietary_restrictions": [],
            "spice_preference": spice_preference
        }
        
        response = self.session.put(f"{self.base_url}/api/user/preferences", json=preferences_data)
        if response.status_code == 200:
            print(f"✅ Set preferences: {favorite_cuisines}, spice: {spice_preference}")
            return True
        else:
            print(f"❌ Preferences failed: {response.status_code} - {response.text}")
            return False

    def debug_chat_response(self, message):
        """Debug a single chat message"""
        print(f"\n🔍 DEBUGGING MESSAGE: '{message}'")
        print("-" * 50)
        
        chat_data = {
            "message": message,
            "user_id": self.user_id
        }
        
        response = self.session.post(f"{self.base_url}/api/chat", json=chat_data)
        
        if response.status_code != 200:
            print(f"❌ Chat API failed: {response.status_code} - {response.text}")
            return
        
        data = response.json()
        
        print(f"📝 AI Response: {data.get('response', 'N/A')}")
        print(f"📝 Show Order Card: {data.get('show_order_card', False)}")
        print(f"📝 Restaurants Count: {len(data.get('restaurants', []))}")
        print(f"📝 Recommended Items Count: {len(data.get('recommended_items', []))}")
        
        # Show recommended items details
        recommended_items = data.get('recommended_items', [])
        if recommended_items:
            print(f"\n📋 RECOMMENDED ITEMS:")
            for i, item in enumerate(recommended_items, 1):
                print(f"  {i}. {item.get('name', 'Unknown')} - PKR {item.get('price', 0)}")
                print(f"     Restaurant: {item.get('restaurant_name', 'Unknown')}")
                print(f"     Category: {item.get('category', 'Unknown')}")
                print(f"     Tags: {item.get('tags', [])}")
                print(f"     Spice Level: {item.get('spice_level', 'Unknown')}")
                if 'preference_score' in item:
                    print(f"     Preference Score: {item.get('preference_score', 0)}")
                print()
        else:
            print("📋 No recommended items returned")
        
        # Show restaurants
        restaurants = data.get('restaurants', [])
        if restaurants:
            print(f"🏪 RESTAURANTS:")
            for i, restaurant in enumerate(restaurants, 1):
                print(f"  {i}. {restaurant.get('name', 'Unknown')} - {restaurant.get('cuisine', [])}")
                print(f"     Rating: {restaurant.get('rating', 0)} | Delivery: {restaurant.get('delivery_time', 'Unknown')}")
                print()

    def run_debug_session(self):
        """Run comprehensive debug session"""
        print("🔍 Starting Chatbot Debug Session")
        print("=" * 60)
        
        # Setup
        if not self.setup_test_user():
            return False
        
        # Set preferences to Japanese, Thai, Desserts
        if not self.set_preferences(["Japanese", "Thai", "Desserts"], "mild"):
            return False
        
        # Test various messages
        test_messages = [
            "I'm hungry",
            "recommend me something", 
            "show me desserts",
            "japanese food please",
            "thai food",
            "I want biryani"
        ]
        
        for message in test_messages:
            self.debug_chat_response(message)
        
        print("\n" + "=" * 60)
        print("🔍 Debug session complete")

def main():
    debugger = ChatbotDebugger()
    debugger.run_debug_session()

if __name__ == "__main__":
    main()