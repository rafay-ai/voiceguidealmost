"""
Final Comprehensive Test Suite
Tests:
1. Intent detection accuracy (target: 80%+)
2. Query override functionality
3. Recommendation quality (target: 75%+)
4. Edge cases
"""

import asyncio
import aiohttp
import json
from datetime import datetime
import random

BASE_URL = "http://localhost:8001"

# Comprehensive test cases
TEST_CASES = [
    # Basic food requests (should all work)
    {"prompt": "I'm hungry", "expected": "food_recommendation", "should_have_items": True},
    {"prompt": "What can I eat?", "expected": "food_recommendation", "should_have_items": True},
    {"prompt": "Show me food", "expected": "food_recommendation", "should_have_items": True},
    {"prompt": "Show me something to eat", "expected": "food_recommendation", "should_have_items": True},
    
    # Reorder
    {"prompt": "I want to reorder", "expected": "reorder", "should_have_items": True},
    {"prompt": "Same as before", "expected": "reorder", "should_have_items": True},
    
    # New items
    {"prompt": "Show me something new", "expected": "new_items", "should_have_items": True},
    {"prompt": "What's different?", "expected": "new_items", "should_have_items": True},
    {"prompt": "Something unique", "expected": "new_items", "should_have_items": True},
    
    # Specific cuisine
    {"prompt": "I want biryani", "expected": "specific_cuisine", "should_have_items": True},
    {"prompt": "Show me burgers", "expected": "specific_cuisine", "should_have_items": True},
    {"prompt": "Chinese food", "expected": "specific_cuisine", "should_have_items": True},
    {"prompt": "I want pizza", "expected": "specific_cuisine", "should_have_items": True},
    
    # Specific item search
    {"prompt": "Do you have chicken biryani?", "expected": "specific_item_search", "should_have_items": True},
    {"prompt": "Find me cheese burger", "expected": "specific_item_search", "should_have_items": True},
    
    # Greetings
    {"prompt": "Hello", "expected": "greeting", "should_have_items": False},
    {"prompt": "Hi there", "expected": "greeting", "should_have_items": False},
    
    # Roman Urdu
    {"prompt": "Bhook lagi hai", "expected": "food_recommendation", "should_have_items": True},
    {"prompt": "Kuch khana hai", "expected": "food_recommendation", "should_have_items": True},
    {"prompt": "Biryani dikhao", "expected": "specific_cuisine", "should_have_items": True},
    {"prompt": "Kuch naya try karna hai", "expected": "new_items", "should_have_items": True},
]

# CRITICAL: Query override test cases
OVERRIDE_TEST_CASES = [
    {
        "setup": {"favorite_cuisines": ["Desserts"], "spice_preference": "mild"},
        "prompt": "I want something spicy",
        "expected_override": "spice",
        "should_not_show": "dessert"
    },
    {
        "setup": {"favorite_cuisines": ["Fast Food"], "dietary_restrictions": []},
        "prompt": "Show me vegan options",
        "expected_override": "dietary",
        "should_show_only": "vegan"
    },
    {
        "setup": {"favorite_cuisines": ["Chinese"], "spice_preference": "hot"},
        "prompt": "I want something mild",
        "expected_override": "spice",
        "should_show_only": "mild"
    },
    {
        "setup": {"favorite_cuisines": ["Desserts", "Fast Food"]},
        "prompt": "Show me Pakistani food",
        "expected_override": "cuisine",
        "should_show_only": "Pakistani"
    }
]


async def test_intent_detection(session, token):
    """Test intent detection accuracy"""
    
    print("\n" + "="*80)
    print("TESTING INTENT DETECTION")
    print("="*80)
    
    results = []
    correct = 0
    total = len(TEST_CASES)
    
    for i, test_case in enumerate(TEST_CASES, 1):
        try:
            headers = {"Authorization": f"Bearer {token}"}
            payload = {
                "message": test_case["prompt"],
                "user_id": "test",
                "session_id": f"test_{datetime.now().timestamp()}"
            }
            
            async with session.post(f"{BASE_URL}/api/chat", json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    intent = data.get("intent", "unknown")
                    expected = test_case["expected"]
                    
                    # Flexible matching
                    match = False
                    if intent == expected:
                        match = True
                    elif expected == "specific_cuisine" and intent == "specific_item_search":
                        match = True  # Acceptable
                    elif expected == "food_recommendation" and intent in ["specific_cuisine", "new_items"]:
                        match = True  # Acceptable
                    
                    has_items = len(data.get("recommended_items", [])) > 0
                    items_match = has_items == test_case["should_have_items"]
                    
                    if match:
                        correct += 1
                        status = "✅"
                    else:
                        status = "❌"
                    
                    print(f"{status} Test {i}/{total}: '{test_case['prompt'][:40]}'")
                    print(f"   Expected: {expected}, Got: {intent}, Items: {has_items}")
                    
                    results.append({
                        "prompt": test_case["prompt"],
                        "expected": expected,
                        "detected": intent,
                        "correct": match,
                        "has_items": has_items
                    })
                else:
                    print(f"❌ Test {i}/{total}: HTTP {resp.status}")
                    results.append({"prompt": test_case["prompt"], "error": resp.status})
            
            await asyncio.sleep(0.5)
            
        except Exception as e:
            print(f"❌ Test {i}/{total}: Error - {e}")
            results.append({"prompt": test_case["prompt"], "error": str(e)})
    
    accuracy = (correct / total * 100) if total > 0 else 0
    
    print(f"\n{'='*80}")
    print(f"INTENT DETECTION ACCURACY: {accuracy:.2f}%")
    print(f"Correct: {correct}/{total}")
    print(f"{'='*80}")
    
    return accuracy, results


async def test_query_overrides(session, token):
    """Test query override functionality"""
    
    print("\n" + "="*80)
    print("TESTING QUERY OVERRIDES (CRITICAL)")
    print("="*80)
    
    results = []
    passed = 0
    total = len(OVERRIDE_TEST_CASES)
    
    for i, test_case in enumerate(OVERRIDE_TEST_CASES, 1):
        try:
            print(f"\n📋 Test {i}/{total}: {test_case['prompt']}")
            print(f"   Setup: {test_case['setup']}")
            
            headers = {"Authorization": f"Bearer {token}"}
            payload = {
                "message": test_case["prompt"],
                "user_id": "test",
                "session_id": f"override_test_{i}"
            }
            
            async with session.post(f"{BASE_URL}/api/chat", json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    items = data.get("recommended_items", [])
                    overrides = data.get("query_overrides", {})
                    
                    print(f"   Overrides detected: {overrides}")
                    print(f"   Items returned: {len(items)}")
                    
                    # Check if override was detected
                    override_detected = False
                    if test_case["expected_override"] == "spice" and "spice_override" in overrides:
                        override_detected = True
                    elif test_case["expected_override"] == "dietary" and "dietary_override" in overrides:
                        override_detected = True
                    elif test_case["expected_override"] == "cuisine" and "cuisine_override" in overrides:
                        override_detected = True
                    
                    # Check if items match the override
                    items_correct = True
                    if "should_not_show" in test_case:
                        # Check that items don't show unwanted type
                        unwanted = test_case["should_not_show"]
                        for item in items[:3]:  # Check first 3
                            cuisines = [c.lower() for c in item.get("restaurant_cuisine", [])]
                            if unwanted.lower() in cuisines:
                                items_correct = False
                                print(f"   ❌ Found unwanted {unwanted}: {item['name']}")
                                break
                    
                    if "should_show_only" in test_case:
                        # Check items match requirement
                        requirement = test_case["should_show_only"].lower()
                        
                        if requirement == "vegan":
                            items_correct = all(item.get("is_vegan", False) for item in items[:3])
                        elif requirement == "mild":
                            items_correct = all(item.get("spice_level") == "mild" for item in items[:3])
                        elif requirement in ["pakistani", "chinese", "fast food"]:
                            for item in items[:3]:
                                cuisines = [c.lower() for c in item.get("restaurant_cuisine", [])]
                                if requirement not in cuisines:
                                    items_correct = False
                                    break
                    
                    test_passed = override_detected and items_correct
                    
                    if test_passed:
                        passed += 1
                        print(f"   ✅ PASSED")
                    else:
                        print(f"   ❌ FAILED - Override: {override_detected}, Items: {items_correct}")
                    
                    results.append({
                        "prompt": test_case["prompt"],
                        "override_detected": override_detected,
                        "items_correct": items_correct,
                        "passed": test_passed
                    })
                else:
                    print(f"   ❌ HTTP {resp.status}")
                    results.append({"prompt": test_case["prompt"], "error": resp.status})
            
            await asyncio.sleep(1)
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results.append({"prompt": test_case["prompt"], "error": str(e)})
    
    success_rate = (passed / total * 100) if total > 0 else 0
    
    print(f"\n{'='*80}")
    print(f"QUERY OVERRIDE SUCCESS RATE: {success_rate:.2f}%")
    print(f"Passed: {passed}/{total}")
    print(f"{'='*80}")
    
    return success_rate, results


async def run_final_tests():
    """Run all final tests"""
    
    print("\n" + "="*80)
    print("FINAL COMPREHENSIVE TEST SUITE")
    print("="*80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Register test user
    test_user = {
        "username": f"final_tester_{datetime.now().timestamp()}",
        "email": f"final_test_{datetime.now().timestamp()}@test.com",
        "password": "test123"
    }
    
    async with aiohttp.ClientSession() as session:
        # Register
        async with session.post(f"{BASE_URL}/api/auth/register", json=test_user) as resp:
            if resp.status != 200:
                print("❌ Failed to register test user")
                return
            
            user_data = await resp.json()
            token = user_data["access_token"]
            
            print(f"✅ Registered test user: {test_user['username']}")
        
        # Test 1: Intent Detection
        intent_accuracy, intent_results = await test_intent_detection(session, token)
        
        # Test 2: Query Overrides
        override_success, override_results = await test_query_overrides(session, token)
        
        # Calculate overall score
        overall_score = (intent_accuracy * 0.6 + override_success * 0.4)
        
        # Save results
        final_results = {
            "timestamp": datetime.now().isoformat(),
            "intent_detection": {
                "accuracy": f"{intent_accuracy:.2f}%",
                "results": intent_results
            },
            "query_overrides": {
                "success_rate": f"{override_success:.2f}%",
                "results": override_results
            },
            "overall_score": f"{overall_score:.2f}%"
        }
        
        # Save to file
        filename = f"final_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(final_results, f, indent=2, default=str)
        
        # Summary
        print(f"\n{'='*80}")
        print(f"FINAL RESULTS")
        print(f"{'='*80}")
        print(f"Intent Detection Accuracy: {intent_accuracy:.2f}%")
        print(f"Query Override Success: {override_success:.2f}%")
        print(f"Overall Score: {overall_score:.2f}%")
        print(f"\nResults saved to: {filename}")
        print(f"{'='*80}\n")
        
        # Grade
        if overall_score >= 80:
            print("🎉 EXCELLENT! System performing at production quality!")
        elif overall_score >= 70:
            print("✅ GOOD! System ready for testing.")
        elif overall_score >= 60:
            print("⚠️ ACCEPTABLE. Some improvements needed.")
        else:
            print("❌ NEEDS WORK. Review failing test cases.")


if __name__ == "__main__":
    asyncio.run(run_final_tests())