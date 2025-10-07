import asyncio
import json
import os
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import uuid
import requests

# Load environment variables
load_dotenv()

# MongoDB connection
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

async def import_data():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    print("🚀 Starting data import...")

    try:
        # Clear existing collections
        print("📝 Clearing existing data...")
        await db.restaurants.drop()
        await db.menu_items.drop()
        await db.orders.drop()
        await db.users.drop()
        
        print("✅ Collections cleared")

        # Import restaurants
        print("🏪 Importing restaurants...")
        restaurants_data = await load_json_data('https://customer-assets.emergentagent.com/job_ceeafdeb-59e4-4607-9af5-2516590de819/artifacts/0be0tl36_food-delivery.restaurants.json')
        
        restaurants_for_db = []
        for restaurant in restaurants_data:
            # Convert MongoDB ObjectId format to UUID
            restaurant_id = str(uuid.uuid4())
            restaurant_doc = {
                'id': restaurant_id,
                'name': restaurant['name'],
                'description': restaurant['description'],
                'rating': restaurant['rating'],
                'price_range': restaurant['priceRange'],
                'cuisine': restaurant['cuisine'],
                'delivery_time': restaurant['deliveryTime'],
                'delivery_fee': restaurant['deliveryFee'],
                'minimum_order': restaurant['minimumOrder'],
                'is_active': restaurant['isActive'],
                'created_at': datetime.fromisoformat(restaurant['createdAt']['$date'].replace('Z', '+00:00')),
                'updated_at': datetime.fromisoformat(restaurant['updatedAt']['$date'].replace('Z', '+00:00')),
                'original_id': restaurant['_id']['$oid']  # Keep reference to original ID
            }
            restaurants_for_db.append(restaurant_doc)
        
        await db.restaurants.insert_many(restaurants_for_db)
        print(f"✅ Imported {len(restaurants_for_db)} restaurants")

        # Create mapping of original restaurant IDs to new UUIDs
        restaurant_id_mapping = {r['original_id']: r['id'] for r in restaurants_for_db}

        # Import menu items
        print("🍽️ Importing menu items...")
        menu_items_data = await load_json_data('https://customer-assets.emergentagent.com/job_ceeafdeb-59e4-4607-9af5-2516590de819/artifacts/l53m8hju_food-delivery.menuitems.json')
        
        menu_items_for_db = []
        menu_item_id_mapping = {}
        
        for item in menu_items_data:
            item_id = str(uuid.uuid4())
            original_restaurant_id = item['restaurant']['$oid']
            new_restaurant_id = restaurant_id_mapping.get(original_restaurant_id)
            
            if new_restaurant_id:  # Only add if restaurant exists
                item_doc = {
                    'id': item_id,
                    'name': item['name'],
                    'description': item['description'],
                    'price': item['price'],
                    'category': item['category'],
                    'restaurant_id': new_restaurant_id,
                    'image': item['image'],
                    'available': item['available'],
                    'preparation_time': item['preparationTime'],
                    'spice_level': item['spiceLevel'],
                    'is_vegetarian': item['isVegetarian'],
                    'is_halal': item['isHalal'],
                    'tags': item['tags'],
                    'popularity_score': item['popularityScore'],
                    'order_count': item['orderCount'],
                    'average_rating': item['averageRating'],
                    'rating_count': item['ratingCount'],
                    'created_at': datetime.fromisoformat(item['createdAt']['$date'].replace('Z', '+00:00')),
                    'updated_at': datetime.fromisoformat(item['updatedAt']['$date'].replace('Z', '+00:00')),
                    'original_id': item['_id']['$oid']
                }
                menu_items_for_db.append(item_doc)
                menu_item_id_mapping[item['_id']['$oid']] = item_id
        
        await db.menu_items.insert_many(menu_items_for_db)
        print(f"✅ Imported {len(menu_items_for_db)} menu items")

        # Create sample users
        print("👥 Creating sample users...")
        import bcrypt
        
        sample_users = [
            {
                'id': str(uuid.uuid4()),
                'username': 'Demo User',
                'email': 'demo@voiceguide.com',
                'password_hash': bcrypt.hashpw('demo123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
                'preferences': {},
                'dietary_restrictions': ['Halal'],
                'favorite_cuisines': ['Pakistani', 'Chinese'],
                'spice_preference': 'medium',
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc)
            },
            {
                'id': str(uuid.uuid4()),
                'username': 'Ahmed Khan',
                'email': 'ahmed@example.com',
                'password_hash': bcrypt.hashpw('password123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
                'preferences': {},
                'dietary_restrictions': ['Halal', 'Vegetarian'],
                'favorite_cuisines': ['Pakistani', 'Indian'],
                'spice_preference': 'hot',
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc)
            },
            {
                'id': str(uuid.uuid4()),
                'username': 'Sara Ali',
                'email': 'sara@example.com', 
                'password_hash': bcrypt.hashpw('password123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
                'preferences': {},
                'dietary_restrictions': ['Vegetarian'],
                'favorite_cuisines': ['Chinese', 'Italian'],
                'spice_preference': 'mild',
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc)
            }
        ]
        
        await db.users.insert_many(sample_users)
        print(f"✅ Created {len(sample_users)} sample users")
        
        # Import orders (simplified version for recommendation engine)
        print("📦 Importing orders...")
        orders_data = await load_json_data('https://customer-assets.emergentagent.com/job_ceeafdeb-59e4-4607-9af5-2516590de819/artifacts/viol0dzp_food-delivery.orders.json')
        
        orders_for_db = []
        user_ids = [user['id'] for user in sample_users]
        
        for i, order in enumerate(orders_data[:50]):  # Import first 50 orders
            # Assign orders to sample users cyclically
            user_id = user_ids[i % len(user_ids)]
            
            # Convert order items
            converted_items = []
            for item in order['items']:
                original_menu_item_id = item['menuItem']['$oid']
                new_menu_item_id = menu_item_id_mapping.get(original_menu_item_id)
                
                if new_menu_item_id:
                    converted_items.append({
                        'menu_item_id': new_menu_item_id,
                        'quantity': item['quantity'],
                        'price': item['price'],
                        'special_instructions': item['specialInstructions']
                    })
            
            if converted_items:  # Only add orders with valid items
                original_restaurant_id = order['restaurant']['$oid']
                new_restaurant_id = restaurant_id_mapping.get(original_restaurant_id)
                
                if new_restaurant_id:
                    order_doc = {
                        'id': str(uuid.uuid4()),
                        'order_number': order['orderNumber'],
                        'user_id': user_id,
                        'restaurant_id': new_restaurant_id,
                        'items': converted_items,
                        'delivery_address': order['deliveryAddress'],
                        'payment_method': order['paymentMethod'],
                        'payment_status': order['paymentStatus'],
                        'order_status': order['orderStatus'],
                        'pricing': order['pricing'],
                        'estimated_delivery_time': datetime.fromisoformat(order['estimatedDeliveryTime']['$date'].replace('Z', '+00:00')) if order.get('estimatedDeliveryTime') else None,
                        'actual_delivery_time': datetime.fromisoformat(order['actualDeliveryTime']['$date'].replace('Z', '+00:00')) if order.get('actualDeliveryTime') else None,
                        'created_at': datetime.fromisoformat(order['createdAt']['$date'].replace('Z', '+00:00')),
                        'updated_at': datetime.fromisoformat(order['updatedAt']['$date'].replace('Z', '+00:00'))
                    }
                    orders_for_db.append(order_doc)
        
        await db.orders.insert_many(orders_for_db)
        print(f"✅ Imported {len(orders_for_db)} orders")

        # Create indexes for better performance
        print("🔍 Creating database indexes...")
        await db.restaurants.create_index("cuisine")
        await db.restaurants.create_index("is_active")
        await db.menu_items.create_index("restaurant_id")
        await db.menu_items.create_index("category")
        await db.menu_items.create_index("available")
        await db.menu_items.create_index([("popularity_score", -1), ("order_count", -1)])
        await db.orders.create_index("user_id")
        await db.orders.create_index("restaurant_id")
        await db.orders.create_index([("created_at", -1)])
        await db.users.create_index("email", unique=True)
        
        print("✅ Database indexes created")
        
        print("🎉 Data import completed successfully!")
        print(f"📊 Summary:")
        print(f"   - Restaurants: {len(restaurants_for_db)}")
        print(f"   - Menu Items: {len(menu_items_for_db)}")
        print(f"   - Orders: {len(orders_for_db)}")
        print(f"   - Users: {len(sample_users)}")
        
    except Exception as e:
        print(f"❌ Error during import: {e}")
        raise
    finally:
        client.close()

async def load_json_data(url):
    """Load JSON data from URL"""
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

if __name__ == "__main__":
    asyncio.run(import_data())