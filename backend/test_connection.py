"""
Quick Test Script for Your Laptop
Run this to test if backend and database are working correctly
"""

import asyncio
import sys
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_connection():
    """Test MongoDB and Backend Connection"""
    
    print("=" * 60)
    print("VOICE GUIDE - CONNECTION TEST")
    print("=" * 60)
    print()
    
    # Test 1: Environment Variables
    print("📋 TEST 1: Environment Variables")
    print("-" * 60)
    mongo_url = os.getenv("MONGO_URL", "Not Found")
    db_name = os.getenv("DB_NAME", "Not Found")
    gemini_key = os.getenv("GEMINI_API_KEY", "Not Found")
    
    print(f"MONGO_URL: {mongo_url}")
    print(f"DB_NAME: {db_name}")
    print(f"GEMINI_API_KEY: {'Set ✅' if gemini_key != 'Not Found' else 'Not Set ❌'}")
    print()
    
    if mongo_url == "Not Found":
        print("❌ ERROR: MONGO_URL not found in .env file!")
        print("   Please create a .env file with:")
        print("   MONGO_URL=mongodb://localhost:27017")
        print("   DB_NAME=voice_guide")
        return
    
    # Test 2: MongoDB Connection
    print("📋 TEST 2: MongoDB Connection")
    print("-" * 60)
    
    try:
        client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=5000)
        # Test connection
        await client.admin.command('ping')
        print("✅ MongoDB connection successful!")
        print()
        
        # Test 3: Database and Collections
        print("📋 TEST 3: Database Collections")
        print("-" * 60)
        
        db = client[db_name]
        collections = await db.list_collection_names()
        
        print(f"Database: {db_name}")
        print(f"Collections found: {len(collections)}")
        print()
        
        # Count documents in each collection
        for collection_name in ['users', 'restaurants', 'menu_items', 'orders', 'cart_items', 'chat_messages']:
            if collection_name in collections:
                count = await db[collection_name].count_documents({})
                print(f"  ✅ {collection_name}: {count} documents")
            else:
                print(f"  ❌ {collection_name}: Collection not found")
        
        print()
        
        # Test 4: Check Orders for Matrix Factorization
        print("📋 TEST 4: Orders for Matrix Factorization")
        print("-" * 60)
        
        orders_count = await db.orders.count_documents({})
        print(f"Total orders: {orders_count}")
        
        if orders_count > 0:
            # Get one order to check structure
            sample_order = await db.orders.find_one({})
            print(f"Sample order structure:")
            print(f"  - user_id: {'✅' if 'user_id' in sample_order else '❌'}")
            print(f"  - items: {'✅' if 'items' in sample_order else '❌'}")
            print(f"  - status: {sample_order.get('status', 'Not found')}")
            
            if orders_count >= 5:
                print(f"\n✅ Sufficient data for Matrix Factorization ({orders_count} orders)")
            else:
                print(f"\n⚠️ Need more orders for good recommendations (have {orders_count}, need 5+)")
        else:
            print("❌ No orders found! Matrix Factorization won't work.")
            print("   Recommendation system will use content-based fallback.")
        
        print()
        
        # Test 5: Check Users
        print("📋 TEST 5: User Registration Test")
        print("-" * 60)
        
        users_count = await db.users.count_documents({})
        print(f"Total users: {users_count}")
        
        if users_count > 0:
            sample_user = await db.users.find_one({})
            print(f"Sample user structure:")
            print(f"  - username: {sample_user.get('username', 'Not found')}")
            print(f"  - email: {sample_user.get('email', 'Not found')}")
            print(f"  - password_hash: {'✅' if 'password_hash' in sample_user else '❌'}")
        
        print()
        
        # Success!
        print("=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print()
        print("Your backend setup is correct!")
        print("If signup/login still hangs, it's a frontend or network issue.")
        print()
        print("Next steps:")
        print("1. Make sure backend is running: uvicorn server:app --host 0.0.0.0 --port 8001 --reload")
        print("2. Test health endpoint in browser: http://localhost:8001/api/health")
        print("3. Check Network tab in browser during signup")
        print()
        
        client.close()
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        print()
        print("Common issues:")
        print("1. MongoDB not running - Start it with: net start MongoDB")
        print("2. Wrong connection string in .env file")
        print("3. Firewall blocking connection")
        print()

if __name__ == "__main__":
    print()
    asyncio.run(test_connection())
