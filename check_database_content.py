#!/usr/bin/env python3
"""
Check Database Content
Verify what restaurants and menu items are available for different cuisines
"""

import requests
import json

class DatabaseChecker:
    def __init__(self, base_url="https://food-voice-ai.preview.emergentagent.com"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})

    def check_available_cuisines(self):
        """Check what cuisines are available"""
        print("🍽️ CHECKING AVAILABLE CUISINES")
        print("-" * 40)
        
        response = self.session.get(f"{self.base_url}/api/cuisines")
        if response.status_code == 200:
            data = response.json()
            cuisines = data.get('cuisines', [])
            print(f"Available cuisines ({len(cuisines)}):")
            for cuisine in cuisines:
                print(f"  - {cuisine}")
        else:
            print(f"❌ Failed to get cuisines: {response.status_code}")
        print()

    def check_restaurants_by_cuisine(self, cuisine):
        """Check restaurants for a specific cuisine"""
        print(f"🏪 RESTAURANTS FOR {cuisine.upper()}")
        print("-" * 40)
        
        response = self.session.get(f"{self.base_url}/api/restaurants?cuisine={cuisine}&limit=20")
        if response.status_code == 200:
            data = response.json()
            restaurants = data.get('restaurants', [])
            print(f"Found {len(restaurants)} restaurants:")
            for restaurant in restaurants:
                print(f"  - {restaurant.get('name', 'Unknown')} | Cuisines: {restaurant.get('cuisine', [])}")
                print(f"    Rating: {restaurant.get('rating', 0)} | Active: {restaurant.get('is_active', False)}")
        else:
            print(f"❌ Failed to get restaurants: {response.status_code}")
        print()

    def check_menu_items_for_restaurant(self, restaurant_id, restaurant_name):
        """Check menu items for a specific restaurant"""
        print(f"📋 MENU ITEMS FOR {restaurant_name}")
        print("-" * 40)
        
        response = self.session.get(f"{self.base_url}/api/restaurants/{restaurant_id}/menu")
        if response.status_code == 200:
            data = response.json()
            menu_items = data.get('menu_items', [])
            print(f"Found {len(menu_items)} menu items:")
            for item in menu_items[:10]:  # Show first 10 items
                print(f"  - {item.get('name', 'Unknown')} | PKR {item.get('price', 0)}")
                print(f"    Category: {item.get('category', 'Unknown')} | Tags: {item.get('tags', [])}")
                print(f"    Spice: {item.get('spice_level', 'Unknown')} | Available: {item.get('available', False)}")
                print()
        else:
            print(f"❌ Failed to get menu items: {response.status_code}")
        print()

    def run_database_check(self):
        """Run comprehensive database check"""
        print("🔍 DATABASE CONTENT ANALYSIS")
        print("=" * 60)
        
        # Check available cuisines
        self.check_available_cuisines()
        
        # Check specific cuisines mentioned in the issue
        target_cuisines = ["Japanese", "Thai", "Desserts", "Pakistani", "Chinese"]
        
        for cuisine in target_cuisines:
            self.check_restaurants_by_cuisine(cuisine)
            
            # Get first restaurant for this cuisine to check menu items
            response = self.session.get(f"{self.base_url}/api/restaurants?cuisine={cuisine}&limit=1")
            if response.status_code == 200:
                data = response.json()
                restaurants = data.get('restaurants', [])
                if restaurants:
                    restaurant = restaurants[0]
                    self.check_menu_items_for_restaurant(restaurant['id'], restaurant['name'])

def main():
    checker = DatabaseChecker()
    checker.run_database_check()

if __name__ == "__main__":
    main()