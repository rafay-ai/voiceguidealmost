"""
Enhanced Chatbot with Improved Intent Detection and Query Override
Fixes:
1. Better intent detection for ambiguous queries
2. Query-based filtering that OVERRIDES user preferences
3. Handles spicy/vegan/dietary requests dynamically
4. Detects preference conflicts and asks for confirmation
"""

import os
import logging
import asyncio
from typing import Dict, List, Optional, Tuple
from enum import Enum
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)


class Intent(Enum):
    """User intent classification"""
    FOOD_RECOMMENDATION = "food_recommendation"
    REORDER = "reorder"
    NEW_ITEMS = "new_items"
    SPECIFIC_CUISINE = "specific_cuisine"
    SPECIFIC_ITEM_SEARCH = "specific_item_search"
    RESTAURANT_QUERY = "restaurant_query"
    ORDER_STATUS = "order_status"
    COMPLAINT = "complaint"
    GREETING = "greeting"
    GENERAL_QUERY = "general_query"
    UNKNOWN = "unknown"


class QueryModifier:
    """Extract query-specific requirements that override user preferences"""
    
    @staticmethod
    def extract_overrides(message: str) -> Dict:
        """
        Extract specific requirements from query that should override preferences
        Returns: {
            'spice_override': 'hot' | 'mild' | 'medium',
            'dietary_override': ['vegan', 'vegetarian'],
            'cuisine_override': ['Pakistani', 'Chinese'],
            'item_type': 'dessert' | 'main' | 'snack'
        }
        """
        message_lower = message.lower()
        overrides = {}
        
        # Spice level override (PRIORITY: query > user preference)
        spice_keywords = {
            'very_hot': ['very spicy', 'extra spicy', 'very hot', 'bahut tez'],
            'hot': ['spicy', 'hot', 'tez', 'teekha'],
            'mild': ['mild', 'not spicy', 'halka', 'no spice', 'bland']
        }
        
        for level, keywords in spice_keywords.items():
            if any(kw in message_lower for kw in keywords):
                overrides['spice_override'] = level
                logger.info(f"🌶️ Spice override detected: {level}")
                break
        
        # Dietary override (PRIORITY: query > user preference)
        dietary_keywords = {
            'vegan': ['vegan', 'plant based', 'no dairy', 'no animal'],
            'vegetarian': ['vegetarian', 'veg', 'veggie', 'no meat'],
            'gluten-free': ['gluten free', 'no gluten', 'gluten-free'],
            'halal': ['halal']
        }
        
        dietary_overrides = []
        for restriction, keywords in dietary_keywords.items():
            if any(kw in message_lower for kw in keywords):
                dietary_overrides.append(restriction.title())
                logger.info(f"🥗 Dietary override detected: {restriction}")
        
        if dietary_overrides:
            overrides['dietary_override'] = dietary_overrides
        
        # Cuisine override
        cuisine_keywords = {
            'Pakistani': ['pakistani', 'biryani', 'karahi', 'nihari', 'pulao', 'desi'],
            'Chinese': ['chinese', 'chowmein', 'fried rice', 'noodles', 'manchurian'],
            'Fast Food': ['burger', 'pizza', 'fries', 'sandwich', 'fast food'],
            'BBQ': ['bbq', 'tikka', 'kebab', 'grill', 'barbecue', 'seekh'],
            'Desserts': ['dessert', 'sweet', 'ice cream', 'cake', 'mithai', 'kulfi'],
            'Italian': ['italian', 'pasta', 'pizza'],
            'Japanese': ['japanese', 'sushi', 'ramen'],
            'Thai': ['thai', 'pad thai', 'curry']
        }
        
        cuisine_overrides = []
        for cuisine, keywords in cuisine_keywords.items():
            if any(kw in message_lower for kw in keywords):
                if not overrides.get('dietary_override') and not overrides.get('spice_override'):
                    cuisine_overrides.append(cuisine)
                    logger.info(f"🍽️ Cuisine override detected: {cuisine}")
        
        if cuisine_overrides:
            overrides['cuisine_override'] = cuisine_overrides
        
        # Item type detection
        item_types = {
            'main': ['main course', 'dinner', 'lunch', 'meal'],
            'snack': ['snack', 'light', 'appetizer', 'starter'],
            'dessert': ['dessert', 'sweet', 'after meal'],
            'drink': ['drink', 'beverage', 'juice']
        }
        
        for item_type, keywords in item_types.items():
            if any(kw in message_lower for kw in keywords):
                overrides['item_type'] = item_type
                logger.info(f"🍴 Item type override: {item_type}")
                break
        
        return overrides
    
    @staticmethod
    def detect_preference_conflict(query_overrides: Dict, user_preferences: Dict) -> Dict:
        """
        Detect when query conflicts with user's stored preferences
        Returns conflict information for confirmation prompts
        """
        conflicts = {
            "has_conflict": False,
            "conflicts": []
        }
        
        # Check spice conflict
        if 'spice_override' in query_overrides:
            user_spice = user_preferences.get('spice_preference', 'medium')
            query_spice = query_overrides['spice_override']
            
            # Conflict: User likes mild but asks for spicy (or vice versa)
            if (user_spice == 'mild' and query_spice in ['hot', 'very_hot']) or \
               (user_spice in ['hot', 'very_hot'] and query_spice == 'mild'):
                conflicts["has_conflict"] = True
                conflicts["conflicts"].append({
                    "type": "spice",
                    "user_preference": user_spice,
                    "query_request": query_spice,
                    "message": f"You usually prefer {user_spice} food, but you're asking for {query_spice}."
                })
        
        # Check dietary conflict
        if 'dietary_override' in query_overrides:
            user_dietary = user_preferences.get('dietary_restrictions', [])
            query_dietary = query_overrides['dietary_override']
            
            # Check if query conflicts with restrictions
            for restriction in user_dietary:
                if restriction.lower() not in [d.lower() for d in query_dietary]:
                    conflicts["has_conflict"] = True
                    conflicts["conflicts"].append({
                        "type": "dietary",
                        "user_preference": restriction,
                        "query_request": query_dietary,
                        "message": f"You're {restriction}, but you're looking for items that may not match this restriction."
                    })
        
        # Check cuisine conflict
        if 'cuisine_override' in query_overrides:
            user_cuisines = user_preferences.get('favorite_cuisines', [])
            query_cuisines = query_overrides['cuisine_override']
            
            # Check if query is completely different from preferences
            if user_cuisines and not any(c in query_cuisines for c in user_cuisines):
                conflicts["has_conflict"] = True
                conflicts["conflicts"].append({
                    "type": "cuisine",
                    "user_preference": user_cuisines,
                    "query_request": query_cuisines,
                    "message": f"You usually prefer {', '.join(user_cuisines)}, but you're asking for {', '.join(query_cuisines)}."
                })
        
        return conflicts


class ConversationContext:
    """Track conversation state"""
    
    def __init__(self):
        self.last_intent = None
        self.recommendations_shown = False
        self.reorder_shown = False
        self.turn_count = 0
        self.awaiting_selection = False
        self.last_overrides = {}
    
    def update(self, intent: Intent, overrides: Dict = None):
        """Update context with new intent"""
        self.last_intent = intent
        self.turn_count += 1
        if overrides:
            self.last_overrides = overrides
    
    def reset_if_loop(self) -> bool:
        """Check if we're in a loop"""
        if self.turn_count > 5 and not self.awaiting_selection:
            self.turn_count = 0
            return True
        return False


class EnhancedChatbot:
    """Advanced chatbot with better intent detection"""
    
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-2.0-flash-lite')
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
        self.contexts: Dict[str, ConversationContext] = {}
        self.query_modifier = QueryModifier()
    
    def detect_language(self, text: str) -> str:
        """Detect language"""
        urdu_chars = set('آابپتٹثجچحخدڈذرڑزژسشصضطظعغفقکگلمنںوہھءیےأإؤئ')
        if any(char in urdu_chars for char in text):
            return "ur"
        
        roman_urdu_keywords = [
            'hai', 'hain', 'kya', 'kuch', 'chahiye', 'bhook', 'khana', 
            'order', 'dikhao', 'mangwao', 'karo', 'de', 'do', 'naya',
            'dobara', 'pehle', 'wala', 'favourite', 'salam', 'yaar', 'bhai'
        ]
        text_lower = text.lower()
        if any(keyword in text_lower for keyword in roman_urdu_keywords):
            return "ur"
        
        return "en"
    
    async def detect_intent(self, message: str, user_context: Dict) -> Tuple[Intent, Dict]:
        """
        IMPROVED intent detection with better accuracy
        """
        message_lower = message.lower()
        extracted_data = {}
        
        # Extract query overrides FIRST
        overrides = self.query_modifier.extract_overrides(message)
        if overrides:
            extracted_data['query_overrides'] = overrides
            logger.info(f"📋 Query overrides: {overrides}")
        
        # Greeting (must be very short)
        greetings = ['hello', 'hi', 'hey', 'salam', 'السلام', 'assalam', 'kaise ho']
        if any(message_lower == greeting or message_lower.startswith(f"{greeting} ") 
               for greeting in greetings):
            return Intent.GREETING, extracted_data
        
        # Reorder
        reorder_keywords = [
            'reorder', 'same', 'again', 'previous', 'last time', 'before', 'usual',
            'dobara', 'pehle wala', 'favourite', 'phir se', 'دوبارہ', 'پہلے'
        ]
        if any(keyword in message_lower for keyword in reorder_keywords):
            return Intent.REORDER, extracted_data
        
        # New items
        new_keywords = [
            'new', 'different', 'unique', 'try something', 'haven\'t tried', 'never tried',
            'naya', 'alag', 'different', 'try karna', 'نیا', 'مختلف', 'explore'
        ]
        if any(keyword in message_lower for keyword in new_keywords):
            return Intent.NEW_ITEMS, extracted_data
        
        # Specific item search
        search_indicators = [
            'do you have', 'have you got', 'find', 'looking for', 'search for',
            'get me', 'i want', 'order', 'give me',
            'hai kya', 'mil sakta', 'dhundo', 'lao', 'لاؤ'
        ]
        
        specific_foods = [
            'biryani', 'karahi', 'nihari', 'pulao', 'tikka', 'kebab',
            'burger', 'pizza', 'sandwich', 'shawarma',
            'chowmein', 'fried rice', 'noodles',
            'cake', 'ice cream', 'kulfi'
        ]
        
        has_search_indicator = any(ind in message_lower for ind in search_indicators)
        has_specific_food = any(food in message_lower for food in specific_foods)
        
        if has_search_indicator and has_specific_food:
            for indicator in search_indicators:
                if indicator in message_lower:
                    parts = message_lower.split(indicator)
                    if len(parts) > 1:
                        item_query = parts[1].strip().replace('?', '').replace('please', '').strip()
                        if item_query:
                            extracted_data['item_query'] = item_query
                            return Intent.SPECIFIC_ITEM_SEARCH, extracted_data
        
        # Specific cuisine
        cuisine_indicators = [
            'show me', 'i want', 'give me', 'recommend', 'suggest',
            'dikhao', 'chahiye', 'de do', 'batao'
        ]
        
        cuisine_keywords = {
            'Pakistani': ['pakistani', 'desi', 'local'],
            'Chinese': ['chinese'],
            'Fast Food': ['fast food', 'junk food'],
            'BBQ': ['bbq', 'barbecue', 'grill'],
            'Desserts': ['dessert', 'sweet', 'mithai'],
            'Italian': ['italian'],
            'Japanese': ['japanese'],
            'Thai': ['thai']
        }
        
        if 'cuisine_override' in overrides:
            extracted_data['cuisines'] = overrides['cuisine_override']
            return Intent.SPECIFIC_CUISINE, extracted_data
        
        detected_cuisines = []
        for cuisine, keywords in cuisine_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                detected_cuisines.append(cuisine)
        
        if detected_cuisines:
            extracted_data['cuisines'] = detected_cuisines
            return Intent.SPECIFIC_CUISINE, extracted_data
        
        # Food recommendation
        food_keywords = [
            'hungry', 'eat', 'food', 'recommend', 'suggestion', 'suggest',
            'menu', 'craving', 'what should', 'what to eat', 'what can i',
            'bhook', 'khana', 'kuch', 'کچھ', 'بھوک', 'کھانا',
            'show me', 'show'
        ]
        if any(keyword in message_lower for keyword in food_keywords):
            return Intent.FOOD_RECOMMENDATION, extracted_data
        
        # Order status
        status_keywords = [
            'order', 'status', 'track', 'where', 'delivery',
            'kahan', 'aa gaya', 'آرڈر', 'ڈیلیوری'
        ]
        if any(keyword in message_lower for keyword in status_keywords):
            return Intent.ORDER_STATUS, extracted_data
        
        # Complaint
        complaint_keywords = [
            'problem', 'issue', 'complaint', 'wrong', 'bad', 'cold', 'late',
            'masla', 'mushkil', 'thanda', 'galat', 'shikayat', 'مسئلہ', 'شکایت'
        ]
        if any(keyword in message_lower for keyword in complaint_keywords):
            return Intent.COMPLAINT, extracted_data
        
        return Intent.GENERAL_QUERY, extracted_data
    
    def get_context(self, session_id: str) -> ConversationContext:
        """Get or create conversation context"""
        if session_id not in self.contexts:
            self.contexts[session_id] = ConversationContext()
        return self.contexts[session_id]
    
    async def generate_response(
        self,
        message: str,
        user_context: Dict,
        intent: Intent,
        order_history: Dict,
        reorder_items: List[Dict],
        new_items: List[Dict],
        session_id: str
    ) -> str:
        """
        Generate response with better error handling and conflict detection
        """
        username = user_context.get('username', 'User')
        lang = self.detect_language(message)
        context = self.get_context(session_id)
        
        # Get query overrides if any
        query_overrides = user_context.get('query_overrides', {})
        
        # DETECT PREFERENCE CONFLICTS
        conflicts = {}
        if query_overrides:
            conflicts = self.query_modifier.detect_preference_conflict(
                query_overrides,
                {
                    'spice_preference': user_context.get('spice_preference', 'medium'),
                    'dietary_restrictions': user_context.get('dietary_restrictions', []),
                    'favorite_cuisines': user_context.get('favorite_cuisines', [])
                }
            )
        
        # Update context
        context.update(intent, query_overrides)
        
        if context.reset_if_loop():
            if lang == "ur":
                return "کیا میں آپ کی مزید مدد کر سکتا ہوں؟"
            return "Is there anything else I can help you with?"
        
        response_lang = "Urdu" if lang == "ur" else "English"
        
        # Build history context
        history_context = ""
        if order_history.get("has_history"):
            total_orders = order_history.get("total_orders", 0)
            top_cuisine = list(order_history.get("cuisine_preferences", {}).keys())[0] if order_history.get("cuisine_preferences") else ""
            if top_cuisine:
                history_context = f"\n\nOrder History: {total_orders} orders. Prefers {top_cuisine}."
        
        # Build recommendations context with overrides highlighted
        recs_context = ""
        
        if query_overrides:
            recs_context += "\n\n⚠️ USER QUERY OVERRIDES (Priority):\n"
            if 'spice_override' in query_overrides:
                recs_context += f"  - Wants: {query_overrides['spice_override']} spice level\n"
            if 'dietary_override' in query_overrides:
                recs_context += f"  - Dietary: {', '.join(query_overrides['dietary_override'])}\n"
            if 'cuisine_override' in query_overrides:
                recs_context += f"  - Cuisines: {', '.join(query_overrides['cuisine_override'])}\n"
        
        # ADD CONFLICT WARNING TO CONTEXT
        if conflicts.get("has_conflict"):
            recs_context += "\n\n⚠️ PREFERENCE CONFLICT DETECTED:\n"
            for conflict in conflicts.get("conflicts", []):
                recs_context += f"  - {conflict['message']}\n"
            recs_context += "\n**IMPORTANT**: Ask user if they want to proceed with this different preference.\n"
        
        if reorder_items and intent in [Intent.REORDER, Intent.FOOD_RECOMMENDATION]:
            context.reorder_shown = True
            recs_context += "\n\n🔄 **FAVORITES**:\n"
            for idx, item in enumerate(reorder_items[:3], 1):
                recs_context += f"{idx}. {item['name']} - PKR {item['price']}\n"
        
        if new_items:
            context.recommendations_shown = True
            header = "🆕 **NEW OPTIONS**" if reorder_items else "🍽️ **RECOMMENDATIONS**"
            recs_context += f"\n\n{header}:\n"
            for idx, item in enumerate(new_items[:3], 1):
                cuisines = ', '.join(item.get('restaurant_cuisine', []))
                spice = item.get('spice_level', 'medium')
                recs_context += f"{idx}. {item['name']} ({cuisines}, {spice} spice) - PKR {item['price']}\n"
        
        # Build prompt based on intent
        if intent == Intent.GREETING:
            prompt = f"""Friendly food assistant for Voice Guide.
User: {username}
Message: "{message}"
Task: Greet warmly, ask if they'd like food. 1-2 sentences. {response_lang}."""

        elif intent == Intent.REORDER:
            if not reorder_items:
                prompt = f"""User wants to reorder but has no history.
Task: Politely say no previous orders, offer recommendations. Brief. {response_lang}."""
            else:
                prompt = f"""User: {username}
{history_context}
Message: "{message}"
{recs_context}
Task: Show favorites with order counts. Enthusiastic. 2 sentences. {response_lang}."""

        elif intent == Intent.NEW_ITEMS:
            prompt = f"""User: {username}
Preferences: {', '.join(user_context.get('favorite_cuisines', []))}
{history_context}
Message: "{message}"
{recs_context}
Task: Present NEW items excitedly. Highlight they're different from usual. 2 sentences. {response_lang}."""

        elif intent == Intent.SPECIFIC_CUISINE:
            prompt = f"""User: {username}
Message: "{message}"
{recs_context}
Task: Present these items matching their request. Brief and appetizing. 1-2 sentences. {response_lang}."""

        elif intent == Intent.SPECIFIC_ITEM_SEARCH:
            if not new_items:
                prompt = f"""User searched for: "{message}"
No items found.
Task: Apologize, suggest similar alternatives. Helpful. 1-2 sentences. {response_lang}."""
            else:
                prompt = f"""User searched: "{message}"
{recs_context}
Task: Confirm we found items. Present them. Brief. 1-2 sentences. {response_lang}."""

        elif intent == Intent.FOOD_RECOMMENDATION:
            if not recs_context:
                prompt = f"""User wants food but no items available right now.
Task: Apologize briefly, suggest trying Biryani or Burgers. Helpful. 1-2 sentences. {response_lang}."""
            else:
                # HANDLE CONFLICTS IN FOOD RECOMMENDATIONS
                if conflicts.get("has_conflict"):
                    conflict_msg = conflicts["conflicts"][0]["message"]
                    prompt = f"""User: {username}
{history_context}
Message: "{message}"
{recs_context}

⚠️ CONFLICT DETECTED: {conflict_msg}

Task: 
1. Acknowledge their usual preference
2. Mention they're asking for something different
3. Ask if they want to see those options anyway
4. Be friendly and supportive. 2-3 sentences. {response_lang}."""
                else:
                    prompt = f"""User: {username}
{history_context}
Message: "{message}"
{recs_context}
Task: Present items. If favorites exist, mention those first. Concise. 2-3 sentences. {response_lang}."""

        elif intent == Intent.COMPLAINT:
            prompt = f"""User has concern: "{message}"
Task: Apologize empathetically. Offer help. Professional. 2 sentences. {response_lang}."""

        else:
            prompt = f"""User asked: "{message}"
Task: Answer helpfully. Guide toward ordering if food-related. Brief. 1-2 sentences. {response_lang}."""

        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=200
                ),
                safety_settings=self.safety_settings
            )
            
            if response.parts:
                generated = response.text.strip()
                context.awaiting_selection = bool(recs_context)
                return generated
            
            # Fallback
            if lang == "ur":
                return "میں یہاں آپ کی مدد کے لیے ہوں۔ کیا آپ کچھ آرڈر کرنا چاہیں گے?"
            return "I'm here to help! What would you like to order?"
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            if lang == "ur":
                return "معذرت، کچھ مسئلہ ہوا۔ دوبارہ کوشش کریں۔"
            return "Sorry, something went wrong. Please try again."
    
    def clear_context(self, session_id: str):
        """Clear conversation context"""
        if session_id in self.contexts:
            del self.contexts[session_id]