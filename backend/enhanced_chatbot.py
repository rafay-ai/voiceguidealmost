"""
Enhanced Chatbot with Intent Detection and Context Management
Supports both English and Urdu with intelligent conversation flow
"""

import os
import logging
import asyncio
from typing import Dict, List, Optional, Tuple
from enum import Enum
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)


class Intent(Enum):
    """User intent classification"""
    FOOD_RECOMMENDATION = "food_recommendation"
    REORDER = "reorder"
    NEW_ITEMS = "new_items"
    SPECIFIC_CUISINE = "specific_cuisine"
    RESTAURANT_QUERY = "restaurant_query"
    ORDER_STATUS = "order_status"
    COMPLAINT = "complaint"
    GREETING = "greeting"
    GENERAL_QUERY = "general_query"
    UNKNOWN = "unknown"


class ConversationContext:
    """Track conversation state to avoid loops"""
    
    def __init__(self):
        self.last_intent = None
        self.recommendations_shown = False
        self.reorder_shown = False
        self.turn_count = 0
        self.awaiting_selection = False
    
    def update(self, intent: Intent):
        """Update context with new intent"""
        self.last_intent = intent
        self.turn_count += 1
    
    def reset_if_loop(self) -> bool:
        """Check if we're in a loop and reset if needed"""
        if self.turn_count > 5 and not self.awaiting_selection:
            self.turn_count = 0
            return True
        return False


class EnhancedChatbot:
    """Advanced chatbot with intent detection and bilingual support"""
    
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
        # Store conversation contexts by session_id
        self.contexts: Dict[str, ConversationContext] = {}
    
    def detect_language(self, text: str) -> str:
        """Detect if text is in Urdu, Roman Urdu, or English"""
        # Check for Urdu characters (pure Urdu script)
        urdu_chars = set('آابپتٹثجچحخدڈذرڑزژسشصضطظعغفقکگلمنںوہھءیےأإؤئ')
        if any(char in urdu_chars for char in text):
            return "ur"
        
        # Check for Roman Urdu keywords (Urdu written in English)
        roman_urdu_keywords = [
            'hai', 'hain', 'kya', 'kuch', 'chahiye', 'bhook', 'khana', 
            'order', 'dikhao', 'mangwao', 'karo', 'de', 'do', 'naya',
            'dobara', 'pehle', 'wala', 'favourite', 'salam', 'yaar', 'bhai'
        ]
        text_lower = text.lower()
        if any(keyword in text_lower for keyword in roman_urdu_keywords):
            return "ur"  # Treat Roman Urdu same as Urdu for response language
        
        return "en"
    
    async def detect_intent(self, message: str, user_context: Dict) -> Tuple[Intent, Dict]:
        """
        Detect user intent from message (supports English and Roman Urdu)
        Returns: (Intent, extracted_data)
        """
        message_lower = message.lower()
        extracted_data = {}
        
        # Greeting detection (English + Roman Urdu + Pure Urdu)
        greetings = ['hello', 'hi', 'hey', 'salam', 'السلام', 'assalam', 'kaise', 'kya hal']
        if any(greeting in message_lower for greeting in greetings):
            return Intent.GREETING, extracted_data
        
        # Reorder intent (English + Roman Urdu + Pure Urdu)
        reorder_keywords = [
            'reorder', 'same', 'again', 'previous', 'last time', 'before', 'usual',
            'dobara', 'pehle', 'wala', 'favourite', 'phir se', 'دوبارہ', 'پہلے'
        ]
        if any(keyword in message_lower for keyword in reorder_keywords):
            return Intent.REORDER, extracted_data
        
        # New items intent (English + Roman Urdu + Pure Urdu)
        new_keywords = [
            'new', 'different', 'unique', 'try something', 'haven\'t tried', 'never tried',
            'naya', 'alag', 'different', 'try karna', 'نیا', 'مختلف'
        ]
        if any(keyword in message_lower for keyword in new_keywords):
        
        # Specific cuisine detection (English + Roman Urdu + Pure Urdu)
        cuisine_keywords = {
            'pakistani': ['pakistani', 'biryani', 'karahi', 'nihari', 'pulao', 'پاکستانی', 'بریانی'],
            'chinese': ['chinese', 'chowmein', 'fried rice', 'noodles', 'چائنیز'],
            'fast food': ['burger', 'pizza', 'fries', 'sandwich', 'برگر', 'پیزا'],
            'bbq': ['bbq', 'tikka', 'kebab', 'grill', 'بی بی کیو', 'seekh'],
            'dessert': ['dessert', 'sweet', 'ice cream', 'cake', 'kulfi', 'میٹھا', 'آئس کریم', 'mithai'],
            'japanese': ['japanese', 'sushi', 'ramen', 'جاپانی'],
            'thai': ['thai', 'pad thai', 'curry', 'تھائی'],
            'indian': ['indian', 'curry', 'tandoori', 'masala', 'انڈین']
        }
        
        detected_cuisines = []
        for cuisine, keywords in cuisine_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                detected_cuisines.append(cuisine.title())
        
        if detected_cuisines:
            extracted_data['cuisines'] = detected_cuisines
            return Intent.SPECIFIC_CUISINE, extracted_data
        
        # Food recommendation intent (English + Roman Urdu + Pure Urdu)
        food_keywords = [
            'hungry', 'eat', 'food', 'order', 'recommend', 'suggestion', 'suggest', 'menu',
            'bhook', 'kha', 'khana', 'mangwa', 'dikhao', 'chahiye', 
            'بھوک', 'کھانا', 'آرڈر'
        ]
        if any(keyword in message_lower for keyword in food_keywords):
            return Intent.FOOD_RECOMMENDATION, extracted_data
        
        # Order status (English + Roman Urdu)
        status_keywords = [
            'order', 'status', 'track', 'where', 'delivery', 'kahan', 'aa gaya', 
            'آرڈر', 'ڈیلیوری'
        ]
        if any(keyword in message_lower for keyword in status_keywords):
            return Intent.ORDER_STATUS, extracted_data
        
        # Complaint (English + Roman Urdu)
        complaint_keywords = [
            'problem', 'issue', 'complaint', 'wrong', 'bad', 'cold', 'late',
            'masla', 'mushkil', 'thanda', 'galat', 'shikayat',
            'مسئلہ', 'شکایت'
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
        Generate contextual response based on intent and available data
        """
        username = user_context.get('username', 'User')
        lang = self.detect_language(message)
        context = self.get_context(session_id)
        
        # Update context
        context.update(intent)
        
        # Check for conversation loop
        if context.reset_if_loop():
            if lang == "ur":
                return "کیا میں آپ کی مزید مدد کر سکتا ہوں؟ آپ کھانا آرڈر کرنا چاہیں گے؟"
            return "Is there anything else I can help you with? Would you like to place an order?"
        
        # Determine response language
        response_lang = "Urdu" if lang == "ur" else "English"
        
        # Build context for Gemini
        history_context = ""
        if order_history.get("has_history"):
            total_orders = order_history.get("total_orders", 0)
            top_cuisine = list(order_history.get("cuisine_preferences", {}).keys())[0] if order_history.get("cuisine_preferences") else "Pakistani"
            history_context = f"\n\n📊 User History: {total_orders} orders in past month. Prefers {top_cuisine} cuisine."
        
        # Build recommendations context
        recs_context = ""
        
        if reorder_items and intent in [Intent.REORDER, Intent.FOOD_RECOMMENDATION]:
            context.reorder_shown = True
            recs_context += "\n\n🔄 **FAVORITES TO REORDER**:\n"
            for idx, item in enumerate(reorder_items[:3], 1):
                recs_context += f"{idx}. {item['name']} - PKR {item['price']} (Ordered {item['order_count']}x)\n"
        
        if new_items:
            context.recommendations_shown = True
            header = "🆕 **TRY SOMETHING NEW**" if reorder_items else "🍽️ **RECOMMENDED FOR YOU**"
            recs_context += f"\n\n{header}:\n"
            for idx, item in enumerate(new_items[:3], 1):
                cuisines = ', '.join(item.get('restaurant_cuisine', []))
                recs_context += f"{idx}. {item['name']} - {item['restaurant_name']} ({cuisines}) - PKR {item['price']}\n"
        
        # Construct prompt based on intent
        if intent == Intent.GREETING:
            prompt = f"""You are a friendly food assistant for Voice Guide in Karachi.

User: {username}
{history_context}

User said: "{message}"

Task: Greet warmly and ask if they'd like to order food. Keep it brief (1-2 sentences). Respond in {response_lang}."""

        elif intent == Intent.REORDER:
            if not reorder_items:
                prompt = f"""You are a friendly food assistant for Voice Guide in Karachi.

User: {username}
Preferences: {', '.join(user_context.get('favorite_cuisines', []))}

User wants to reorder but has no order history.

Task: Politely explain they haven't ordered before and offer to show recommendations. Respond in {response_lang}. Keep it brief."""
            else:
                prompt = f"""You are a friendly food assistant for Voice Guide in Karachi.

User: {username}
{history_context}

User asked: "{message}"

{recs_context}

Task: Show their past favorites enthusiastically. Mention how many times they've ordered each item. Keep it friendly and concise (2-3 sentences). Respond in {response_lang}."""

        elif intent == Intent.NEW_ITEMS:
            prompt = f"""You are a friendly food assistant for Voice Guide in Karachi.

User: {username}
Preferences: {', '.join(user_context.get('favorite_cuisines', []))}
{history_context}

User wants: "{message}"

{recs_context}

Task: Present NEW recommendations enthusiastically. If they have order history, briefly acknowledge their usual favorites then highlight the new items. Keep it engaging (2-3 sentences). Respond in {response_lang}."""

        elif intent == Intent.SPECIFIC_CUISINE:
            prompt = f"""You are a friendly food assistant for Voice Guide in Karachi.

User: {username}
Preferences: {', '.join(user_context.get('favorite_cuisines', []))}

User requested: "{message}"

{recs_context}

Task: Present the cuisine-specific recommendations. Keep it brief and appetizing (1-2 sentences). Respond in {response_lang}."""

        elif intent == Intent.FOOD_RECOMMENDATION:
            if not reorder_items and not new_items:
                prompt = f"""You are a friendly food assistant for Voice Guide in Karachi.

User: {username}
Preferences: {', '.join(user_context.get('favorite_cuisines', []))}

User asked: "{message}"

No specific items found at the moment.

Task: Apologize briefly and suggest they can try popular cuisines like Biryani, Burgers, or Pizza. Keep it helpful (1-2 sentences). Respond in {response_lang}."""
            else:
                prompt = f"""You are a friendly food assistant for Voice Guide in Karachi.

User: {username}
Preferences: {', '.join(user_context.get('favorite_cuisines', []))}
{history_context}

User asked: "{message}"

{recs_context}

Task: If they have favorites, show those FIRST with order counts. Then present new items. Keep response concise (2-3 sentences total). Respond in {response_lang}."""

        elif intent == Intent.COMPLAINT:
            prompt = f"""You are a friendly food assistant for Voice Guide in Karachi.

User: {username}

User has a concern: "{message}"

Task: Respond empathetically and professionally. Apologize and offer to help resolve the issue. Ask them to contact support if needed. Keep it caring (2-3 sentences). Respond in {response_lang}."""

        else:  # GENERAL_QUERY
            prompt = f"""You are a friendly food assistant for Voice Guide in Karachi.

User: {username}

User asked: "{message}"

Task: Answer their question helpfully. If food-related, gently guide them to place an order. Keep it brief (1-2 sentences). Respond in {response_lang}."""

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
                context.awaiting_selection = bool(recs_context)  # User needs to select from recommendations
                return generated
            
            # Fallback responses
            if lang == "ur":
                return "میں آپ کی مدد کے لیے حاضر ہوں۔ آپ کیا آرڈر کرنا چاہیں گے؟"
            return "I'm here to help! What would you like to order?"
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            if lang == "ur":
                return "معذرت، کچھ مسئلہ ہوا۔ دوبارہ کوشش کریں۔"
            return "Sorry, something went wrong. Please try again."
    
    def clear_context(self, session_id: str):
        """Clear conversation context for a session"""
        if session_id in self.contexts:
            del self.contexts[session_id]
