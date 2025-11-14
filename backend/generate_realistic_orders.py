"""
Generate Realistic Orders with 50 Users
Mixed language (Roman Urdu + English) for realistic Pakistani communication
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import random
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv
import uuid

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "voice_guide")

# Realistic Pakistani names (mixed)
FIRST_NAMES = [
    "Ahmed", "Ali", "Hassan", "Hamza", "Usman", "Bilal", "Fahad", "Faisal", "Imran", "Kamran",
    "Zain", "Shahzaib", "Talha", "Rizwan", "Arslan", "Saad", "Waleed", "Haris", "Danish", "Asad",
    "Fatima", "Ayesha", "Sara", "Zainab", "Maryam", "Hira", "Sana", "Aisha", "Noor", "Amna",
    "Umer", "Adnan", "Junaid", "Aqib", "Shoaib", "Waqas", "Yasir", "Zeeshan", "Tariq", "Naveed",
    "Mehwish", "Rabia", "Sidra", "Zara", "Aliza", "Nimra", "Hafsa", "Bushra", "Mahnoor", "Anum"
]

LAST_NAMES = [
    "Khan", "Ahmed", "Ali", "Hussain", "Shah", "Malik", "Raza", "Hassan", "Abbas", "Syed",
    "Butt", "Awan", "Chaudhry", "Qureshi", "Sheikh", "Mirza", "Mughal", "Abbasi", "Rizvi", "Zaidi"
]

# Realistic food preferences (mixed Roman Urdu + English)
FOOD_PREFERENCES = [
    "Biryani lover", "BBQ fan", "Fast food junkie", "Desi food only",
    "Chinese khane ka shoukeen", "Pizza addict", "Burger person", "Spicy food lover",
    "Halal zabih only", "Healthy eating", "Sweet tooth", "Karahi fan",
    "Student Biryani regular", "Howdy fan", "BBQ Tonight regular", "Jalal Sons customer"
]

# Dietary restrictions (realistic mix)
DIETARY_OPTIONS = [
    [],  # Most people don't have restrictions
    [],
    [],
    ["halal"],
    ["halal"],
    ["vegetarian"],
    ["gluten-free"]
]

# Spice preferences
SPICE_LEVELS = ["mild", "mild", "medium", "medium", "medium", "hot", "hot"]

# Cuisines
ALL_CUISINES = ["Pakistani", "Chinese", "Fast Food", "BBQ", "Desserts", "Japanese", "Thai", "Indian"]


async def generate_50_users_and_orders():
    """Generate 50 realistic users with order history"""
    
    print("\n" + "="*80)
    print("GENERATING 50 USERS WITH REALISTIC ORDERS")
    print("Mixed Language (Roman Urdu + English)")
    print("="*80)
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Get available menu items and restaurants
    menu_items = await db.menu_items.find({"available": True}, {"_id": 0}).to_list(None)
    restaurants = await db.restaurants.find({"is_active": True}, {"_id": 0}).to_list(None)
    
    if not menu_items or not restaurants:
        print("❌ No menu items or restaurants found!")
        return
    
    print(f"Found {len(menu_items)} menu items and {len(restaurants)} restaurants")
    
    total_orders_created = 0
    total_ratings_created = 0
    
    for i in range(50):
        # Generate realistic user data
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        username = f"{first_name.lower()}_{last_name.lower()}_{i}"
        email = f"{username}@gmail.com"
        
        # Random preferences
        favorite_cuisines = random.sample(ALL_CUISINES, random.randint(2, 4))
        dietary_restrictions = random.choice(DIETARY_OPTIONS)
        spice_preference = random.choice(SPICE_LEVELS)
        
        # Check if user exists
        existing_user = await db.users.find_one({"username": username})
        
        if not existing_user:
            # Create new user
            user_id = str(uuid.uuid4())
            user_doc = {
                "id": user_id,
                "username": username,
                "email": email,
                "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5F6lSpJ8SgJLe",  # "password123"
                "favorite_cuisines": favorite_cuisines,
                "dietary_restrictions": dietary_restrictions,
                "spice_preference": spice_preference,
                "addresses": [{
                    "address": f"House {random.randint(1, 999)}, Street {random.randint(1, 50)}, Karachi",
                    "lat": 24.8607 + random.uniform(-0.1, 0.1),
                    "lng": 67.0011 + random.uniform(-0.1, 0.1),
                    "is_default": True
                }],
                "preferences_set": True,
                "created_at": datetime.now(timezone.utc)
            }
            await db.users.insert_one(user_doc)
            print(f"✅ Created user {i+1}/50: {username}")
        else:
            user_id = existing_user["id"]
            print(f"⚠️  User {i+1}/50 already exists: {username}")
        
        # Generate 5-15 orders per user (more realistic)
        num_orders = random.randint(5, 15)
        
        for order_num in range(num_orders):
            # Select restaurant
            restaurant = random.choice(restaurants)
            
            # Select 1-4 items from that restaurant
            restaurant_items = [item for item in menu_items if item["restaurant_id"] == restaurant["id"]]
            if not restaurant_items:
                continue
            
            selected_items = random.sample(restaurant_items, min(random.randint(1, 4), len(restaurant_items)))
            
            order_items = []
            total_amount = 0
            
            for item in selected_items:
                quantity = random.randint(1, 3)
                price = item["price"] * quantity
                total_amount += price
                
                order_items.append({
                    "menu_item_id": item["id"],
                    "name": item["name"],
                    "quantity": quantity,
                    "price": item["price"],
                    "special_instructions": ""
                })
            
            # Create order with random date in past 60 days
            days_ago = random.randint(1, 60)
            order_date = datetime.now(timezone.utc) - timedelta(days=days_ago)
            
            order_doc = {
                "id": f"order_{user_id}_{order_num}_{order_date.timestamp()}",
                "user_id": user_id,
                "restaurant_id": restaurant["id"],
                "items": order_items,
                "total_amount": total_amount,
                "delivery_fee": 50,
                "order_status": "Delivered",  # Important for Matrix Factorization
                "payment_status": "Paid",
                "delivery_address": {
                    "address": f"House {random.randint(1, 999)}, Karachi",
                    "lat": 24.8607,
                    "lng": 67.0011
                },
                "created_at": order_date,
                "updated_at": order_date
            }
            
            await db.orders.insert_one(order_doc)
            total_orders_created += 1
            
            # Generate ratings for some items (70% chance)
            for order_item in order_items:
                if random.random() < 0.7:  # 70% of items get rated
                    rating = random.choices(
                        [1, 2, 3, 4, 5],
                        weights=[5, 10, 20, 35, 30]  # Most ratings are 3-5
                    )[0]
                    
                    rating_doc = {
                        "id": str(uuid.uuid4()),
                        "user_id": user_id,
                        "menu_item_id": order_item["menu_item_id"],
                        "restaurant_id": restaurant["id"],
                        "rating": rating,
                        "review": "",
                        "created_at": order_date,
                        "updated_at": order_date
                    }
                    
                    await db.ratings.insert_one(rating_doc)
                    total_ratings_created += 1
        
        # Progress indicator
        if (i + 1) % 10 == 0:
            print(f"Progress: {i+1}/50 users created...")
    
    print(f"\n✅ Generation Complete!")
    print(f"   Total Users: 50")
    print(f"   Total Orders: {total_orders_created}")
    print(f"   Total Ratings: {total_ratings_created}")
    print(f"   Average Orders per User: {total_orders_created / 50:.1f}")
    print(f"   Average Ratings per User: {total_ratings_created / 50:.1f}")
    
    # Update menu item average ratings
    print(f"\n📊 Updating menu item average ratings...")
    for item in menu_items:
        ratings_cursor = db.ratings.find(
            {"menu_item_id": item["id"]},
            {"_id": 0, "rating": 1}
        )
        ratings = await ratings_cursor.to_list(None)
        
        if ratings:
            avg_rating = sum(r["rating"] for r in ratings) / len(ratings)
            await db.menu_items.update_one(
                {"id": item["id"]},
                {"$set": {
                    "average_rating": round(avg_rating, 2),
                    "total_ratings": len(ratings)
                }}
            )
    
    print(f"✅ Updated average ratings for all items")
    
    client.close()


if __name__ == "__main__":
    print("\n🚀 Starting realistic order generation...")
    print("This will create:")
    print("  - 50 Pakistani users")
    print("  - 250-750 orders (5-15 per user)")
    print("  - 175-525 ratings (70% of orders)")
    print("\nPress Ctrl+C to cancel...")
    
    try:
        asyncio.run(generate_50_users_and_orders())
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
