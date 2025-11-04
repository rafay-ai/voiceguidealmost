from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
import uuid
from datetime import datetime, timezone

MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "voice_guide"

# More diverse menu items
MENU_ITEMS = [
    # Chinese Items
    {"name": "Chicken Chowmein", "category": "Chinese", "tags": ["chinese", "noodles"], "price": 450, "cuisine": "Chinese"},
    {"name": "Egg Fried Rice", "category": "Chinese", "tags": ["chinese", "rice"], "price": 400, "cuisine": "Chinese"},
    {"name": "Chicken Manchurian", "category": "Chinese", "tags": ["chinese", "chicken"], "price": 550, "cuisine": "Chinese"},
    {"name": "Sweet & Sour Chicken", "category": "Chinese", "tags": ["chinese", "chicken"], "price": 600, "cuisine": "Chinese"},
    {"name": "Spring Rolls (6 pcs)", "category": "Chinese", "tags": ["chinese", "appetizer"], "price": 300, "cuisine": "Chinese"},
    
    # Thai Items
    {"name": "Pad Thai", "category": "Thai", "tags": ["thai", "noodles"], "price": 650, "cuisine": "Thai"},
    {"name": "Thai Green Curry", "category": "Thai", "tags": ["thai", "curry"], "price": 700, "cuisine": "Thai"},
    {"name": "Tom Yum Soup", "category": "Thai", "tags": ["thai", "soup"], "price": 500, "cuisine": "Thai"},
    
    # More Pakistani Items
    {"name": "Chicken Pulao", "category": "Pakistani", "tags": ["pulao", "rice", "pakistani"], "price": 350, "cuisine": "Pakistani"},
    {"name": "Nihari (Beef)", "category": "Pakistani", "tags": ["nihari", "beef", "pakistani"], "price": 500, "cuisine": "Pakistani"},
    {"name": "Haleem", "category": "Pakistani", "tags": ["haleem", "pakistani"], "price": 400, "cuisine": "Pakistani"},
    {"name": "Chapli Kebab (2 pcs)", "category": "BBQ", "tags": ["kebab", "bbq"], "price": 280, "cuisine": "Pakistani"},
    
    # Vegetarian Items
    {"name": "Paneer Tikka", "category": "Indian", "tags": ["paneer", "vegetarian", "indian"], "price": 450, "cuisine": "Indian"},
    {"name": "Dal Makhani", "category": "Indian", "tags": ["dal", "vegetarian", "indian"], "price": 300, "cuisine": "Indian"},
    {"name": "Vegetable Curry", "category": "Indian", "tags": ["curry", "vegetarian", "indian"], "price": 350, "cuisine": "Indian"},
    
    # More Fast Food
    {"name": "Chicken Nuggets (9 pcs)", "category": "Fast Food", "tags": ["nuggets", "chicken", "fast food"], "price": 350, "cuisine": "Fast Food"},
    {"name": "Fish Burger", "category": "Fast Food", "tags": ["burger", "fish", "fast food"], "price": 400, "cuisine": "Fast Food"},
    {"name": "Cheese Fries", "category": "Fast Food", "tags": ["fries", "cheese", "fast food"], "price": 250, "cuisine": "Fast Food"},
    
    # Desserts
    {"name": "Kheer", "category": "Desserts", "tags": ["dessert", "sweet", "pakistani"], "price": 200, "cuisine": "Pakistani"},
    {"name": "Gajar Halwa", "category": "Desserts", "tags": ["dessert", "sweet", "pakistani"], "price": 250, "cuisine": "Pakistani"},

     # Add these to MENU_ITEMS array:
# More Chinese variety
    {"name": "Vegetable Chowmein", "category": "Chinese", "tags": ["chowmein", "noodles", "chinese", "vegetarian"], "price": 380, "cuisine": "Chinese"},
    {"name": "Chicken Chowmein", "category": "Chinese", "tags": ["chowmein", "noodles", "chinese", "chicken"], "price": 450, "cuisine": "Chinese"},
    {"name": "Beef Chowmein", "category": "Chinese", "tags": ["chowmein", "noodles", "chinese", "beef"], "price": 500, "cuisine": "Chinese"},

    {"name": "Vegetable Fried Rice", "category": "Chinese", "tags": ["fried rice", "rice", "chinese", "vegetarian"], "price": 350, "cuisine": "Chinese"},
    {"name": "Chicken Fried Rice", "category": "Chinese", "tags": ["fried rice", "rice", "chinese", "chicken"], "price": 400, "cuisine": "Chinese"},
    {"name": "Shrimp Fried Rice", "category": "Chinese", "tags": ["fried rice", "rice", "chinese", "seafood"], "price": 550, "cuisine": "Chinese"},

    {"name": "Chicken Manchurian", "category": "Chinese", "tags": ["manchurian", "chinese", "chicken", "spicy"], "price": 550, "cuisine": "Chinese"},
    {"name": "Vegetable Manchurian", "category": "Chinese", "tags": ["manchurian", "chinese", "vegetarian"], "price": 450, "cuisine": "Chinese"},

    {"name": "Hakka Noodles", "category": "Chinese", "tags": ["noodles", "chinese", "hakka"], "price": 420, "cuisine": "Chinese"},
    {"name": "Singapore Noodles", "category": "Chinese", "tags": ["noodles", "chinese", "singapore"], "price": 480, "cuisine": "Chinese"},

]

async def seed_items():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Get first restaurant for each cuisine
    restaurants = await db.restaurants.find({}, {"_id": 0}).to_list(None)
    
    cuisine_restaurant_map = {}
    for restaurant in restaurants:
        for cuisine in restaurant.get('cuisine', []):
            if cuisine not in cuisine_restaurant_map:
                cuisine_restaurant_map[cuisine] = restaurant['id']
    
    print(f"📦 Found restaurants for cuisines: {list(cuisine_restaurant_map.keys())}")
    
    added_count = 0
    for item_data in MENU_ITEMS:
        cuisine = item_data.pop('cuisine')
        restaurant_id = cuisine_restaurant_map.get(cuisine)
        
        if not restaurant_id:
            print(f"⚠️  No restaurant found for {cuisine}, skipping {item_data['name']}")
            continue
        
        menu_item = {
            "id": str(uuid.uuid4()),
            "restaurant_id": restaurant_id,
            "name": item_data["name"],
            "description": f"Delicious {item_data['name']}",
            "price": item_data["price"],
            "category": item_data["category"],
            "tags": item_data["tags"],
            "image": "/api/placeholder/food-item",
            "available": True,
            "preparation_time": 20,
            "spice_level": "medium",
            "is_vegetarian": "vegetarian" in item_data["tags"],
            "is_halal": True,
            "popularity_score": 4.0,
            "order_count": 0,
            "average_rating": 4.2,
            "rating_count": 10,
            "created_at": datetime.now(timezone.utc)
        }
        
        await db.menu_items.insert_one(menu_item)
        print(f"✅ Added: {menu_item['name']} to {cuisine} restaurant")
        added_count += 1
    
    print(f"\n🎉 Successfully added {added_count} menu items!")
    client.close()

if __name__ == "__main__":
    asyncio.run(seed_items())