"""
Comprehensive Testing Suite for Voice Guide
- Chatbot Testing (English & Urdu)
- Order Placement for Matrix Factorization Training
- Recommendation Accuracy Evaluation
- Results saved to formatted files
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


# ============================================================================
# CHATBOT TESTING
# ============================================================================

CHATBOT_TEST_CASES = [
    # English Tests
    {"lang": "en", "prompt": "I'm hungry", "expected_intent": "food_recommendation"},
    {"lang": "en", "prompt": "Show me something to eat", "expected_intent": "food_recommendation"},
    {"lang": "en", "prompt": "I want to reorder", "expected_intent": "reorder"},
    {"lang": "en", "prompt": "Order my usual", "expected_intent": "reorder"},
    {"lang": "en", "prompt": "Show me something new", "expected_intent": "new_items"},
    {"lang": "en", "prompt": "I want to try something different", "expected_intent": "new_items"},
    {"lang": "en", "prompt": "I want biryani", "expected_intent": "specific_cuisine"},
    {"lang": "en", "prompt": "Show me burgers", "expected_intent": "specific_cuisine"},
    {"lang": "en", "prompt": "I want Chinese food", "expected_intent": "specific_cuisine"},
    {"lang": "en", "prompt": "Hello", "expected_intent": "greeting"},
    {"lang": "en", "prompt": "Hi there", "expected_intent": "greeting"},
    
    # Urdu Tests
    {"lang": "ur", "prompt": "بھوک لگی ہے", "expected_intent": "food_recommendation"},
    {"lang": "ur", "prompt": "کھانا چاہیے", "expected_intent": "food_recommendation"},
    {"lang": "ur", "prompt": "دوبارہ آرڈر کرنا ہے", "expected_intent": "reorder"},
    {"lang": "ur", "prompt": "نیا کھانا دکھاؤ", "expected_intent": "new_items"},
    {"lang": "ur", "prompt": "بریانی چاہیے", "expected_intent": "specific_cuisine"},
    {"lang": "ur", "prompt": "السلام علیکم", "expected_intent": "greeting"},
    
    # Edge Cases
    {"lang": "en", "prompt": "What's the status of my order?", "expected_intent": "order_status"},
    {"lang": "en", "prompt": "I have a complaint", "expected_intent": "complaint"},
    {"lang": "en", "prompt": "The food was cold", "expected_intent": "complaint"},
]


async def test_chatbot(session, token, test_case):
    """Test a single chatbot interaction"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "message": test_case["prompt"],
            "session_id": f"test_session_{datetime.now().timestamp()}"
        }
        
        async with session.post(f"{BASE_URL}/api/chat", json=payload, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                
                result = {
                    "prompt": test_case["prompt"],
                    "language": test_case["lang"],
                    "expected_intent": test_case["expected_intent"],
                    "detected_intent": data.get("intent", "unknown"),
                    "response": data.get("response", ""),
                    "response_language": "ur" if any(ord(c) > 127 for c in data.get("response", "")) else "en",
                    "reorder_items_count": len(data.get("reorder_items", [])),
                    "new_items_count": len(data.get("new_items", [])),
                    "success": data.get("intent") == test_case["expected_intent"],
                    "timestamp": datetime.now().isoformat()
                }
                
                return result
            else:
                return {
                    "prompt": test_case["prompt"],
                    "error": f"HTTP {resp.status}",
                    "success": False
                }
    except Exception as e:
        return {
            "prompt": test_case["prompt"],
            "error": str(e),
            "success": False
        }


# ============================================================================
# ORDER PLACEMENT FOR TRAINING
# ============================================================================

async def create_test_users_and_orders(db):
    """Create realistic test users and orders for Matrix Factorization training"""
    
    print("\n" + "="*80)
    print("CREATING TEST USERS AND ORDERS FOR MATRIX FACTORIZATION")
    print("="*80)
    
    # Get available menu items
    menu_items = await db.menu_items.find({"available": True}, {"_id": 0}).to_list(None)
    restaurants = await db.restaurants.find({"is_active": True}, {"_id": 0}).to_list(None)
    
    if not menu_items or not restaurants:
        print("❌ No menu items or restaurants found!")
        return []
    
    # Create test users with different preferences
    test_users = [
        {"username": f"test_user_{i}", "email": f"test{i}@test.com", "password": "test123",
         "favorite_cuisines": random.sample(["Pakistani", "Chinese", "Fast Food", "BBQ", "Desserts"], 2),
         "dietary_restrictions": random.choice([[], ["vegetarian"], ["vegan"], ["halal"]]),
         "spice_preference": random.choice(["mild", "medium", "hot"])}
        for i in range(10)
    ]
    
    created_orders = []
    
    for user_data in test_users:
        try:
            # Register user
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{BASE_URL}/api/auth/register", json=user_data) as resp:
                    if resp.status == 200:
                        user_info = await resp.json()
                        token = user_info["access_token"]
                        user_id = user_info["user"]["id"]
                        
                        print(f"✅ Created user: {user_data['username']}")
                        
                        # Place 3-7 orders for this user
                        num_orders = random.randint(3, 7)
                        for order_num in range(num_orders):
                            # Select 1-3 random items
                            selected_items = random.sample(menu_items, random.randint(1, 3))
                            
                            order_items = []
                            total_amount = 0
                            
                            for item in selected_items:
                                quantity = random.randint(1, 2)
                                price = item["price"] * quantity
                                total_amount += price
                                
                                order_items.append({
                                    "menu_item_id": item["id"],
                                    "name": item["name"],
                                    "quantity": quantity,
                                    "price": item["price"],
                                    "special_instructions": ""
                                })
                            
                            # Create order directly in DB (simulating completed order)
                            order_doc = {
                                "id": f"order_{user_id}_{order_num}_{datetime.now().timestamp()}",
                                "user_id": user_id,
                                "restaurant_id": selected_items[0]["restaurant_id"],
                                "items": order_items,
                                "total_amount": total_amount,
                                "delivery_fee": 50,
                                "order_status": "Delivered",  # Important for Matrix Factorization!
                                "payment_status": "Paid",
                                "delivery_address": {"address": "Test Address", "lat": 24.8607, "lng": 67.0011},
                                "created_at": datetime.now(),
                                "updated_at": datetime.now()
                            }
                            
                            await db.orders.insert_one(order_doc)
                            created_orders.append(order_doc)
                        
                        print(f"  📦 Created {num_orders} orders for {user_data['username']}")
                    
        except Exception as e:
            print(f"❌ Error creating user {user_data['username']}: {e}")
    
    print(f"\n✅ Total orders created: {len(created_orders)}")
    return created_orders


# ============================================================================
# RECOMMENDATION EVALUATION
# ============================================================================

async def evaluate_recommendations(db, token):
    """Evaluate recommendation accuracy"""
    
    print("\n" + "="*80)
    print("EVALUATING RECOMMENDATION SYSTEM")
    print("="*80)
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        async with aiohttp.ClientSession() as session:
            # Get recommendations
            async with session.get(f"{BASE_URL}/api/recommendations?limit=10", headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    recommendations = data.get("recommendations", [])
                    reorder_items = data.get("reorder_items", [])
                    new_items = data.get("new_items", [])
                    
                    # Get user's order history
                    user_info = await get_user_profile(session, token)
                    user_id = user_info["id"]
                    
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
                    reorder_accuracy = len([r for r in reorder_items if r["id"] in ordered_item_ids]) / max(len(reorder_items), 1)
                    new_items_novelty = len([n for n in new_items if n["id"] not in ordered_item_ids]) / max(len(new_items), 1)
                    
                    # Diversity (how many different restaurants)
                    unique_restaurants = len(set(r.get("restaurant_id") for r in recommendations))
                    diversity_score = unique_restaurants / max(total_recommendations, 1)
                    
                    # Check dietary restrictions compliance
                    user_restrictions = user_info.get("dietary_restrictions", [])
                    compliant = True
                    for rec in recommendations:
                        if "vegetarian" in user_restrictions and not rec.get("is_vegetarian", False):
                            compliant = False
                            break
                        if "vegan" in user_restrictions and not rec.get("is_vegan", False):
                            compliant = False
                            break
                    
                    dietary_compliance = 1.0 if compliant else 0.0
                    
                    # Overall score
                    overall_score = (
                        reorder_accuracy * 0.3 +
                        new_items_novelty * 0.3 +
                        diversity_score * 0.2 +
                        dietary_compliance * 0.2
                    ) * 100
                    
                    evaluation = {
                        "total_recommendations": total_recommendations,
                        "reorder_items_count": len(reorder_items),
                        "new_items_count": len(new_items),
                        "reorder_accuracy": f"{reorder_accuracy * 100:.2f}%",
                        "new_items_novelty": f"{new_items_novelty * 100:.2f}%",
                        "diversity_score": f"{diversity_score * 100:.2f}%",
                        "dietary_compliance": f"{dietary_compliance * 100:.2f}%",
                        "overall_score": f"{overall_score:.2f}%",
                        "past_orders_count": len(past_orders),
                        "unique_items_ordered": len(ordered_item_ids)
                    }
                    
                    return evaluation
                    
    except Exception as e:
        print(f"❌ Error evaluating recommendations: {e}")
        import traceback
        traceback.print_exc()
        return {}


async def get_user_profile(session, token):
    """Get user profile"""
    headers = {"Authorization": f"Bearer {token}"}
    async with session.get(f"{BASE_URL}/api/user/profile", headers=headers) as resp:
        return await resp.json()


# ============================================================================
# MATRIX FACTORIZATION STATUS
# ============================================================================

async def get_matrix_status():
    """Get Matrix Factorization model status"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{BASE_URL}/api/admin/build-matrix") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data
                else:
                    return {"error": f"HTTP {resp.status}"}
    except Exception as e:
        return {"error": str(e)}


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

async def run_all_tests():
    """Run all tests and generate report"""
    
    print("\n" + "="*80)
    print("VOICE GUIDE - COMPREHENSIVE TESTING SUITE")
    print("="*80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Step 1: Create test users and orders
    print("\n📊 STEP 1: Creating Test Data for Matrix Factorization")
    created_orders = await create_test_users_and_orders(db)
    results["order_tests"] = {
        "total_orders_created": len(created_orders),
        "orders": created_orders[:5]  # Save first 5 as examples
    }
    
    # Step 2: Rebuild matrix with new data
    print("\n📊 STEP 2: Rebuilding Matrix Factorization Model")
    matrix_status = await get_matrix_status()
    results["matrix_evaluation"]["rebuild_status"] = matrix_status
    print(f"Matrix Status: {matrix_status}")
    
    # Wait for matrix to build
    print("Waiting 15 seconds for matrix to build...")
    await asyncio.sleep(15)
    
    # Step 3: Test Chatbot
    print("\n📊 STEP 3: Testing Chatbot (English & Urdu)")
    
    # Register a test user for chatbot testing
    test_user = {
        "username": f"chatbot_tester_{datetime.now().timestamp()}",
        "email": f"chatbot_test@test.com",
        "password": "test123"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BASE_URL}/api/auth/register", json=test_user) as resp:
            if resp.status == 200:
                user_data = await resp.json()
                token = user_data["access_token"]
                
                # Run chatbot tests
                chatbot_results = []
                for i, test_case in enumerate(CHATBOT_TEST_CASES):
                    print(f"  Testing {i+1}/{len(CHATBOT_TEST_CASES)}: {test_case['prompt'][:50]}...")
                    result = await test_chatbot(session, token, test_case)
                    chatbot_results.append(result)
                    await asyncio.sleep(0.5)  # Rate limit
                
                results["chatbot_tests"] = chatbot_results
                
                # Chatbot accuracy
                successful = sum(1 for r in chatbot_results if r.get("success", False))
                accuracy = (successful / len(chatbot_results)) * 100
                results["chatbot_tests_summary"] = {
                    "total_tests": len(chatbot_results),
                    "successful": successful,
                    "failed": len(chatbot_results) - successful,
                    "accuracy": f"{accuracy:.2f}%"
                }
                
                print(f"\n  Chatbot Accuracy: {accuracy:.2f}%")
                
                # Step 4: Evaluate Recommendations
                print("\n📊 STEP 4: Evaluating Recommendation System")
                recommendation_eval = await evaluate_recommendations(db, token)
                results["recommendation_tests"] = recommendation_eval
                
                print(f"\n  Recommendation Score: {recommendation_eval.get('overall_score', 'N/A')}")
    
    # Save results
    print("\n📊 STEP 5: Saving Results")
    save_results_to_file(results)
    
    print("\n" + "="*80)
    print("✅ ALL TESTS COMPLETED!")
    print("="*80)
    print(f"\nResults saved to:")
    print(f"  - test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    print(f"  - test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
    print("\n")
    
    client.close()


def save_results_to_file(results):
    """Save results to JSON and formatted Markdown"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Save JSON
    json_filename = f"test_results_{timestamp}.json"
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Save Markdown
    md_filename = f"test_results_{timestamp}.md"
    with open(md_filename, 'w', encoding='utf-8') as f:
        f.write("# Voice Guide - Test Results Report\n\n")
        f.write(f"**Generated:** {results['timestamp']}\n\n")
        f.write("---\n\n")
        
        # Chatbot Tests
        f.write("## 1. Chatbot Testing Results\n\n")
        summary = results.get("chatbot_tests_summary", {})
        f.write(f"**Total Tests:** {summary.get('total_tests', 0)}\n")
        f.write(f"**Successful:** {summary.get('successful', 0)}\n")
        f.write(f"**Failed:** {summary.get('failed', 0)}\n")
        f.write(f"**Accuracy:** {summary.get('accuracy', 'N/A')}\n\n")
        
        f.write("### Test Cases:\n\n")
        f.write("| Prompt | Language | Expected | Detected | Success | Response |\n")
        f.write("|--------|----------|----------|----------|---------|----------|\n")
        
        for test in results.get("chatbot_tests", []):
            prompt = test.get("prompt", "")[:30]
            lang = test.get("language", "")
            expected = test.get("expected_intent", "")
            detected = test.get("detected_intent", "")
            success = "✅" if test.get("success") else "❌"
            response = test.get("response", "")[:50]
            f.write(f"| {prompt} | {lang} | {expected} | {detected} | {success} | {response} |\n")
        
        # Order Tests
        f.write("\n## 2. Order Placement Results\n\n")
        order_data = results.get("order_tests", {})
        f.write(f"**Total Orders Created:** {order_data.get('total_orders_created', 0)}\n\n")
        
        # Recommendation Tests
        f.write("\n## 3. Recommendation System Evaluation\n\n")
        rec_eval = results.get("recommendation_tests", {})
        f.write(f"**Overall Score:** {rec_eval.get('overall_score', 'N/A')}\n\n")
        f.write("### Metrics:\n\n")
        f.write(f"- **Reorder Accuracy:** {rec_eval.get('reorder_accuracy', 'N/A')}\n")
        f.write(f"- **New Items Novelty:** {rec_eval.get('new_items_novelty', 'N/A')}\n")
        f.write(f"- **Diversity Score:** {rec_eval.get('diversity_score', 'N/A')}\n")
        f.write(f"- **Dietary Compliance:** {rec_eval.get('dietary_compliance', 'N/A')}\n")
        f.write(f"- **Total Recommendations:** {rec_eval.get('total_recommendations', 0)}\n")
        f.write(f"- **Past Orders:** {rec_eval.get('past_orders_count', 0)}\n\n")
        
        # Matrix Status
        f.write("\n## 4. Matrix Factorization Status\n\n")
        matrix_data = results.get("matrix_evaluation", {}).get("rebuild_status", {})
        if "users" in matrix_data:
            f.write(f"**Users in Matrix:** {matrix_data.get('users', 0)}\n")
            f.write(f"**Items in Matrix:** {matrix_data.get('items', 0)}\n")
            f.write(f"**Status:** {matrix_data.get('status', 'unknown')}\n")
        
        f.write("\n---\n\n")
        f.write("## For FYP Presentation\n\n")
        f.write("### Key Metrics:\n\n")
        f.write(f"1. **Chatbot Intent Detection Accuracy:** {summary.get('accuracy', 'N/A')}\n")
        f.write(f"2. **Recommendation Overall Score:** {rec_eval.get('overall_score', 'N/A')}\n")
        f.write(f"3. **Bilingual Support:** Tested in English & Urdu ✅\n")
        f.write(f"4. **Matrix Factorization:** Trained on {order_data.get('total_orders_created', 0)} orders\n")
        f.write(f"5. **Dietary Compliance:** {rec_eval.get('dietary_compliance', 'N/A')}\n\n")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
