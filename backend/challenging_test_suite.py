"""
CHALLENGING Test Suite - Designed to Test Edge Cases and Ambiguity
Expected Accuracy: 70-85%
"""

import asyncio
import aiohttp
import json
from datetime import datetime
import random

BASE_URL = "http://localhost:8001"

# CHALLENGING test cases - designed to test ambiguity and edge cases
CHALLENGING_TEST_CASES = [
    # ========== AMBIGUOUS QUERIES (should be tricky) ==========
    {
        "prompt": "Something good",
        "expected": "food_recommendation",
        "should_have_items": True,
        "difficulty": "hard",
        "note": "Very vague - could mean anything"
    },
    {
        "prompt": "What do you have?",
        "expected": "food_recommendation",
        "should_have_items": True,
        "difficulty": "medium",
        "note": "General question"
    },
    {
        "prompt": "Surprise me",
        "expected": "new_items",
        "should_have_items": True,
        "difficulty": "hard",
        "note": "No specific intent"
    },
    
    # ========== MIXED LANGUAGE (Roman Urdu + English) ==========
    {
        "prompt": "Kuch spicy food dikhao",
        "expected": "food_recommendation",
        "should_have_items": True,
        "difficulty": "medium",
        "note": "Mixed Urdu-English"
    },
    {
        "prompt": "Burger hai kya tasty wala?",
        "expected": "specific_item_search",
        "should_have_items": True,
        "difficulty": "medium",
        "note": "Roman Urdu + English item"
    },
    {
        "prompt": "Bhook lag rahi hai, fast food chahiye",
        "expected": "specific_cuisine",
        "should_have_items": True,
        "difficulty": "medium",
        "note": "Mixed language with cuisine"
    },
    
    # ========== SIMILAR SOUNDING INTENTS ==========
    {
        "prompt": "Order again",
        "expected": "reorder",
        "should_have_items": True,
        "difficulty": "easy",
        "note": "Reorder synonym"
    },
    {
        "prompt": "Get me what I had last time",
        "expected": "reorder",
        "should_have_items": True,
        "difficulty": "medium",
        "note": "Indirect reorder"
    },
    {
        "prompt": "Different stuff",
        "expected": "new_items",
        "should_have_items": True,
        "difficulty": "hard",
        "note": "Very casual phrasing"
    },
    
    # ========== CONFUSING / CONTRADICTORY ==========
    {
        "prompt": "I want biryani but not rice",
        "expected": "specific_item_search",
        "should_have_items": False,  # Should fail or return nothing
        "difficulty": "hard",
        "note": "Contradictory request"
    },
    {
        "prompt": "Show me pizza without cheese",
        "expected": "specific_item_search",
        "should_have_items": True,  # Might find something
        "difficulty": "hard",
        "note": "Unusual requirement"
    },
    {
        "prompt": "Healthy junk food",
        "expected": "food_recommendation",
        "should_have_items": True,
        "difficulty": "hard",
        "note": "Oxymoron"
    },
    
    # ========== VERY LONG QUERIES ==========
    {
        "prompt": "I'm really hungry and I want something spicy but not too spicy maybe medium spicy with chicken or beef and rice would be nice but pasta is also okay I guess",
        "expected": "food_recommendation",
        "should_have_items": True,
        "difficulty": "hard",
        "note": "Run-on sentence with multiple requests"
    },
    {
        "prompt": "Can you please show me some good food that I can order right now because I'm very hungry and I don't know what to eat maybe something new that I haven't tried before",
        "expected": "new_items",
        "should_have_items": True,
        "difficulty": "hard",
        "note": "Long rambling query"
    },
    
    # ========== TYPOS AND MISSPELLINGS ==========
    {
        "prompt": "I wnt bryani",
        "expected": "specific_cuisine",
        "should_have_items": True,
        "difficulty": "medium",
        "note": "Multiple typos"
    },
    {
        "prompt": "Show me burgers pls",
        "expected": "specific_cuisine",
        "should_have_items": True,
        "difficulty": "easy",
        "note": "Common abbreviation"
    },
    {
        "prompt": "gimme smthing gud",
        "expected": "food_recommendation",
        "should_have_items": True,
        "difficulty": "medium",
        "note": "SMS-style typing"
    },
    
    # ========== CONTEXT-DEPENDENT (needs history) ==========
    {
        "prompt": "More of that",
        "expected": "reorder",
        "should_have_items": True,  # Only if has history
        "difficulty": "hard",
        "note": "Requires conversation context"
    },
    {
        "prompt": "Add more",
        "expected": "reorder",
        "should_have_items": True,
        "difficulty": "hard",
        "note": "Assumes previous selection"
    },
    
    # ========== NEGATIONS (tricky) ==========
    {
        "prompt": "I don't want biryani",
        "expected": "food_recommendation",
        "should_have_items": True,
        "difficulty": "hard",
        "note": "Negative preference"
    },
    {
        "prompt": "Not spicy please",
        "expected": "food_recommendation",
        "should_have_items": True,
        "difficulty": "medium",
        "note": "Negative requirement"
    },
    {
        "prompt": "Anything but pizza",
        "expected": "food_recommendation",
        "should_have_items": True,
        "difficulty": "hard",
        "note": "Exclusion request"
    },
    
    # ========== BASIC (should still work) ==========
    {
        "prompt": "I'm hungry",
        "expected": "food_recommendation",
        "should_have_items": True,
        "difficulty": "easy",
        "note": "Clear intent"
    },
    {
        "prompt": "Show me biryani",
        "expected": "specific_cuisine",
        "should_have_items": True,
        "difficulty": "easy",
        "note": "Direct request"
    },
    {
        "prompt": "Reorder",
        "expected": "reorder",
        "should_have_items": True,
        "difficulty": "easy",
        "note": "One word command"
    },
]

# CONFLICT TEST CASES - should trigger confirmation prompts
CONFLICT_TEST_CASES = [
    {
        "setup": {
            "favorite_cuisines": ["Desserts", "Fast Food"],
            "dietary_restrictions": ["Vegetarian"],
            "spice_preference": "mild"
        },
        "prompt": "I want something very spicy with meat",
        "expected_conflicts": ["spice", "dietary"],
        "should_ask_confirmation": True,
        "note": "Conflicts with both spice and dietary preferences"
    },
    {
        "setup": {
            "favorite_cuisines": ["Pakistani"],
            "dietary_restrictions": ["Vegan"],
            "spice_preference": "medium"
        },
        "prompt": "Show me chicken biryani",
        "expected_conflicts": ["dietary"],
        "should_ask_confirmation": True,
        "note": "Conflicts with vegan restriction"
    },
    {
        "setup": {
            "favorite_cuisines": ["Chinese", "Thai"],
            "dietary_restrictions": [],
            "spice_preference": "hot"
        },
        "prompt": "I want Pakistani food that's not spicy",
        "expected_conflicts": ["cuisine", "spice"],
        "should_ask_confirmation": True,
        "note": "Different cuisine + opposite spice level"
    },
    {
        "setup": {
            "favorite_cuisines": ["Desserts"],
            "dietary_restrictions": ["Halal"],
            "spice_preference": "mild"
        },
        "prompt": "Show me BBQ tikka extra spicy",
        "expected_conflicts": ["cuisine", "spice"],
        "should_ask_confirmation": True,
        "note": "Different category + high spice"
    },
]


async def test_challenging_intents(session, token):
    """Test with challenging and ambiguous queries"""
    
    print("\n" + "="*80)
    print("CHALLENGING INTENT DETECTION TEST")
    print("="*80)
    print("Testing with ambiguous queries, typos, and edge cases")
    print("Expected Accuracy: 70-85% (realistic)")
    print("="*80)
    
    results = []
    correct = 0
    total = len(CHALLENGING_TEST_CASES)
    
    # Group by difficulty
    easy_correct = 0
    easy_total = 0
    medium_correct = 0
    medium_total = 0
    hard_correct = 0
    hard_total = 0
    
    for i, test_case in enumerate(CHALLENGING_TEST_CASES, 1):
        try:
            headers = {"Authorization": f"Bearer {token}"}
            payload = {
                "message": test_case["prompt"],
                "user_id": "test",
                "session_id": f"test_{datetime.now().timestamp()}"
            }
            
            print(f"\n{'='*80}")
            print(f"Test {i}/{total} [{test_case['difficulty'].upper()}]")
            print(f"Query: \"{test_case['prompt']}\"")
            print(f"Note: {test_case['note']}")
            print(f"Expected: {test_case['expected']}")
            
            async with session.post(f"{BASE_URL}/api/chat", json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    intent = data.get("intent", "unknown")
                    has_items = len(data.get("recommended_items", [])) > 0
                    
                    # More flexible matching for hard cases
                    match = False
                    if intent == test_case["expected"]:
                        match = True
                    elif test_case["difficulty"] == "hard":
                        # Allow some leniency for hard cases
                        if test_case["expected"] == "food_recommendation" and intent in ["specific_cuisine", "new_items"]:
                            match = True
                        elif test_case["expected"] == "new_items" and intent == "food_recommendation":
                            match = True
                    
                    items_match = has_items == test_case["should_have_items"]
                    
                    if match and items_match:
                        correct += 1
                        status = "✅ PASS"
                        
                        # Count by difficulty
                        if test_case["difficulty"] == "easy":
                            easy_correct += 1
                        elif test_case["difficulty"] == "medium":
                            medium_correct += 1
                        else:
                            hard_correct += 1
                    else:
                        status = "❌ FAIL"
                    
                    # Count total by difficulty
                    if test_case["difficulty"] == "easy":
                        easy_total += 1
                    elif test_case["difficulty"] == "medium":
                        medium_total += 1
                    else:
                        hard_total += 1
                    
                    print(f"Result: {status}")
                    print(f"Got Intent: {intent}, Has Items: {has_items}")
                    print(f"Response Preview: {data.get('response', '')[:100]}...")
                    
                    results.append({
                        "prompt": test_case["prompt"],
                        "difficulty": test_case["difficulty"],
                        "expected": test_case["expected"],
                        "detected": intent,
                        "correct": match and items_match,
                        "has_items": has_items,
                        "note": test_case["note"]
                    })
                else:
                    print(f"Result: ❌ FAIL - HTTP {resp.status}")
                    results.append({"prompt": test_case["prompt"], "error": resp.status})
            
            await asyncio.sleep(0.5)
            
        except Exception as e:
            print(f"Result: ❌ ERROR - {str(e)[:100]}")
            results.append({"prompt": test_case["prompt"], "error": str(e)})
    
    # Calculate statistics
    overall_accuracy = (correct / total * 100) if total > 0 else 0
    easy_accuracy = (easy_correct / easy_total * 100) if easy_total > 0 else 0
    medium_accuracy = (medium_correct / medium_total * 100) if medium_total > 0 else 0
    hard_accuracy = (hard_correct / hard_total * 100) if hard_total > 0 else 0
    
    print(f"\n{'='*80}")
    print(f"CHALLENGING TEST RESULTS")
    print(f"{'='*80}")
    print(f"Overall Accuracy: {overall_accuracy:.2f}% ({correct}/{total})")
    print(f"\nBy Difficulty:")
    print(f"  Easy:   {easy_accuracy:.2f}% ({easy_correct}/{easy_total})")
    print(f"  Medium: {medium_accuracy:.2f}% ({medium_correct}/{medium_total})")
    print(f"  Hard:   {hard_accuracy:.2f}% ({hard_correct}/{hard_total})")
    print(f"{'='*80}")
    
    return overall_accuracy, results


async def test_preference_conflicts(session, token):
    """Test conflict detection and confirmation prompts"""
    
    print("\n" + "="*80)
    print("TESTING PREFERENCE CONFLICT DETECTION")
    print("="*80)
    print("Testing when user's query conflicts with their saved preferences")
    print("="*80)
    
    results = []
    detected = 0
    total = len(CONFLICT_TEST_CASES)
    
    for i, test_case in enumerate(CONFLICT_TEST_CASES, 1):
        try:
            print(f"\n{'='*80}")
            print(f"Conflict Test {i}/{total}")
            print(f"User Preferences: {test_case['setup']}")
            print(f"Query: \"{test_case['prompt']}\"")
            print(f"Expected Conflicts: {test_case['expected_conflicts']}")
            print(f"Note: {test_case['note']}")
            
            headers = {"Authorization": f"Bearer {token}"}
            
            # FIRST: Update user preferences to match test case setup
            print("\n  Setting up user preferences...")
            async with session.put(
                f"{BASE_URL}/api/user/preferences",
                json=test_case['setup'],
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    print("  ✅ Preferences updated")
                else:
                    print(f"  ⚠️ Failed to update preferences: {resp.status}")
            
            await asyncio.sleep(0.5)
            
            # NOW: Send the conflicting query
            payload = {
                "message": test_case["prompt"],
                "user_id": "test",
                "session_id": f"conflict_test_{i}"
            }
            
            async with session.post(f"{BASE_URL}/api/chat", json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    overrides = data.get("query_overrides", {})
                    conflicts = data.get("preference_conflicts", {})
                    response = data.get("response", "")
                    
                    print(f"\n  Overrides Detected: {overrides}")
                    print(f"  Conflicts Detected: {conflicts}")
                    
                    # Check if conflicts were detected
                    has_conflict = conflicts.get("has_conflict", False)
                    conflict_types = [c["type"] for c in conflicts.get("conflicts", [])]
                    
                    # Check if expected conflicts were detected
                    expected_detected = all(exp in conflict_types for exp in test_case["expected_conflicts"])
                    
                    # Check if response asks for confirmation
                    confirmation_keywords = [
                        "usually prefer", "typically like", "your preference",
                        "want to override", "sure about", "confirm",
                        "different from", "you're", "but you", "however you"
                    ]
                    asks_confirmation = any(keyword.lower() in response.lower() for keyword in confirmation_keywords)
                    
                    if expected_detected or (has_conflict and asks_confirmation):
                        detected += 1
                        status = "✅ PASS"
                    else:
                        status = "❌ FAIL"
                    
                    print(f"\n  Result: {status}")
                    print(f"  Conflict Detected: {has_conflict}")
                    print(f"  Expected Conflicts: {test_case['expected_conflicts']}")
                    print(f"  Detected Conflicts: {conflict_types}")
                    print(f"  Asks Confirmation: {asks_confirmation}")
                    print(f"  Response Preview: {response[:150]}...")
                    
                    results.append({
                        "prompt": test_case["prompt"],
                        "setup": test_case["setup"],
                        "expected_conflicts": test_case["expected_conflicts"],
                        "detected_conflicts": conflict_types,
                        "has_conflict": has_conflict,
                        "asks_confirmation": asks_confirmation,
                        "passed": expected_detected or (has_conflict and asks_confirmation)
                    })
                else:
                    print(f"  Result: ❌ FAIL - HTTP {resp.status}")
                    results.append({"prompt": test_case["prompt"], "error": resp.status})
            
            await asyncio.sleep(1)
            
        except Exception as e:
            print(f"  Result: ❌ ERROR - {str(e)[:100]}")
            results.append({"prompt": test_case["prompt"], "error": str(e)})
    
    detection_rate = (detected / total * 100) if total > 0 else 0
    
    print(f"\n{'='*80}")
    print(f"CONFLICT DETECTION RESULTS")
    print(f"{'='*80}")
    print(f"Detection Rate: {detection_rate:.2f}% ({detected}/{total})")
    print(f"{'='*80}")
    
    return detection_rate, results


async def run_comprehensive_tests():
    """Run all comprehensive tests"""
    
    print("\n" + "="*80)
    print("COMPREHENSIVE CHALLENGING TEST SUITE")
    print("="*80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Register test user
    test_user = {
        "username": f"challenge_tester_{datetime.now().timestamp()}",
        "email": f"challenge_test_{datetime.now().timestamp()}@test.com",
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
        
        # Test 1: Challenging Intent Detection
        intent_accuracy, intent_results = await test_challenging_intents(session, token)
        
        # Test 2: Preference Conflicts
        conflict_detection, conflict_results = await test_preference_conflicts(session, token)
        
        # Calculate overall score
        overall_score = (intent_accuracy * 0.7 + conflict_detection * 0.3)
        
        # Save results
        final_results = {
            "timestamp": datetime.now().isoformat(),
            "challenging_intent_detection": {
                "accuracy": f"{intent_accuracy:.2f}%",
                "results": intent_results
            },
            "conflict_detection": {
                "detection_rate": f"{conflict_detection:.2f}%",
                "results": conflict_results
            },
            "overall_score": f"{overall_score:.2f}%"
        }
        
        # Save to file
        filename = f"comprehensive_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(final_results, f, indent=2, ensure_ascii=False, default=str)
        
        # Summary
        print(f"\n{'='*80}")
        print(f"FINAL COMPREHENSIVE RESULTS")
        print(f"{'='*80}")
        print(f"Challenging Intent Detection: {intent_accuracy:.2f}%")
        print(f"Conflict Detection: {conflict_detection:.2f}%")
        print(f"Overall Score: {overall_score:.2f}%")
        print(f"\nResults saved to: {filename}")
        print(f"{'='*80}\n")
        
        # Realistic grading
        if overall_score >= 75:
            print("🎉 EXCELLENT! System handling edge cases well!")
        elif overall_score >= 65:
            print("✅ GOOD! Acceptable performance with room for improvement.")
        elif overall_score >= 55:
            print("⚠️ FAIR. Needs optimization for edge cases.")
        else:
            print("❌ NEEDS IMPROVEMENT. Review failing test cases.")


if __name__ == "__main__":
    asyncio.run(run_comprehensive_tests())