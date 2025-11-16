#!/usr/bin/env python3
"""
Focused Chatbot Menu Item Cards Testing
Analyzing specific issues found in comprehensive testing
"""

import requests
import json
from datetime import datetime

class FocusedChatbotTester:
    def __init__(self, base_url="https://food-voice-ai.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.user_id = None
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})

    def setup_auth(self):
        """Setup authentication"""
        # Try registration
        test_user_data = {
            "username": f"focused_test_{datetime.now().strftime('%H%M%S')}",
            "email": f"focused_test_{datetime.now().strftime('%H%M%S')}@voiceguide.com",
            "password": "TestPass123!"
        }
        
        try:
            response = self.session.post(f"{self.base_url}/api/auth/register", json=test_user_data)
            if response.status_code == 200:
                data = response.json()
                self.token = data['access_token']
                self.user_id = data['user']['id']
                self.session.headers['Authorization'] = f'Bearer {self.token}'
                print(f"✅ Authenticated as: {data['user']['username']}")
                return True
        except Exception as e:
            print(f"❌ Auth failed: {e}")
        return False

    def set_preferences(self):
        """Set user preferences"""
        preferences_data = {
            "favorite_cuisines": ["Pakistani", "Chinese", "Desserts"],
            "dietary_restrictions": ["Halal"],
            "spice_preference": "medium"
        }
        
        try:
            response = self.session.put(f"{self.base_url}/api/user/preferences", json=preferences_data)
            if response.status_code == 200:
                print("✅ Preferences set successfully")
                return True
        except Exception as e:
            print(f"❌ Preferences failed: {e}")
        return False

    def test_single_message(self, message, expected_intent=None):
        """Test a single chat message and analyze response"""
        print(f"\n🧪 Testing: '{message}'")
        
        chat_data = {
            "message": message,
            "user_id": self.user_id
        }
        
        try:
            response = self.session.post(f"{self.base_url}/api/chat", json=chat_data)
            if response.status_code == 200:
                data = response.json()
                
                intent = data.get('intent', 'N/A')
                show_order_card = data.get('show_order_card', False)
                recommended_items = data.get('recommended_items', [])
                reorder_items = data.get('reorder_items', [])
                new_items = data.get('new_items', [])
                ai_response = data.get('response', 'N/A')
                
                total_items = len(recommended_items) if recommended_items else (len(reorder_items) + len(new_items))
                
                print(f"   📝 Intent: {intent}")
                print(f"   📝 Show Order Card: {show_order_card}")
                print(f"   📝 Total Items: {total_items}")
                print(f"   📝 AI Response: {ai_response[:100]}...")
                
                if expected_intent and intent != expected_intent:
                    print(f"   ❌ Intent mismatch: expected '{expected_intent}', got '{intent}'")
                
                if total_items > 0:
                    print(f"   ✅ Items returned successfully")
                    # Show first item details
                    items_to_check = recommended_items if recommended_items else (reorder_items + new_items)
                    if items_to_check:
                        first_item = items_to_check[0]
                        print(f"   📝 Sample: {first_item.get('name')} from {first_item.get('restaurant_name')} - PKR {first_item.get('price')}")
                else:
                    print(f"   ⚠️  No items returned")
                
                return {
                    'success': True,
                    'intent': intent,
                    'show_order_card': show_order_card,
                    'total_items': total_items,
                    'response': ai_response
                }
            else:
                print(f"   ❌ API Error: {response.status_code}")
                return {'success': False, 'error': response.status_code}
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            return {'success': False, 'error': str(e)}

    def run_focused_analysis(self):
        """Run focused analysis of chatbot menu item cards"""
        print("🎯 FOCUSED CHATBOT MENU ITEM CARDS ANALYSIS")
        print("="*60)
        
        if not self.setup_auth():
            print("❌ Cannot proceed without authentication")
            return
        
        if not self.set_preferences():
            print("❌ Cannot set preferences")
            return
        
        # Test cases from review request
        test_cases = [
            {
                'message': 'recommend me something',
                'expected_intent': 'food_recommendation',
                'description': 'General recommendation - should show menu cards'
            },
            {
                'message': 'Order Rasmalai',
                'expected_intent': 'specific_item_search',
                'description': 'Specific item search - English'
            },
            {
                'message': 'find biryani',
                'expected_intent': 'specific_item_search',
                'description': 'Specific item search - should return biryani items'
            },
            {
                'message': 'ice cream dikhao',
                'expected_intent': 'specific_item_search',
                'description': 'Roman Urdu - should return ice cream/dessert items'
            },
            {
                'message': "I'm hungry",
                'expected_intent': 'food_recommendation',
                'description': 'Generic request - should use user preferences'
            }
        ]
        
        results = []
        for test_case in test_cases:
            result = self.test_single_message(test_case['message'], test_case['expected_intent'])
            result['test_case'] = test_case
            results.append(result)
        
        # Analysis Summary
        print(f"\n📊 ANALYSIS SUMMARY:")
        print("="*60)
        
        working_tests = []
        failing_tests = []
        
        for result in results:
            if result['success']:
                test_case = result['test_case']
                intent_correct = result['intent'] == test_case['expected_intent']
                has_items = result['total_items'] > 0
                shows_cards = result['show_order_card']
                
                if intent_correct and has_items and shows_cards:
                    working_tests.append(test_case['message'])
                    print(f"✅ WORKING: '{test_case['message']}'")
                else:
                    failing_tests.append({
                        'message': test_case['message'],
                        'issues': []
                    })
                    issues = []
                    if not intent_correct:
                        issues.append(f"Intent: expected '{test_case['expected_intent']}', got '{result['intent']}'")
                    if not has_items:
                        issues.append("No items returned")
                    if not shows_cards:
                        issues.append("show_order_card is False")
                    
                    failing_tests[-1]['issues'] = issues
                    print(f"❌ FAILING: '{test_case['message']}' - {', '.join(issues)}")
            else:
                failing_tests.append({
                    'message': result['test_case']['message'],
                    'issues': [f"API Error: {result.get('error', 'Unknown')}"]
                })
                print(f"❌ ERROR: '{result['test_case']['message']}' - {result.get('error', 'Unknown')}")
        
        print(f"\n📈 SUCCESS RATE: {len(working_tests)}/{len(test_cases)} ({len(working_tests)/len(test_cases)*100:.1f}%)")
        
        if working_tests:
            print(f"\n✅ WORKING FEATURES:")
            for msg in working_tests:
                print(f"   - {msg}")
        
        if failing_tests:
            print(f"\n❌ ISSUES FOUND:")
            for test in failing_tests:
                print(f"   - '{test['message']}': {', '.join(test['issues'])}")
        
        # Recommendations
        print(f"\n🔧 RECOMMENDATIONS:")
        
        intent_issues = [t for t in failing_tests if any('Intent:' in issue for issue in t['issues'])]
        if intent_issues:
            print("   1. Fix intent detection for:")
            for test in intent_issues:
                print(f"      - '{test['message']}'")
        
        no_items_issues = [t for t in failing_tests if any('No items' in issue for issue in t['issues'])]
        if no_items_issues:
            print("   2. Fix item retrieval for:")
            for test in no_items_issues:
                print(f"      - '{test['message']}'")
        
        card_issues = [t for t in failing_tests if any('show_order_card' in issue for issue in t['issues'])]
        if card_issues:
            print("   3. Fix show_order_card logic for:")
            for test in card_issues:
                print(f"      - '{test['message']}'")

if __name__ == "__main__":
    tester = FocusedChatbotTester()
    tester.run_focused_analysis()