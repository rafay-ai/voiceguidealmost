#!/usr/bin/env python3
"""
Populate test data for Voice Guide app testing
"""
import asyncio
import uuid
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from datetime import datetime, timezone

# Load environment
load_dotenv('backend/.env')
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

async def populate_test_data():
    """Populate minimal test data for testing"""
    
    # Clear existing data
    await db.restaurants.delete_many({})
    await db.menu_items.delete_many({})
    
    # Create test restaurants
    restaurants = [
        {
            "id": str(uuid.uuid4()),
            "name": "Student Biryani",
            "description": "Famous for authentic Karachi-style biryani",
            "rating": 4.5,
            "price_range": "Budget",
            "cuisine": ["Pakistani", "Biryani"],
            "delivery_time": "30-40 min",
            "delivery_fee": 50,
            "minimum_order": 300,
            "is_active": True,
            "image": "/api/placeholder/restaurant",
            "created_at": datetime.now(timezone.utc)
        },
        {
            "id": str(uuid.uuid4()),
            "name": "KFC",
            "description": "Finger lickin' good chicken",
            "rating": 4.2,
            "price_range": "Medium",
            "cuisine": ["Fast Food", "Chicken"],
            "delivery_time": "25-35 min",
            "delivery_fee": 60,
            "minimum_order": 400,
            "is_active": True,
            "image": "/api/placeholder/restaurant",
            "created_at": datetime.now(timezone.utc)
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Dragon City",
            "description": "Authentic Chinese cuisine",
            "rating": 4.0,
            "price_range": "Medium",
            "cuisine": ["Chinese", "Thai"],
            "delivery_time": "35-45 min",
            "delivery_fee": 70,
            "minimum_order": 500,
            "is_active": True,
            "image": "/api/placeholder/restaurant",
            "created_at": datetime.now(timezone.utc)
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Sweet Treats",
            "description": "Delicious desserts and sweets",
            "rating": 4.3,
            "price_range": "Budget",
            "cuisine": ["Desserts", "Sweets"],
            "delivery_time": "20-30 min",
            "delivery_fee": 40,
            "minimum_order": 200,
            "is_active": True,
            "image": "/api/placeholder/restaurant",
            "created_at": datetime.now(timezone.utc)
        }
    ]
    
    # Insert restaurants
    await db.restaurants.insert_many(restaurants)
    print(f"✅ Inserted {len(restaurants)} restaurants")
    
    # Create test menu items
    menu_items = []
    
    # Student Biryani items
    student_biryani_id = restaurants[0]["id"]
    menu_items.extend([
        {
            "id": str(uuid.uuid4()),
            "name": "Chicken Biryani",
            "description": "Aromatic basmati rice with tender chicken",
            "price": 350,
            "category": "Main Course",
            "restaurant_id": student_biryani_id,
            "image": "/api/placeholder/food-item",
            "available": True,
            "preparation_time": 25,
            "spice_level": "medium",
            "is_vegetarian": False,
            "is_halal": True,
            "tags": ["biryani", "chicken", "rice", "pakistani"],
            "popularity_score": 8.5,
            "order_count": 150,
            "average_rating": 4.6,
            "rating_count": 45,
            "created_at": datetime.now(timezone.utc)
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Mutton Biryani",
            "description": "Traditional mutton biryani with aromatic spices",
            "price": 450,
            "category": "Main Course",
            "restaurant_id": student_biryani_id,
            "image": "/api/placeholder/food-item",
            "available": True,
            "preparation_time": 30,
            "spice_level": "hot",
            "is_vegetarian": False,
            "is_halal": True,
            "tags": ["biryani", "mutton", "rice", "pakistani"],
            "popularity_score": 7.8,
            "order_count": 89,
            "average_rating": 4.4,
            "rating_count": 32,
            "created_at": datetime.now(timezone.utc)
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Raita",
            "description": "Cool yogurt side dish",
            "price": 80,
            "category": "Sides",
            "restaurant_id": student_biryani_id,
            "image": "/api/placeholder/food-item",
            "available": True,
            "preparation_time": 5,
            "spice_level": "mild",
            "is_vegetarian": True,
            "is_halal": True,
            "tags": ["raita", "yogurt", "side", "vegetarian"],
            "popularity_score": 6.5,
            "order_count": 200,
            "average_rating": 4.2,
            "rating_count": 67,
            "created_at": datetime.now(timezone.utc)
        }
    ])
    
    # KFC items
    kfc_id = restaurants[1]["id"]
    menu_items.extend([
        {
            "id": str(uuid.uuid4()),
            "name": "Zinger Burger",
            "description": "Spicy chicken burger with crispy coating",
            "price": 320,
            "category": "Burgers",
            "restaurant_id": kfc_id,
            "image": "/api/placeholder/food-item",
            "available": True,
            "preparation_time": 15,
            "spice_level": "hot",
            "is_vegetarian": False,
            "is_halal": True,
            "tags": ["burger", "chicken", "spicy", "fast food"],
            "popularity_score": 9.2,
            "order_count": 300,
            "average_rating": 4.7,
            "rating_count": 89,
            "created_at": datetime.now(timezone.utc)
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Chicken Pieces (8 pcs)",
            "description": "Crispy fried chicken pieces",
            "price": 850,
            "category": "Chicken",
            "restaurant_id": kfc_id,
            "image": "/api/placeholder/food-item",
            "available": True,
            "preparation_time": 20,
            "spice_level": "medium",
            "is_vegetarian": False,
            "is_halal": True,
            "tags": ["chicken", "fried", "pieces", "fast food"],
            "popularity_score": 8.8,
            "order_count": 180,
            "average_rating": 4.5,
            "rating_count": 56,
            "created_at": datetime.now(timezone.utc)
        }
    ])
    
    # Dragon City items
    dragon_city_id = restaurants[2]["id"]
    menu_items.extend([
        {
            "id": str(uuid.uuid4()),
            "name": "Chicken Chowmein",
            "description": "Stir-fried noodles with chicken and vegetables",
            "price": 380,
            "category": "Noodles",
            "restaurant_id": dragon_city_id,
            "image": "/api/placeholder/food-item",
            "available": True,
            "preparation_time": 18,
            "spice_level": "medium",
            "is_vegetarian": False,
            "is_halal": True,
            "tags": ["chowmein", "noodles", "chicken", "chinese"],
            "popularity_score": 7.5,
            "order_count": 120,
            "average_rating": 4.1,
            "rating_count": 38,
            "created_at": datetime.now(timezone.utc)
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Chicken Fried Rice",
            "description": "Wok-fried rice with chicken and vegetables",
            "price": 350,
            "category": "Rice",
            "restaurant_id": dragon_city_id,
            "image": "/api/placeholder/food-item",
            "available": True,
            "preparation_time": 15,
            "spice_level": "mild",
            "is_vegetarian": False,
            "is_halal": True,
            "tags": ["fried rice", "chicken", "rice", "chinese"],
            "popularity_score": 7.2,
            "order_count": 95,
            "average_rating": 4.0,
            "rating_count": 29,
            "created_at": datetime.now(timezone.utc)
        }
    ])
    
    # Sweet Treats items
    sweet_treats_id = restaurants[3]["id"]
    menu_items.extend([
        {
            "id": str(uuid.uuid4()),
            "name": "Gulab Jamun (4 pcs)",
            "description": "Sweet milk dumplings in sugar syrup",
            "price": 180,
            "category": "Desserts",
            "restaurant_id": sweet_treats_id,
            "image": "/api/placeholder/food-item",
            "available": True,
            "preparation_time": 10,
            "spice_level": "mild",
            "is_vegetarian": True,
            "is_halal": True,
            "tags": ["gulab jamun", "dessert", "sweet", "vegetarian"],
            "popularity_score": 8.0,
            "order_count": 160,
            "average_rating": 4.4,
            "rating_count": 52,
            "created_at": datetime.now(timezone.utc)
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Kulfi Ice Cream",
            "description": "Traditional Pakistani ice cream",
            "price": 120,
            "category": "Desserts",
            "restaurant_id": sweet_treats_id,
            "image": "/api/placeholder/food-item",
            "available": True,
            "preparation_time": 5,
            "spice_level": "mild",
            "is_vegetarian": True,
            "is_halal": True,
            "tags": ["kulfi", "ice cream", "dessert", "cold"],
            "popularity_score": 7.8,
            "order_count": 140,
            "average_rating": 4.3,
            "rating_count": 41,
            "created_at": datetime.now(timezone.utc)
        }
    ])
    
    # Insert menu items
    await db.menu_items.insert_many(menu_items)
    print(f"✅ Inserted {len(menu_items)} menu items")
    
    # Verify data
    restaurant_count = await db.restaurants.count_documents({})
    menu_count = await db.menu_items.count_documents({})
    
    print(f"\n📊 Database populated:")
    print(f"   Restaurants: {restaurant_count}")
    print(f"   Menu Items: {menu_count}")
    
    return True

if __name__ == "__main__":
    asyncio.run(populate_test_data())