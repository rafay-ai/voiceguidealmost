#!/usr/bin/env python3
"""
Database Check - Verify menu items and restaurants for chatbot testing
"""

import requests
import json

class DatabaseChecker:
    def __init__(self, base_url="https://food-voice-ai.preview.emergentagent.com"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})

    def check_restaurants(self):
        """Check available restaurants and cuisines"""
        print("🏪 CHECKING RESTAURANTS AND CUISINES")
        print("="*50)
        
        try:
            response = self.session.get(f"{self.base_url}/api/restaurants?page=1&limit=20")
            if response.status_code == 200:
                data = response.json()
                restaurants = data.get('restaurants', [])
                
                print(f"📊 Total Restaurants: {data.get('total', 0)}")
                
                # Group by cuisine
                cuisine_count = {}
                for restaurant in restaurants:
                    for cuisine in restaurant.get('cuisine', []):
                        cuisine_count[cuisine] = cuisine_count.get(cuisine, 0) + 1
                
                print(f"\n🍽️  CUISINES AVAILABLE:")
                for cuisine, count in sorted(cuisine_count.items()):
                    print(f"   - {cuisine}: {count} restaurants")
                
                # Check for specific cuisines mentioned in tests
                target_cuisines = ['Desserts', 'Pakistani', 'Chinese', 'Japanese', 'Thai']
                print(f"\n🎯 TARGET CUISINES CHECK:")
                for cuisine in target_cuisines:
                    if cuisine in cuisine_count:
                        print(f"   ✅ {cuisine}: {cuisine_count[cuisine]} restaurants")
                    else:
                        print(f"   ❌ {cuisine}: 0 restaurants")
                
                return restaurants
            else:
                print(f"❌ Failed to get restaurants: {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ Exception: {e}")
            return []

    def check_menu_items(self, restaurants):
        """Check menu items for specific food items"""
        print(f"\n🍕 CHECKING MENU ITEMS")
        print("="*50)
        
        target_items = ['rasmalai', 'biryani', 'ice cream', 'pizza', 'burger']
        item_findings = {item: [] for item in target_items}
        
        total_items = 0
        
        for restaurant in restaurants[:10]:  # Check first 10 restaurants
            try:
                response = self.session.get(f"{self.base_url}/api/restaurants/{restaurant['id']}/menu")
                if response.status_code == 200:
                    data = response.json()
                    menu_items = data.get('menu_items', [])
                    total_items += len(menu_items)
                    
                    # Check for target items
                    for item in menu_items:
                        name = item.get('name', '').lower()
                        description = item.get('description', '').lower()
                        tags = ' '.join(item.get('tags', [])).lower()
                        
                        for target in target_items:
                            if target in name or target in description or target in tags:
                                item_findings[target].append({
                                    'name': item.get('name'),
                                    'restaurant': restaurant.get('name'),
                                    'price': item.get('price'),
                                    'available': item.get('available', True)
                                })
            except Exception as e:
                print(f"   ⚠️  Error checking {restaurant.get('name')}: {e}")
        
        print(f"📊 Total Menu Items Checked: {total_items}")
        
        print(f"\n🔍 TARGET ITEMS SEARCH RESULTS:")
        for target, findings in item_findings.items():
            if findings:
                print(f"   ✅ {target.upper()}: {len(findings)} items found")
                for finding in findings[:3]:  # Show first 3
                    print(f"      - {finding['name']} at {finding['restaurant']} (PKR {finding['price']})")
            else:
                print(f"   ❌ {target.upper()}: 0 items found")
        
        return item_findings

    def test_menu_search_api(self):
        """Test the menu search API directly"""
        print(f"\n🔍 TESTING MENU SEARCH API")
        print("="*50)
        
        search_terms = ['rasmalai', 'biryani', 'ice cream', 'pizza', 'burger']
        
        for term in search_terms:
            try:
                # Test without authentication first
                response = self.session.post(f"{self.base_url}/api/menu/search?query={term}")
                print(f"🔍 Search '{term}': Status {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    items = data.get('items', [])
                    count = data.get('count', 0)
                    print(f"   📝 Found {count} items")
                    
                    if items:
                        for item in items[:2]:  # Show first 2
                            print(f"      - {item.get('name')} from {item.get('restaurant_name', 'N/A')}")
                elif response.status_code == 401:
                    print(f"   ⚠️  Authentication required for search API")
                else:
                    print(f"   ❌ Error: {response.text[:100]}")
            except Exception as e:
                print(f"   ❌ Exception: {e}")

    def run_comprehensive_check(self):
        """Run comprehensive database check"""
        print("🔍 COMPREHENSIVE DATABASE CHECK FOR CHATBOT MENU ITEMS")
        print("="*70)
        
        # Check restaurants and cuisines
        restaurants = self.check_restaurants()
        
        if restaurants:
            # Check menu items
            self.check_menu_items(restaurants)
        
        # Test menu search API
        self.test_menu_search_api()
        
        print(f"\n📋 SUMMARY:")
        print("="*50)
        print("This check helps identify:")
        print("1. Which cuisines are available in the database")
        print("2. Which specific food items exist")
        print("3. Whether the menu search API is working")
        print("4. Potential gaps in the database that affect chatbot responses")

if __name__ == "__main__":
    checker = DatabaseChecker()
    checker.run_comprehensive_check()