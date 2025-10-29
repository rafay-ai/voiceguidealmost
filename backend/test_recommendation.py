"""
Test Script for Voice Guide Recommendation Engine
Simulates multiple users placing multiple orders to test:
- Order history analysis
- Reorder recommendations
- New item suggestions
- Dominant cuisine detection
"""

import asyncio
import aiohttp
import random
from datetime import datetime, timedelta
import json

# Configuration
BASE_URL = "http://0.0.0.0:8001"  # Change to your server URL
TEST_USERS_COUNT = 5
ORDERS_PER_USER = 20

# Test user profiles with different preferences
TEST_USER_PROFILES = [
    {
        "username": "biryani_lover",
        "email": "biryani_lover@test.com",
        "password": "test123",
        "phone": "+923001234501",
        "preferences": {
            "favorite_cuisines": ["Pakistani", "BBQ"],
            "dietary_restrictions": ["Halal"],
            "spice_preference": "hot"
        },
        "preferred_items": ["biryani", "karahi", "tikka", "seekh"],  # Will order these mostly
        "occasional_items": ["burger", "pizza"]  # Will order these sometimes
    },
    {
        "username": "fast_food_fan",
        "email": "fastfood_fan@test.com",
        "password": "test123",
        "phone": "+923001234502",
        "preferences": {
            "favorite_cuisines": ["Fast Food", "Chinese"],
            "dietary_restrictions": [],
            "spice_preference": "mild"
        },
        "preferred_items": ["burger", "pizza", "fries", "nugget"],
        "occasional_items": ["chowmein", "fried rice"]
    },
    {
        "username": "chinese_cuisine",
        "email": "chinese_cuisine@test.com",
        "password": "test123",
        "phone": "+923001234503",
        "preferences": {
            "favorite_cuisines": ["Chinese", "Thai"],
            "dietary_restrictions": [],
            "spice_preference": "medium"
        },
        "preferred_items": ["chowmein", "fried rice", "manchurian"],
        "occasional_items": ["biryani", "tikka"]
    },
    {
        "username": "vegetarian_user",
        "email": "vegetarian@test.com",
        "password": "test123",
        "phone": "+923001234504",
        "preferences": {
            "favorite_cuisines": ["Pakistani", "Indian"],
            "dietary_restrictions": ["Vegetarian"],
            "spice_preference": "medium"
        },
        "preferred_items": ["pulao", "curry", "paneer", "dal"],
        "occasional_items": ["pizza", "pasta"]
    },
    {
        "username": "mixed_preferences",
        "email": "mixed@test.com",
        "password": "test123",
        "phone": "+923001234505",
        "preferences": {
            "favorite_cuisines": ["Pakistani", "Fast Food", "Chinese"],
            "dietary_restrictions": [],
            "spice_preference": "hot"
        },
        "preferred_items": ["biryani", "burger", "chowmein", "pizza"],
        "occasional_items": ["tikka", "kebab", "wings"]
    }
]

# Test address for all users
TEST_ADDRESS = {
    "label": "Home",
    "district": "District South",
    "area": "Clifton",
    "street_address": "123 Test Street, Block 5",
    "landmark": "Near Test Mosque",
    "phone": "+923001234567",
    "is_default": True
}

class RecommendationTester:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = None
        self.test_users = []
        self.menu_items = []
        self.restaurants = []
        
    async def setup(self):
        """Initialize session and fetch available menu items"""
        self.session = aiohttp.ClientSession()
        print("🚀 Starting Recommendation Engine Test...")
        print(f"📍 Server: {self.base_url}\n")
        
    async def cleanup(self):
        """Close session"""
        if self.session:
            await self.session.close()
    
    async def register_and_setup_user(self, user_profile):
        """Register user and set up preferences"""
        try:
            # Register user
            async with self.session.post(
                f"{self.base_url}/auth/register",
                json={
                    "username": user_profile["username"],
                    "email": user_profile["email"],
                    "password": user_profile["password"],
                    "phone": user_profile["phone"]
                }
            ) as resp:
                if resp.status != 200:
                    # User might already exist, try login
                    async with self.session.post(
                        f"{self.base_url}/auth/login",
                        json={
                            "email": user_profile["email"],
                            "password": user_profile["password"]
                        }
                    ) as login_resp:
                        data = await login_resp.json()
                else:
                    data = await resp.json()
                
                token = data.get("access_token")
                user_id = data.get("user", {}).get("id")
                
                if not token:
                    print(f"❌ Failed to register/login user: {user_profile['username']}")
                    return None
                
                print(f"✅ User registered: {user_profile['username']}")
                
                # Set up preferences
                headers = {"Authorization": f"Bearer {token}"}
                async with self.session.post(
                    f"{self.base_url}/user/setup-preferences",
                    json=user_profile["preferences"],
                    headers=headers
                ) as pref_resp:
                    if pref_resp.status == 200:
                        print(f"   ✓ Preferences set for {user_profile['username']}")
                
                # Add address
                async with self.session.post(
                    f"{self.base_url}/user/addresses",
                    json=TEST_ADDRESS,
                    headers=headers
                ) as addr_resp:
                    if addr_resp.status == 200:
                        print(f"   ✓ Address added for {user_profile['username']}")
                
                return {
                    "profile": user_profile,
                    "token": token,
                    "user_id": user_id,
                    "headers": headers
                }
                
        except Exception as e:
            print(f"❌ Error setting up user {user_profile['username']}: {e}")
            return None
    
    async def fetch_menu_items(self):
        """Fetch available menu items and restaurants"""
        try:
            # Fetch restaurants
            async with self.session.get(f"{self.base_url}/restaurants?limit=50") as resp:
                data = await resp.json()
                self.restaurants = data.get("restaurants", [])
                print(f"📦 Fetched {len(self.restaurants)} restaurants")
            
            # Fetch menu items from each restaurant
            for restaurant in self.restaurants[:10]:  # Limit to first 10 restaurants
                async with self.session.get(
                    f"{self.base_url}/restaurants/{restaurant['id']}/menu"
                ) as resp:
                    data = await resp.json()
                    items = data.get("menu_items", [])
                    for item in items:
                        item["restaurant_name"] = restaurant["name"]
                        item["restaurant_cuisine"] = restaurant.get("cuisine", [])
                    self.menu_items.extend(items)
            
            print(f"📦 Fetched {len(self.menu_items)} menu items\n")
            
        except Exception as e:
            print(f"❌ Error fetching menu items: {e}")
    
    def find_items_matching_keywords(self, keywords):
        """Find menu items matching keywords"""
        matching_items = []
        for item in self.menu_items:
            item_text = f"{item.get('name', '')} {item.get('category', '')} {' '.join(item.get('tags', []))}".lower()
            for keyword in keywords:
                if keyword.lower() in item_text:
                    matching_items.append(item)
                    break
        return matching_items
    
    async def place_order(self, user, items_to_order):
        """Place an order for a user"""
        try:
            # Add items to cart
            for item in items_to_order:
                cart_data = {
                    "menu_item_id": item["id"],
                    "restaurant_id": item["restaurant_id"],
                    "quantity": random.randint(1, 2),
                    "special_instructions": ""
                }
                
                async with self.session.post(
                    f"{self.base_url}/cart/add",
                    json=cart_data,
                    headers=user["headers"]
                ) as resp:
                    if resp.status != 200:
                        print(f"   ⚠️  Failed to add item to cart: {item['name']}")
            
            # Get user's default address
            async with self.session.get(
                f"{self.base_url}/user/profile",
                headers=user["headers"]
            ) as resp:
                profile_data = await resp.json()
                addresses = profile_data.get("addresses", [])
                default_address = next((addr for addr in addresses if addr.get("is_default")), None)
                
                if not default_address:
                    print(f"   ❌ No default address for {user['profile']['username']}")
                    return False
            
            # Checkout
            checkout_data = {
                "address_id": default_address["id"],
                "payment_method": "cod",
                "special_instructions": ""
            }
            
            async with self.session.post(
                f"{self.base_url}/orders/checkout",
                json=checkout_data,
                headers=user["headers"]
            ) as resp:
                if resp.status == 200:
                    order_data = await resp.json()
                    order_number = order_data.get("order", {}).get("order_number")
                    return order_number
                else:
                    error = await resp.text()
                    print(f"   ❌ Checkout failed: {error}")
                    return False
                    
        except Exception as e:
            print(f"   ❌ Error placing order: {e}")
            return False
    
    async def simulate_user_orders(self, user, num_orders=20):
        """Simulate multiple orders for a user with realistic patterns"""
        print(f"\n👤 Simulating {num_orders} orders for: {user['profile']['username']}")
        print(f"   Preferences: {', '.join(user['profile']['preferences']['favorite_cuisines'])}")
        print(f"   Spice: {user['profile']['preferences']['spice_preference']}")
        
        preferred_keywords = user['profile']['preferred_items']
        occasional_keywords = user['profile']['occasional_items']
        
        orders_placed = 0
        
        for i in range(num_orders):
            # 70% chance to order preferred items, 30% occasional
            if random.random() < 0.7:
                keywords = preferred_keywords
            else:
                keywords = occasional_keywords
            
            # Find matching items
            matching_items = self.find_items_matching_keywords(keywords)
            
            if not matching_items:
                print(f"   ⚠️  No items found for keywords: {keywords}")
                continue
            
            # Select 1-3 random items
            items_to_order = random.sample(matching_items, min(random.randint(1, 3), len(matching_items)))
            
            # Place order
            order_number = await self.place_order(user, items_to_order)
            
            if order_number:
                orders_placed += 1
                item_names = [item['name'][:20] for item in items_to_order]
                print(f"   ✓ Order {orders_placed}/{num_orders}: {order_number} - {', '.join(item_names)}")
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.5)
        
        print(f"   ✅ Completed {orders_placed}/{num_orders} orders for {user['profile']['username']}\n")
        return orders_placed
    
    async def test_recommendations(self, user):
        """Test recommendation endpoint for a user"""
        print(f"\n🔍 Testing Recommendations for: {user['profile']['username']}")
        
        try:
            # Test chat with general food request
            async with self.session.post(
                f"{self.base_url}/chat",
                json={
                    "message": "I'm hungry, recommend me something",
                    "user_id": user["user_id"]
                },
                headers=user["headers"]
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    print(f"   📝 Response: {data.get('response')[:100]}...")
                    
                    reorder_items = data.get('reorder_items', [])
                    new_items = data.get('new_items', [])
                    history_summary = data.get('order_history_summary')
                    
                    if history_summary:
                        print(f"\n   📊 Order History:")
                        print(f"      Total Orders: {history_summary.get('total_orders')}")
                        print(f"      Dominant Cuisines: {', '.join(history_summary.get('dominant_cuisines', []))}")
                        print(f"      Most Ordered: {history_summary.get('most_ordered_cuisine')}")
                    
                    if reorder_items:
                        print(f"\n   🔁 Reorder Items ({len(reorder_items)}):")
                        for item in reorder_items[:3]:
                            print(f"      - {item['name']} (PKR {item['price']}) - Ordered {item.get('order_count_history')}x")
                    
                    if new_items:
                        print(f"\n   ✨ New Recommendations ({len(new_items)}):")
                        for item in new_items[:3]:
                            cuisines = ', '.join(item.get('restaurant_cuisine', []))
                            print(f"      - {item['name']} ({cuisines}) - PKR {item['price']}")
                    
                    return True
                else:
                    print(f"   ❌ Chat request failed: {resp.status}")
                    return False
                    
        except Exception as e:
            print(f"   ❌ Error testing recommendations: {e}")
            return False
    
    async def test_new_request(self, user):
        """Test 'something new' request"""
        print(f"\n🆕 Testing 'Something New' Request for: {user['profile']['username']}")
        
        try:
            async with self.session.post(
                f"{self.base_url}/chat",
                json={
                    "message": "Show me something new and unique",
                    "user_id": user["user_id"]
                },
                headers=user["headers"]
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   📝 Response: {data.get('response')[:150]}...")
                    
                    new_items = data.get('new_items', [])
                    if new_items:
                        print(f"\n   ✨ New Items Suggested ({len(new_items)}):")
                        for item in new_items[:3]:
                            cuisines = ', '.join(item.get('restaurant_cuisine', []))
                            reason = item.get('recommendation_reason', '')
                            print(f"      - {item['name']} ({cuisines}) - {reason}")
                    
                    return True
                else:
                    print(f"   ❌ Request failed")
                    return False
                    
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
    
    async def run_full_test(self):
        """Run complete test suite"""
        await self.setup()
        
        # Fetch menu items
        await self.fetch_menu_items()
        
        if not self.menu_items:
            print("❌ No menu items found. Make sure your database has data!")
            return
        
        # Register and setup users
        print("\n" + "="*60)
        print("STEP 1: Setting Up Test Users")
        print("="*60)
        
        for profile in TEST_USER_PROFILES[:TEST_USERS_COUNT]:
            user = await self.register_and_setup_user(profile)
            if user:
                self.test_users.append(user)
        
        print(f"\n✅ Set up {len(self.test_users)} test users")
        
        # Simulate orders for each user
        print("\n" + "="*60)
        print("STEP 2: Simulating User Orders")
        print("="*60)
        
        for user in self.test_users:
            await self.simulate_user_orders(user, ORDERS_PER_USER)
        
        # Test recommendations
        print("\n" + "="*60)
        print("STEP 3: Testing Recommendations")
        print("="*60)
        
        for user in self.test_users:
            await self.test_recommendations(user)
            await asyncio.sleep(1)
        
        # Test 'something new' requests
        print("\n" + "="*60)
        print("STEP 4: Testing 'Something New' Requests")
        print("="*60)
        
        for user in self.test_users:
            await self.test_new_request(user)
            await asyncio.sleep(1)
        
        # Summary
        print("\n" + "="*60)
        print("✅ TEST COMPLETED")
        print("="*60)
        print(f"Total Users: {len(self.test_users)}")
        print(f"Orders Per User: {ORDERS_PER_USER}")
        print(f"Total Orders Simulated: ~{len(self.test_users) * ORDERS_PER_USER}")
        print("\n💡 Now check the recommendations in your app!")
        print("   Each user should see:")
        print("   1. Reorder items from their frequent orders")
        print("   2. New recommendations from untried cuisines")
        print("   3. Dominant cuisine detection (3+ orders)")
        
        await self.cleanup()

async def main():
    """Main function"""
    tester = RecommendationTester(BASE_URL)
    await tester.run_full_test()

if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════╗
║     Voice Guide Recommendation Engine Test Script         ║
║                                                           ║
║  This script will:                                        ║
║  1. Create 5 test users with different preferences       ║
║  2. Simulate 20 orders per user (100 total)              ║
║  3. Test order history analysis                          ║
║  4. Test reorder recommendations                         ║
║  5. Test new item suggestions                            ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    asyncio.run(main())