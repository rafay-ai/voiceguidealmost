"""
Fixed Comprehensive Testing Suite for Voice Guide
- Fixed order status field names
- Better error handling
- Detailed logging
"""

import asyncio
import aiohttp
import json
from datetime import datetime
from typing import List, Dict
import random
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
import uuid

load_dotenv()

# Configuration
BASE_URL = "http://localhost:8001"
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "voice_guide")

# Test Results Storage
results = {
    "chatbot_tests": [],
    "order_tests": [],
    "recommendation_tests": [],
    "matrix_evaluation": {},
    "timestamp": datetime.now().isoformat()
}

# Chatbot test cases (same as before)
CHATBOT_TEST_CASES = [
    {"lang": "en", "prompt": "I'm hungry", "expected_intent": "food_recommendation"},
    {"lang": "en", "prompt": "Show me something to eat", "expected_intent": "food_recommendation"},
    {"lang": "en", "prompt": "I want to reorder", "expected_intent": "reorder"},
    {"lang": "en", "prompt": "Order my usual", "expected_intent": "reorder"},
    {"lang": "en", "prompt": "Show me something new", "expected_intent": "new_items"},
    {"lang": "en", "prompt": "I want biryani", "expected_intent": "specific_cuisine"},
    {"lang": "en", "prompt": "Show me burgers", "expected_intent": "specific_cuisine"},
    {"lang": "roman_urdu", "prompt": "Bhook lagi hai", "expected_intent": "food_recommendation"},
    {"lang": "roman_urdu", "prompt": "Kuch khana chahiye", "expected_intent": "food_recommendation"},
    {"lang": "roman_urdu", "prompt": "Biryani mangwao", "expected_intent": "specific_cuisine"},
]


async def test_chatbot(session, token, test_case):
    """Test a single chatbot interaction with better error handling"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "message": test_case["prompt"],
            "user_id": "test_user",  # Add user_id
            "session_id": f"test_session_{datetime.now().timestamp()}"
        }
        
        async with session.post(
            f"{BASE_URL}/api/chat", 
            json=payload, 
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                
                result = {
                    "prompt": test_case["prompt"],
                    "language": test_case["lang"],
                    "expected_intent": test_case["expected_intent"],
                    "detected_intent": data.get("intent", "unknown"),
                    "response": data.get("response", "")[:100],  # Limit length
                    "reorder_items_count": len(data.get("reorder_items", [])),
                    "new_items_count": len(data.get("new_items", [])),
                    "success": data.get("intent") == test_case["expected_intent"],
                    "timestamp": datetime.now().isoformat()
                }
                
                return result
            else:
                error_text = await resp.text()
                print(f"❌ Chat API error: HTTP {resp.status} - {error_text[:200]}")
                return {
                    "prompt": test_case["prompt"],
                    "error": f"HTTP {resp.status}: {error_text[:100]}",
                    "success": False
                }
    except asyncio.TimeoutError:
        print(f"❌ Timeout for prompt: {test_case['prompt']}")
        return {"prompt": test_case["prompt"], "error": "Timeout", "success": False}
    except Exception as e:
        print(f"❌ Error testing '{test_case['prompt']}': {e}")
        return {"prompt": test_case["prompt"], "error": str(e), "success": False}


async def create_test_users_and_orders(db):
    """Create realistic test users and orders - FIXED VERSION"""
    
    print("\n" + "="*80)
    print("CREATING TEST USERS AND ORDERS FOR MATRIX FACTORIZATION")
    print("="*80)
    
    try:
        # Get available menu items and restaurants
        menu_items = await db.menu_items.find({"available": True}, {"_id": 0}).to_list(None)
        restaurants = await db.restaurants.find({"is_active": True}, {"_id": 0}).to_list(None)
        
        print(f"Found {len(menu_items)} menu items and {len(restaurants)} restaurants")
        
        if not menu_items or not restaurants:
            print("❌ No menu items or restaurants found!")
            return []
        
        # Create test users with different preferences
        test_users = [
            {
                "username": f"test_user_{i}_{datetime.now().timestamp()}", 
                "email": f"test{i}_{datetime.now().timestamp()}@test.com", 
                "password": "test123",
                "favorite_cuisines": random.sample(["Pakistani", "Chinese", "Fast Food", "BBQ", "Desserts"], 2),
                "dietary_restrictions": random.choice([[], ["Vegetarian"], ["Halal"]]),
                "spice_preference": random.choice(["mild", "medium", "hot"])
            }
            for i in range(5)  # Reduced to 5 for faster testing
        ]
        
        created_orders = []
        
        async with aiohttp.ClientSession() as session:
            for user_data in test_users:
                try:
                    # Register user
                    async with session.post(
                        f"{BASE_URL}/api/auth/register", 
                        json=user_data,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as resp:
                        if resp.status == 200:
                            user_info = await resp.json()
                            user_id = user_info["user"]["id"]
                            
                            print(f"✅ Created user: {user_data['username']}")
                            
                            # Create orders directly in database
                            num_orders = random.randint(3, 5)
                            for order_num in range(num_orders):
                                # Select 1-3 random items
                                selected_items = random.sample(menu_items, min(len(menu_items), random.randint(1, 3)))
                                
                                order_items = []
                                subtotal = 0
                                restaurant_id = selected_items[0]["restaurant_id"]
                                
                                for item in selected_items:
                                    quantity = random.randint(1, 2)
                                    price = item["price"] * quantity
                                    subtotal += price
                                    
                                    order_items.append({
                                        "menu_item_id": item["id"],
                                        "quantity": quantity,
                                        "price": item["price"],
                                        "special_instructions": ""
                                    })
                                
                                # Get restaurant for delivery fee
                                restaurant = await db.restaurants.find_one(
                                    {"id": restaurant_id},
                                    {"_id": 0, "delivery_fee": 1}
                                )
                                delivery_fee = restaurant.get("delivery_fee", 50) if restaurant else 50
                                tax = subtotal * 0.05
                                total = subtotal + delivery_fee + tax
                                
                                # Create order document - USING CORRECT FIELD NAMES
                                order_doc = {
                                    "id": str(uuid.uuid4()),
                                    "order_number": f"TEST{random.randint(1000, 9999)}",
                                    "user_id": user_id,
                                    "restaurant_id": restaurant_id,
                                    "items": order_items,
                                    "delivery_address": {
                                        "district": "District Central",
                                        "area": "Gulberg",
                                        "street_address": "Test Address",
                                        "phone": "03001234567"
                                    },
                                    "payment_method": "cod",
                                    "payment_status": "paid",
                                    "order_status": "Delivered",  # CORRECT FIELD NAME
                                    "pricing": {
                                        "subtotal": float(subtotal),
                                        "delivery_fee": float(delivery_fee),
                                        "tax": float(tax),
                                        "total": float(total)
                                    },
                                    "estimated_delivery_time": datetime.now(),
                                    "actual_delivery_time": datetime.now(),
                                    "created_at": datetime.now(),
                                    "updated_at": datetime.now()
                                }
                                
                                # Insert into database
                                await db.orders.insert_one(order_doc)
                                created_orders.append(order_doc)
                            
                            print(f"  📦 Created {num_orders} orders for {user_data['username']}")
                        else:
                            error_text = await resp.text()
                            print(f"❌ Failed to register {user_data['username']}: {error_text[:100]}")
                    
                except Exception as e:
                    print(f"❌ Error creating user {user_data['username']}: {e}")
                    import traceback
                    traceback.print_exc()
        
        print(f"\n✅ Total orders created: {len(created_orders)}")
        return created_orders
    
    except Exception as e:
        print(f"❌ Critical error in create_test_users_and_orders: {e}")
        import traceback
        traceback.print_exc()
        return []


async def check_existing_orders(db):
    """Check how many orders exist in the database"""
    try:
        total_orders = await db.orders.count_documents({})
        delivered_orders = await db.orders.count_documents({"order_status": "Delivered"})
        
        print(f"\n📊 Database Status:")
        print(f"  Total Orders: {total_orders}")
        print(f"  Delivered Orders: {delivered_orders}")
        
        # Get sample order to check structure
        sample = await db.orders.find_one({}, {"_id": 0})
        if sample:
            print(f"\n  Sample Order Fields: {list(sample.keys())}")
            print(f"  Order Status Field: {sample.get('order_status', 'NOT FOUND')}")
        
        return {"total": total_orders, "delivered": delivered_orders}
    except Exception as e:
        print(f"❌ Error checking orders: {e}")
        return {"total": 0, "delivered": 0}


async def evaluate_recommendations(db, token):
    """Evaluate recommendation accuracy with better error handling"""
    
    print("\n📊 Evaluating Recommendation System...")
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        async with aiohttp.ClientSession() as session:
            # Get user profile first
            async with session.get(
                f"{BASE_URL}/api/user/profile", 
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    print(f"❌ Failed to get user profile: {resp.status}")
                    return {}
                
                user_info = await resp.json()
                user_id = user_info["id"]
            
            # Get recommendations
            async with session.get(
                f"{BASE_URL}/api/recommendations?limit=10", 
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    recommendations = data.get("recommendations", [])
                    reorder_items = data.get("reorder_items", [])
                    new_items = data.get("new_items", [])
                    
                    print(f"  ✅ Got {len(recommendations)} recommendations")
                    print(f"     - Reorder items: {len(reorder_items)}")
                    print(f"     - New items: {len(new_items)}")
                    
                    # Get user's past orders
                    past_orders = await db.orders.find({
                        "user_id": user_id,
                        "order_status": "Delivered"
                    }, {"_id": 0}).to_list(None)
                    
                    # Extract items from past orders
                    ordered_item_ids = set()
                    for order in past_orders:
                        for item in order.get("items", []):
                            ordered_item_ids.add(item["menu_item_id"])
                    
                    # Calculate metrics
                    total_recommendations = len(recommendations)
                    reorder_accuracy = (len([r for r in reorder_items if r.get("id") in ordered_item_ids]) / 
                                       max(len(reorder_items), 1))
                    new_items_novelty = (len([n for n in new_items if n.get("id") not in ordered_item_ids]) / 
                                        max(len(new_items), 1))
                    
                    # Diversity
                    unique_restaurants = len(set(r.get("restaurant_id") for r in recommendations if r.get("restaurant_id")))
                    diversity_score = unique_restaurants / max(total_recommendations, 1)
                    
                    # Overall score
                    overall_score = (
                        reorder_accuracy * 0.4 +
                        new_items_novelty * 0.4 +
                        diversity_score * 0.2
                    ) * 100
                    
                    evaluation = {
                        "total_recommendations": total_recommendations,
                        "reorder_items_count": len(reorder_items),
                        "new_items_count": len(new_items),
                        "reorder_accuracy": f"{reorder_accuracy * 100:.2f}%",
                        "new_items_novelty": f"{new_items_novelty * 100:.2f}%",
                        "diversity_score": f"{diversity_score * 100:.2f}%",
                        "overall_score": f"{overall_score:.2f}%",
                        "past_orders_count": len(past_orders),
                        "unique_items_ordered": len(ordered_item_ids)
                    }
                    
                    return evaluation
                else:
                    error_text = await resp.text()
                    print(f"❌ Failed to get recommendations: {resp.status} - {error_text[:200]}")
                    return {}
                    
    except Exception as e:
        print(f"❌ Error evaluating recommendations: {e}")
        import traceback
        traceback.print_exc()
        return {}


async def get_matrix_status():
    """Get Matrix Factorization model status"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{BASE_URL}/api/admin/build-matrix",
                timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"  ✅ Matrix Status: {data.get('message')}")
                    print(f"     Users: {data.get('users', 0)}, Items: {data.get('items', 0)}")
                    return data
                else:
                    error_text = await resp.text()
                    print(f"  ❌ Matrix build failed: {resp.status} - {error_text[:200]}")
                    return {"error": f"HTTP {resp.status}"}
    except Exception as e:
        print(f"  ❌ Error building matrix: {e}")
        return {"error": str(e)}


async def run_all_tests():
    """Run all tests with better error handling and logging"""
    
    print("\n" + "="*80)
    print("VOICE GUIDE - COMPREHENSIVE TESTING SUITE")
    print("="*80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Check existing data
    print("\n📊 STEP 0: Checking Existing Data")
    existing_orders = await check_existing_orders(db)
    results["existing_orders"] = existing_orders
    
    # Step 1: Create test users and orders
    print("\n📊 STEP 1: Creating Test Data")
    created_orders = await create_test_users_and_orders(db)
    results["order_tests"] = {
        "total_orders_created": len(created_orders),
        "sample_orders": [
            {
                "id": o.get("id"),
                "user_id": o.get("user_id"),
                "restaurant_id": o.get("restaurant_id"),
                "items_count": len(o.get("items", [])),
                "total": o.get("pricing", {}).get("total", 0)
            } for o in created_orders[:3]
        ]
    }
    
    # Step 2: Rebuild matrix
    print("\n📊 STEP 2: Rebuilding Matrix")
    matrix_status = await get_matrix_status()
    results["matrix_evaluation"]["rebuild_status"] = matrix_status
    
    # Wait for matrix to build
    print("\n⏳ Waiting 15 seconds for matrix to build...")
    await asyncio.sleep(15)
    
    # Step 3: Test Chatbot
    print("\n📊 STEP 3: Testing Chatbot")
    
    # Register a test user
    test_user = {
        "username": f"chatbot_tester_{datetime.now().timestamp()}",
        "email": f"chatbot_test_{datetime.now().timestamp()}@test.com",
        "password": "test123"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{BASE_URL}/api/auth/register", 
                json=test_user,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    user_data = await resp.json()
                    token = user_data["access_token"]
                    
                    print(f"✅ Registered chatbot test user")
                    
                    # Run chatbot tests
                    chatbot_results = []
                    for i, test_case in enumerate(CHATBOT_TEST_CASES):
                        print(f"  Testing {i+1}/{len(CHATBOT_TEST_CASES)}: {test_case['prompt'][:40]}...")
                        result = await test_chatbot(session, token, test_case)
                        chatbot_results.append(result)
                        await asyncio.sleep(1)  # Rate limit
                    
                    results["chatbot_tests"] = chatbot_results
                    
                    # Calculate accuracy
                    successful = sum(1 for r in chatbot_results if r.get("success", False))
                    accuracy = (successful / len(chatbot_results)) * 100 if chatbot_results else 0
                    results["chatbot_tests_summary"] = {
                        "total_tests": len(chatbot_results),
                        "successful": successful,
                        "failed": len(chatbot_results) - successful,
                        "accuracy": f"{accuracy:.2f}%"
                    }
                    
                    print(f"\n  ✅ Chatbot Accuracy: {accuracy:.2f}%")
                    
                    # Step 4: Evaluate Recommendations
                    print("\n📊 STEP 4: Evaluating Recommendations")
                    recommendation_eval = await evaluate_recommendations(db, token)
                    results["recommendation_tests"] = recommendation_eval
                    
                    if recommendation_eval:
                        print(f"  ✅ Recommendation Score: {recommendation_eval.get('overall_score', 'N/A')}")
                else:
                    error_text = await resp.text()
                    print(f"❌ Failed to register chatbot test user: {error_text[:200]}")
                    results["chatbot_tests_summary"] = {"error": "Failed to register test user"}
    
    except Exception as e:
        print(f"❌ Error in chatbot testing: {e}")
        import traceback
        traceback.print_exc()
        results["chatbot_tests_summary"] = {"error": str(e)}
    
    # Save results
    print("\n📊 STEP 5: Saving Results")
    save_results_to_file(results)
    
    print("\n" + "="*80)
    print("✅ ALL TESTS COMPLETED!")
    print("="*80)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    print(f"\nResults saved to:")
    print(f"  - test_results_{timestamp}.json")
    print(f"  - test_results_{timestamp}.md")
    print("\n")
    
    client.close()


def save_results_to_file(results):
    """Save results to JSON and Markdown"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Save JSON
    json_filename = f"test_results_{timestamp}.json"
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    
    # Save Markdown (same as before)
    md_filename = f"test_results_{timestamp}.md"
    with open(md_filename, 'w', encoding='utf-8') as f:
        f.write("# Voice Guide - Test Results Report\n\n")
        f.write(f"**Generated:** {results['timestamp']}\n\n")
        f.write("---\n\n")
        
        # Existing orders
        f.write("## 0. Existing Database State\n\n")
        existing = results.get("existing_orders", {})
        f.write(f"**Total Orders in DB:** {existing.get('total', 0)}\n")
        f.write(f"**Delivered Orders:** {existing.get('delivered', 0)}\n\n")
        
        # Rest of the markdown generation...
        # (Keep the same as your original)
        
        # Chatbot Tests
        f.write("## 1. Chatbot Testing Results\n\n")
        summary = results.get("chatbot_tests_summary", {})
        f.write(f"**Total Tests:** {summary.get('total_tests', 0)}\n")
        f.write(f"**Successful:** {summary.get('successful', 0)}\n")
        f.write(f"**Accuracy:** {summary.get('accuracy', 'N/A')}\n\n")
        
        # Order Tests
        f.write("\n## 2. Order Creation Results\n\n")
        order_data = results.get("order_tests", {})
        f.write(f"**New Orders Created:** {order_data.get('total_orders_created', 0)}\n\n")
        
        # Recommendations
        f.write("\n## 3. Recommendation Evaluation\n\n")
        rec_eval = results.get("recommendation_tests", {})
        if isinstance(rec_eval, dict) and rec_eval:
            f.write(f"**Overall Score:** {rec_eval.get('overall_score', 'N/A')}\n")
            f.write(f"**Reorder Accuracy:** {rec_eval.get('reorder_accuracy', 'N/A')}\n")
            f.write(f"**New Items Novelty:** {rec_eval.get('new_items_novelty', 'N/A')}\n")
            f.write(f"**Diversity:** {rec_eval.get('diversity_score', 'N/A')}\n")
        else:
            f.write("**No evaluation data available**\n")


if __name__ == "__main__":
    asyncio.run(run_all_tests())