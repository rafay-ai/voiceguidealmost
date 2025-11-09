from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, Request, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from sklearn.feature_extraction.text import TfidfVectorizer
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os
import logging
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import google.generativeai as genai
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re

# Import our enhanced modules
from recommendation_engine import RecommendationEngine
from enhanced_chatbot import EnhancedChatbot, Intent

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Configure Gemini
genai.configure(api_key=os.environ['GEMINI_API_KEY'])

# Email Configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = "abdulrafayy277@gmail.com"
EMAIL_PASSWORD = "brgapzawujokcbmb"  # Remove spaces from app password
EMAIL_FROM_NAME = "VoiceGuide"

# Create the main app
app = FastAPI(title="Voice Guide API", version="2.0.0")
api_router = APIRouter(prefix="/api")

# JWT Configuration
SECRET_KEY = "voice_guide_secret_key_2024"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

# Security
security = HTTPBearer()
executor = ThreadPoolExecutor(max_workers=4)

# Initialize Enhanced Components
recommendation_engine = RecommendationEngine(db)
enhanced_chatbot = EnhancedChatbot()

# Initialize embeddings on startup
@app.on_event("startup")
async def startup_event():
    """Initialize embeddings for menu items on server startup"""
    logging.info("Initializing recommendation engine...")
    try:
        # Generate embeddings for items that don't have them yet
        count = await recommendation_engine.generate_item_embeddings(limit=100)  # Limit to 100 for initial setup
        logging.info(f"Initialized {count} menu item embeddings")
    except Exception as e:
        logging.error(f"Error initializing embeddings: {e}")

# Karachi Areas Data
KARACHI_AREAS = {
    "District Central": [
        "Gulberg", "Federal B Area", "North Nazimabad", "Nazimabad", 
        "Buffer Zone", "New Karachi", "North Karachi", "Gulshan-e-Iqbal"
    ],
    "District East": [
        "Gulistan-e-Jauhar", "Gulshan-e-Iqbal", "University Road", 
        "Karsaz", "Drigh Road", "Faisal Cantonment", "Malir"
    ],
    "District South": [
        "Clifton", "Defence (DHA)", "Garden", "Saddar", "Civil Lines", 
        "Arambagh", "Kharadar", "Mithadar", "Soldier Bazar"
    ],
    "District West": [
        "Orangi Town", "Baldia Town", "SITE", "Manghopir", 
        "Mauripur", "Keamari", "Fish Harbour"
    ],
    "District Malir": [
        "Malir", "Airport", "Jinnah Terminal", "Korangi", 
        "Landhi", "Shah Faisal Colony", "Bin Qasim"
    ],
    "District Korangi": [
        "Korangi", "Landhi", "Shah Faisal Colony", "Model Colony", 
        "Allama Iqbal Town", "Zaman Town"
    ]
}

# --- Data Models ---
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    email: str
    password_hash: str
    preferences: Dict[str, Any] = Field(default_factory=dict)
    dietary_restrictions: List[str] = Field(default_factory=list)
    favorite_cuisines: List[str] = Field(default_factory=list)
    spice_preference: str = "medium"
    addresses: List[Dict[str, Any]] = Field(default_factory=list)
    default_address_id: Optional[str] = None
    phone: Optional[str] = None
    preferences_set: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    phone: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class Address(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    label: str  # Home, Office, etc.
    district: str
    area: str
    street_address: str
    landmark: Optional[str] = None
    phone: str
    is_default: bool = False

class Restaurant(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    rating: float
    price_range: str
    cuisine: List[str]
    delivery_time: str
    delivery_fee: float
    minimum_order: float
    is_active: bool = True
    image: str = "/api/placeholder/restaurant"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class MenuItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    price: float
    category: str
    restaurant_id: str
    image: str = "/api/placeholder/food-item"
    available: bool = True
    preparation_time: int
    spice_level: str
    is_vegetarian: bool
    is_halal: bool
    tags: List[str]
    popularity_score: float
    order_count: int = 0
    average_rating: float = 0.0
    rating_count: int = 0
    embedding: Optional[List[float]] = None
    embedding_text: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CartItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    menu_item_id: str
    restaurant_id: str
    quantity: int
    special_instructions: str = ""
    added_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CartItemAdd(BaseModel):
    menu_item_id: str
    restaurant_id: str
    quantity: int = 1
    special_instructions: str = ""

class OrderItem(BaseModel):
    menu_item_id: str
    quantity: int
    price: float
    special_instructions: str = ""

class Order(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order_number: str
    user_id: str
    restaurant_id: str
    items: List[OrderItem]
    delivery_address: Dict[str, str]
    payment_method: str
    payment_status: str = "pending"
    order_status: str = "placed"
    pricing: Dict[str, float]
    estimated_delivery_time: Optional[datetime] = None
    actual_delivery_time: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CheckoutRequest(BaseModel):
    address_id: str
    payment_method: str  # "easypaisa" or "cod"
    special_instructions: str = ""

class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    message: str
    response: str
    message_type: str = "text"  # text, voice
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PreferenceUpdate(BaseModel):
    favorite_cuisines: Optional[List[str]] = None
    dietary_restrictions: Optional[List[str]] = None
    spice_preference: Optional[str] = None

class VoiceOrderRequest(BaseModel):
    audio_text: str
    user_id: str

class ChatRequest(BaseModel):
    message: str
    user_id: str
    session_id: Optional[str] = None

class PreferencesSetup(BaseModel):
    favorite_cuisines: List[str]
    dietary_restrictions: List[str]
    spice_preference: str

# --- Helper Functions ---
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return User(**user)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

def generate_order_number():
    """Generate unique order number"""
    import random
    return f"VG{datetime.now().strftime('%Y%m%d')}{random.randint(1000, 9999)}"

def detect_language(text: str) -> str:
    # Basic check for Urdu characters (add more comprehensive check if needed)
    urdu_chars = r'[\u0600-\u06FF\u0750-\u077F\u0591-\u05F4]' # Include Hebrew just in case for script similarity detection
    if re.search(urdu_chars, text):
        return 'ur'
    # Add checks for other languages if necessary
    return 'en' # Default to English

async def generate_embedding(text: str) -> List[float]:
    """Generate embedding vector for text using Gemini"""
    try:
        # Use genai.embed_content for embeddings
        result = await asyncio.to_thread(
            genai.embed_content,
            model="models/text-embedding-004",
            content=text,
            task_type="retrieval_document"
        )
        return result['embedding']
    except Exception as e:
        logging.error(f"Error generating embedding: {e}")
        return None
    
#----EMBEDDING FUNCTION----
def cosine_similarity_vectors(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two embedding vectors"""
    if not vec1 or not vec2:
        return 0.0
    
    # Convert to numpy arrays for efficient computation
    v1 = np.array(vec1)
    v2 = np.array(vec2)
    
    # Calculate cosine similarity
    dot_product = np.dot(v1, v2)
    magnitude1 = np.linalg.norm(v1)
    magnitude2 = np.linalg.norm(v2)
    
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    
    return float(dot_product / (magnitude1 * magnitude2))

async def create_menu_item_text(menu_item: Dict) -> str:
    """Create rich text representation of menu item for embedding"""
    parts = [
        menu_item.get('name', ''),
        menu_item.get('description', ''),
        menu_item.get('category', ''),
        ' '.join(menu_item.get('tags', [])),
        f"spice level: {menu_item.get('spice_level', 'medium')}",
        "vegetarian" if menu_item.get('is_vegetarian') else "",
        "halal" if menu_item.get('is_halal') else ""
    ]
    
    # Get restaurant info
    restaurant = await db.restaurants.find_one(
        {"id": menu_item.get('restaurant_id')}, 
        {"_id": 0, "cuisine": 1}
    )
    if restaurant and restaurant.get('cuisine'):
        parts.append(' '.join(restaurant['cuisine']))
    
    return ' '.join(filter(None, parts))

def deduplicate_items_by_name(items: List[Dict]) -> List[Dict]:
        """Remove duplicate items with same name, keep highest scoring one"""
        seen_names = {}
        unique_items = []
    
        for item in items:
            name = item.get('name', '')
            score = item.get('preference_score', 0) or item.get('recommendation_score', 0)
        
            if name not in seen_names or score > seen_names[name]['score']:
                seen_names[name] = {'item': item, 'score': score}
    
        return [data['item'] for data in seen_names.values()]


# --- Email Service ---
async def send_order_confirmation_email(user_email: str, user_name: str, order: dict, order_items: List[dict]):
    """Send order confirmation email"""
    try:
        msg = MIMEMultipart()
        msg['From'] = f"{EMAIL_FROM_NAME} <{EMAIL_ADDRESS}>"
        msg['To'] = user_email
        msg['Subject'] = f"Order Confirmation - {order['order_number']}"
        
        # Calculate total
        total_amount = order['pricing']['total']
        
        # Create HTML email body
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #f97316, #fb7185); padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">Voice Guide</h1>
                <p style="color: white; margin: 5px 0;">Order Confirmation</p>
            </div>
            
            <div style="padding: 20px; background: #f8f9fa;">
                <h2 style="color: #333;">Hi {user_name},</h2>
                <p>Thank you for your order! Your food is being prepared and will be delivered soon.</p>
                
                <div style="background: white; padding: 15px; border-radius: 8px; margin: 15px 0;">
                    <h3 style="color: #f97316; margin-top: 0;">Order Details</h3>
                    <p><strong>Order Number:</strong> {order['order_number']}</p>
                    <p><strong>Status:</strong> {order['order_status'].title()}</p>
                    <p><strong>Payment Method:</strong> {order['payment_method'].title()}</p>
                </div>
                
                <div style="background: white; padding: 15px; border-radius: 8px; margin: 15px 0;">
                    <h3 style="color: #f97316; margin-top: 0;">Items Ordered</h3>
        """
        
        for item in order_items:
            html_body += f"""
                    <div style="border-bottom: 1px solid #eee; padding: 10px 0;">
                        <p style="margin: 0;"><strong>{item['name']}</strong></p>
                        <p style="margin: 0; color: #666;">Quantity: {item['quantity']} × PKR {item['price']}</p>
                        {f"<p style='margin: 0; color: #888; font-style: italic;'>Note: {item['special_instructions']}</p>" if item.get('special_instructions') else ""}
                    </div>
            """
        
        html_body += f"""
                </div>
                
                <div style="background: white; padding: 15px; border-radius: 8px; margin: 15px 0;">
                    <h3 style="color: #f97316; margin-top: 0;">Delivery Address</h3>
                    <p style="margin: 0;">{order['delivery_address']['area']}, {order['delivery_address']['district']}</p>
                    <p style="margin: 0;">{order['delivery_address']['street_address']}</p>
                    <p style="margin: 0;">Phone: {order['delivery_address']['phone']}</p>
                </div>
                
                <div style="background: #f97316; color: white; padding: 15px; border-radius: 8px; text-align: center;">
                    <h2 style="margin: 0;">Total: PKR {total_amount}</h2>
                </div>
                
                <p style="text-align: center; margin-top: 20px; color: #666;">
                    Thank you for choosing Voice Guide!<br>
                    Track your order in the app for real-time updates.
                </p>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_body, 'html'))
        
        # Send email
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"✅ Order confirmation email sent to {user_email}")
        
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

# --- Recommendation Engine ---
class RecommendationEngine:
    def __init__(self, db_client):
        self.db = db_client

    async def get_user_order_history(self, user_id: str, limit: int = 50):
        """Get user's order history for recommendations"""
        orders_cursor = self.db.orders.find(
            {"user_id": user_id}, 
            {"_id": 0},
            sort=[("created_at", -1)]
        ).limit(limit)
        return await orders_cursor.to_list(None)

    async def get_user_preferences_vector(self, user_id: str):
        """Create user preference vector based on order history and explicit preferences"""
        user = await self.db.users.find_one({"id": user_id}, {"_id": 0})
        if not user:
            return None

        orders = await self.get_user_order_history(user_id)
        
        # Initialize preference scores
        cuisine_scores = {}
        spice_scores = {}
        category_scores = {}
        time_decay = 0.95  # Recent orders have more weight
        
        # Process order history
        for i, order in enumerate(orders):
            weight = time_decay ** i  # More recent orders have higher weight
            
            for item in order.get('items', []):
                menu_item = await self.db.menu_items.find_one({"id": item['menu_item_id']}, {"_id": 0})
                if menu_item:
                    # Update cuisine preferences
                    restaurant = await self.db.restaurants.find_one({"id": menu_item['restaurant_id']}, {"_id": 0})
                    if restaurant:
                        for cuisine in restaurant.get('cuisine', []):
                            cuisine_scores[cuisine] = cuisine_scores.get(cuisine, 0) + weight * item['quantity']
                    
                    # Update category preferences
                    category = menu_item.get('category', '')
                    category_scores[category] = category_scores.get(category, 0) + weight * item['quantity']
                    
                    # Update spice preferences
                    spice_level = menu_item.get('spice_level', 'medium')
                    spice_scores[spice_level] = spice_scores.get(spice_level, 0) + weight * item['quantity']

        # Combine with explicit preferences
        explicit_preferences = user.get('preferences', {})
        favorite_cuisines = user.get('favorite_cuisines', [])
        
        # Boost explicitly mentioned preferences
        for cuisine in favorite_cuisines:
            cuisine_scores[cuisine] = cuisine_scores.get(cuisine, 0) + 5.0

        return {
            'user_id': user_id,
            'cuisine_preferences': cuisine_scores,
            'category_preferences': category_scores,
            'spice_preferences': spice_scores,
            'explicit_preferences': explicit_preferences
        }

    async def get_similar_users(self, user_id: str, limit: int = 10):
        """Find users with similar preferences using collaborative filtering"""
        target_user_prefs = await self.get_user_preferences_vector(user_id)
        if not target_user_prefs:
            return []

        # Get all users with order history
        users_with_orders = await self.db.orders.distinct("user_id")
        similar_users = []

        for other_user_id in users_with_orders[:50]:  # Limit for performance
            if other_user_id == user_id:
                continue
                
            other_prefs = await self.get_user_preferences_vector(other_user_id)
            if not other_prefs:
                continue

            # Calculate similarity score
            similarity = self.calculate_user_similarity(target_user_prefs, other_prefs)
            if similarity > 0.3:  # Minimum similarity threshold
                similar_users.append((other_user_id, similarity))

        # Sort by similarity and return top users
        similar_users.sort(key=lambda x: x[1], reverse=True)
        return similar_users[:limit]

    def calculate_user_similarity(self, user1_prefs, user2_prefs):
        """Calculate similarity between two users based on their preferences"""
        cuisine_sim = self.calculate_dict_similarity(
            user1_prefs['cuisine_preferences'], 
            user2_prefs['cuisine_preferences']
        )
        category_sim = self.calculate_dict_similarity(
            user1_prefs['category_preferences'], 
            user2_prefs['category_preferences']
        )
        
        # Weighted average of different similarity measures
        overall_similarity = (cuisine_sim * 0.6 + category_sim * 0.4)
        return overall_similarity

    def calculate_dict_similarity(self, dict1, dict2):
        """Calculate cosine similarity between two dictionaries"""
        if not dict1 or not dict2:
            return 0.0

        all_keys = set(list(dict1.keys()) + list(dict2.keys()))
        if not all_keys:
            return 0.0

        vec1 = [dict1.get(key, 0) for key in all_keys]
        vec2 = [dict2.get(key, 0) for key in all_keys]

        # Calculate cosine similarity
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    async def get_recommendations(self, user_id: str, limit: int = 20):
        """Get personalized recommendations for a user, strongly considering preferences"""
        user = await self.db.users.find_one({"id": user_id}, {"_id": 0})
        if not user or not user.get("preferences_set"):
            # Return popular items if no user or preferences not set
            logging.info(f"User {user_id} not found or preferences not set, returning popular items.")
            return await self.get_popular_items(limit)

        user_prefs_vector = await self.get_user_preferences_vector(user_id)
        if not user_prefs_vector:
            logging.warning(f"Could not generate preferences vector for user {user_id}, returning popular items.")
            return await self.get_popular_items(limit)

        # Get content-based recommendations FIRST, strongly based on explicit preferences
        content_based_items = await self.get_content_based_recommendations(user_prefs_vector, limit)

        # Get similar users for collaborative filtering
        similar_users = await self.get_similar_users(user_id)

        # Get items ordered by similar users
        collaborative_items = await self.get_collaborative_recommendations(user_id, similar_users, limit // 2)

        # Combine and remove duplicates, prioritizing content-based
        all_recommendations = []
        seen_items = set()

        # Add content-based results first
        for item in content_based_items:
            if item['id'] not in seen_items:
                item['recommendation_reason'] = 'Based on your preferences'
                all_recommendations.append(item)
                seen_items.add(item['id'])

        # Add collaborative filtering results
        for item in collaborative_items:
            if item['id'] not in seen_items:
                item['recommendation_reason'] = 'Users like you also enjoyed'
                all_recommendations.append(item)
                seen_items.add(item['id'])

        # Fill remaining slots with popular items if needed
        if len(all_recommendations) < limit:
            popular_items = await self.get_popular_items(limit - len(all_recommendations))
            for item in popular_items:
                if item['id'] not in seen_items:
                    item['recommendation_reason'] = 'Popular choice'
                    all_recommendations.append(item)
                    seen_items.add(item['id'])

        logging.info(f"Generated {len(all_recommendations)} recommendations for user {user_id}")
        return all_recommendations[:limit]

    async def get_collaborative_recommendations(self, user_id: str, similar_users: List[tuple], limit: int):
        """Get recommendations based on similar users' orders"""
        if not similar_users:
            return []

        item_scores = {}
        user_ordered_items = set()

        # Get items already ordered by the target user
        user_orders = await self.get_user_order_history(user_id)
        for order in user_orders:
            for item in order.get('items', []):
                user_ordered_items.add(item['menu_item_id'])

        # Score items based on similar users' preferences
        for similar_user_id, similarity_score in similar_users:
            similar_user_orders = await self.get_user_order_history(similar_user_id, 20)
            
            for order in similar_user_orders:
                for item in order.get('items', []):
                    menu_item_id = item['menu_item_id']
                    
                    # Skip items already ordered by the user
                    if menu_item_id in user_ordered_items:
                        continue
                    
                    # Score based on similarity and quantity
                    score = similarity_score * item['quantity']
                    item_scores[menu_item_id] = item_scores.get(menu_item_id, 0) + score

        # Get top scored items
        top_items = sorted(item_scores.items(), key=lambda x: x[1], reverse=True)[:limit]
        
        # Fetch menu item details
        recommendations = []
        for menu_item_id, score in top_items:
            menu_item = await self.db.menu_items.find_one({"id": menu_item_id}, {"_id": 0})
            if menu_item and menu_item.get('available', True):
                menu_item['recommendation_score'] = score
                recommendations.append(menu_item)

        return recommendations

    async def get_content_based_recommendations(self, user_prefs: Dict, limit: int):
        """Get recommendations based strongly on user's explicit content preferences"""
        favorite_cuisines = user_prefs.get('explicit_preferences', {}).get('favorite_cuisines', [])
        if not favorite_cuisines: # Use calculated if explicit not available
             favorite_cuisines = list(user_prefs.get('cuisine_preferences', {}).keys())
        spice_pref = user_prefs.get('explicit_preferences', {}).get('spice_preference', 'medium')
        dietary_restrictions = user_prefs.get('explicit_preferences', {}).get('dietary_restrictions', [])

        logging.info(f"Getting content-based recs. Prefs: Cuisines={favorite_cuisines}, Spice={spice_pref}, Diet={dietary_restrictions}")

        query_conditions = []
        base_query = {"available": True}

        # --- Cuisine Filtering ---
        if favorite_cuisines:
             # Find restaurants matching ANY of the favorite cuisines
            restaurants_cursor = self.db.restaurants.find({
                "cuisine": {"$in": favorite_cuisines},
                "is_active": True
            }, {"_id": 0}).limit(100) # Limit restaurant search scope
            restaurants = await restaurants_cursor.to_list(None)
            restaurant_ids = [r['id'] for r in restaurants]
            logging.info(f"Found {len(restaurant_ids)} restaurants matching cuisines: {favorite_cuisines}")

            if restaurant_ids:
                 # Prefer items from matching restaurants OR items explicitly tagged with the cuisine
                query_conditions.append({
                    "$or": [
                         {"restaurant_id": {"$in": restaurant_ids}},
                         {"tags": {"$in": favorite_cuisines}},
                         {"name": {"$regex": '|'.join(favorite_cuisines), "$options": "i"}} # Also check name
                    ]
                })
            else:
                 # If no restaurants match, broaden search to items tagged or named with the cuisine
                 query_conditions.append({
                      "$or": [
                           {"tags": {"$in": favorite_cuisines}},
                           {"name": {"$regex": '|'.join(favorite_cuisines), "$options": "i"}}
                      ]
                 })

        # --- Dietary Filtering ---
        if dietary_restrictions:
            diet_conditions = []
            if "Vegetarian" in dietary_restrictions:
                diet_conditions.append({"is_vegetarian": True})
            if "Halal" in dietary_restrictions:
                diet_conditions.append({"is_halal": True})
            # Add more conditions for Gluten-Free, Vegan, etc. if data exists
            if diet_conditions:
                query_conditions.append({"$and": diet_conditions}) # MUST meet all specified restrictions

        # --- Spice Preference (Used for scoring, not strict filtering initially) ---

        if query_conditions:
            query = {"$and": [base_query] + query_conditions}
        else:
            query = base_query # Fallback if no specific preferences to filter on

        logging.info(f"Content-based query: {query}")
        menu_items_cursor = self.db.menu_items.find(query, {"_id": 0}).limit(limit * 5) # Fetch more to score
        menu_items = await menu_items_cursor.to_list(None)
        logging.info(f"Found {len(menu_items)} potential content-based items.")

        # If initial query yielded too few results, broaden search slightly (e.g., remove strict dietary AND)
        if not menu_items and query_conditions:
             logging.info("Broadening content-based search...")
             broad_query = {"$and": [base_query] + query_conditions[:1]} # Use only first condition (likely cuisine)
             menu_items_cursor = self.db.menu_items.find(broad_query, {"_id": 0}).limit(limit * 3)
             menu_items = await menu_items_cursor.to_list(None)
             logging.info(f"Found {len(menu_items)} items after broadening search.")


        # Score items based on preferences
        scored_items = []
        for item in menu_items:
            score = await self.calculate_content_score(item, user_prefs) # Use modified scoring
            # Filter out items that *strongly* mismatch spice pref if possible
            if spice_pref == 'mild' and item.get('spice_level') in ['hot', 'very_hot'] and len(scored_items) > limit:
                 continue # Skip very spicy if user wants mild and we have enough options
            if spice_pref == 'very_hot' and item.get('spice_level') == 'mild' and len(scored_items) > limit:
                 continue # Skip mild if user wants very hot

            item['recommendation_score'] = score
            scored_items.append(item)

        # Sort by score and return top items
        scored_items.sort(key=lambda x: x['recommendation_score'], reverse=True)
        return scored_items[:limit]

    async def calculate_content_score(self, menu_item: Dict, user_prefs: Dict):
        """Calculate content-based score, giving more weight to explicit preferences"""
        score = 0.0
        favorite_cuisines = user_prefs.get('explicit_preferences', {}).get('favorite_cuisines', [])
        spice_pref = user_prefs.get('explicit_preferences', {}).get('spice_preference', 'medium')

        # Base score from popularity/rating
        score += menu_item.get('popularity_score', 0) * 0.5 # Reduced base weight
        score += menu_item.get('average_rating', 0) * 1.0   # Slightly increased rating weight

        # --- Stronger Preference Scoring ---
        # Cuisine match (Tags, Category, Name, Restaurant Cuisine)
        item_cuisines = set(menu_item.get('tags', []) + [menu_item.get('category', '')])
        restaurant = await self.db.restaurants.find_one({"id": menu_item['restaurant_id']}, {"_id": 0, "cuisine": 1})
        if restaurant and restaurant.get('cuisine'):
             item_cuisines.update(restaurant['cuisine'])

        matched_fav_cuisines = [c for c in favorite_cuisines if c in item_cuisines or c.lower() in menu_item.get('name', '').lower()]
        if matched_fav_cuisines:
             score += 20.0 # Significant boost for matching a favorite cuisine

        # Spice preference match
        item_spice = menu_item.get('spice_level', 'medium')
        if item_spice == spice_pref:
            score += 10.0 # Good boost for matching spice
        elif (spice_pref=='medium' and item_spice=='mild') or \
             (spice_pref=='hot' and item_spice=='medium') or \
             (spice_pref=='very_hot' and item_spice=='hot'):
             score += 3.0 # Small boost for adjacent spice level
        elif (spice_pref=='mild' and item_spice in ['hot', 'very_hot']) or \
             (spice_pref=='very_hot' and item_spice=='mild'):
             score -= 5.0 # Penalty for strong mismatch if preferences are strong

        # Category preference score (from history, lower weight than explicit)
        category_prefs = user_prefs.get('category_preferences', {})
        category = menu_item.get('category', '')
        score += category_prefs.get(category, 0) * 0.2 # Lower weight for historical category

        return max(0, score)

    async def get_popular_items(self, limit: int = 20):
        """Get popular menu items as fallback recommendations"""
        menu_items_cursor = self.db.menu_items.find(
            {"available": True},
            {"_id": 0},
            sort=[("popularity_score", -1), ("order_count", -1)]
        ).limit(limit)
        menu_items = await menu_items_cursor.to_list(None)
        
        for item in menu_items:
            item['recommendation_reason'] = 'Popular choice'
            item['recommendation_score'] = item.get('popularity_score', 0)
        
        return menu_items

# Initialize recommendation engine
recommendation_engine = RecommendationEngine(db)

# --- Enhanced Gemini Chat Integration ---
async def get_restaurant_recommendations_for_chat(message: str, user_context: Dict):
    """Get actual restaurant recommendations based on user preferences and message"""
    try:
        message_lower = message.lower()
        
        # Build query based on message content and user preferences
        query = {"is_active": True}
        
        # Enhanced cuisine keywords mapping
        cuisine_keywords = {
            'pakistani': ['Pakistani'], 'biryani': ['Pakistani'], 'karahi': ['Pakistani'],
            'chinese': ['Chinese'], 'chowmein': ['Chinese'], 'fried rice': ['Chinese'],
            'fast food': ['Fast Food'], 'burger': ['Fast Food'], 'pizza': ['Fast Food'], 
            'bbq': ['BBQ'], 'kebab': ['BBQ'], 'tikka': ['BBQ'],
            'dessert': ['Desserts'], 'sweet': ['Desserts'], 'ice cream': ['Desserts'],
            'japanese': ['Japanese'], 'sushi': ['Japanese'], 'thai': ['Thai'],
            'indian': ['Indian'], 'italian': ['Italian'], 'mexican': ['Mexican']
        }
        
        # Check for specific cuisine requests first
        matched_cuisines = []
        for keyword, cuisines in cuisine_keywords.items():
            if keyword in message_lower:
                matched_cuisines.extend(cuisines)
        
        # If user asks for general recommendations, use their preferences
        if any(word in message_lower for word in ['recommend', 'suggestion', 'hungry', 'food']) and not matched_cuisines:
            user_preferences = user_context.get('favorite_cuisines', [])
            if user_preferences:
                matched_cuisines = user_preferences[:3]  # Use top 3 preferences
        
        # Apply cuisine filter
        if matched_cuisines:
            query["cuisine"] = {"$in": matched_cuisines}
        
        # Get restaurants with variety
        restaurants_cursor = db.restaurants.find(query, {"_id": 0}).limit(4)
        restaurants = await restaurants_cursor.to_list(None)
        
        # If no results and we had specific cuisine, try broader search
        if not restaurants and matched_cuisines:
            # Try partial matches
            broader_query = {"is_active": True}
            restaurants_cursor = db.restaurants.find(broader_query, {"_id": 0}).limit(3)
            restaurants = await restaurants_cursor.to_list(None)
        
        return restaurants
    except Exception as e:
        logging.error(f"Error getting restaurant recommendations: {e}")
        return []

async def get_embedding_based_recommendations(self, user_id: str, limit: int = 10):
        """Get recommendations using embedding similarity"""
        try:
            # Get user's recent orders to understand preferences
            orders = await self.get_user_order_history(user_id, limit=10)
            
            if not orders:
                return []
            
            # Collect menu items from recent orders
            ordered_item_ids = []
            for order in orders:
                for item in order.get('items', []):
                    ordered_item_ids.append(item['menu_item_id'])
            
            # Get embeddings of items user has ordered
            ordered_items_cursor = self.db.menu_items.find(
                {
                    "id": {"$in": ordered_item_ids},
                    "embedding": {"$exists": True, "$ne": None}
                },
                {"_id": 0, "id": 1, "embedding": 1, "name": 1}
            )
            ordered_items = await ordered_items_cursor.to_list(None)
            
            if not ordered_items:
                logging.info("No ordered items with embeddings found")
                return []
            
            # Calculate average embedding of user's preferences
            embeddings = [item['embedding'] for item in ordered_items if item.get('embedding')]
            if not embeddings:
                return []
            
            # Average the embeddings
            avg_embedding = np.mean(embeddings, axis=0).tolist()
            
            # Get all available items with embeddings (excluding already ordered)
            candidate_items_cursor = self.db.menu_items.find(
                {
                    "id": {"$nin": ordered_item_ids},
                    "available": True,
                    "embedding": {"$exists": True, "$ne": None}
                },
                {"_id": 0}
            ).limit(200)  # Limit candidates for performance
            
            candidate_items = await candidate_items_cursor.to_list(None)
            
            # Calculate similarity scores
            scored_items = []
            for item in candidate_items:
                if not item.get('embedding'):
                    continue
                
                similarity = cosine_similarity_vectors(avg_embedding, item['embedding'])
                
                # Combine similarity with other factors
                score = similarity * 10  # Scale up similarity
                score += item.get('average_rating', 0) * 0.5
                score += item.get('popularity_score', 0) * 0.3
                
                item['embedding_similarity'] = round(similarity, 3)
                item['recommendation_score'] = score
                
                # Enrich with restaurant info
                restaurant = await self.db.restaurants.find_one(
                    {"id": item['restaurant_id']}, 
                    {"_id": 0}
                )
                if restaurant:
                    item["restaurant_name"] = restaurant["name"]
                    item["restaurant_rating"] = restaurant["rating"]
                    item["delivery_time"] = restaurant["delivery_time"]
                    item["restaurant_cuisine"] = restaurant.get("cuisine", "")
                
                scored_items.append(item)
            
            # Sort by score
            scored_items.sort(key=lambda x: x['recommendation_score'], reverse=True)
            
            logging.info(f"Found {len(scored_items)} embedding-based recommendations")
            return scored_items[:limit]
            
        except Exception as e:
            logging.error(f"Error in embedding-based recommendations: {e}")
            import traceback
            logging.error(traceback.format_exc())
            return []
async def analyze_user_order_history(user_id: str, days: int = 30):
    """
    Analyze user's order history for the past month to identify patterns
    Returns cuisine frequency, favorite items, and recommendations
    """
    try:
        # Get orders from the past month
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        orders_cursor = db.orders.find(
            {
                "user_id": user_id,
                "created_at": {"$gte": cutoff_date}
            },
            {"_id": 0}
        ).sort([("created_at", -1)])
        
        orders = await orders_cursor.to_list(None)
        
        if not orders:
            return {
                "has_history": False,
                "total_orders": 0,
                "cuisine_frequency": {},
                "favorite_items": [],
                "dominant_cuisine": None,
                "tried_cuisines": []
            }
        
        # Track cuisines and items
        cuisine_count = {}
        item_frequency = {}
        all_cuisines_tried = set()
        
        for order in orders:
            restaurant = await db.restaurants.find_one(
                {"id": order["restaurant_id"]}, 
                {"_id": 0, "cuisine": 1, "name": 1}
            )
            
            if restaurant:
                # Count cuisines
                for cuisine in restaurant.get("cuisine", []):
                    cuisine_count[cuisine] = cuisine_count.get(cuisine, 0) + 1
                    all_cuisines_tried.add(cuisine)
            
            # Track individual items
            for item in order.get("items", []):
                menu_item = await db.menu_items.find_one(
                    {"id": item["menu_item_id"]}, 
                    {"_id": 0}
                )
                
                if menu_item:
                    item_key = menu_item["id"]
                    if item_key not in item_frequency:
                        item_frequency[item_key] = {
                            "count": 0,
                            "item": menu_item,
                            "restaurant_name": restaurant.get("name", "Unknown") if restaurant else "Unknown"
                        }
                    item_frequency[item_key]["count"] += item["quantity"]
        
        # Find dominant cuisine (ordered 3+ times)
        dominant_cuisines = [
            cuisine for cuisine, count in cuisine_count.items() 
            if count >= 3
        ]
        
        # Sort favorite items by frequency
        favorite_items = sorted(
            item_frequency.values(), 
            key=lambda x: x["count"], 
            reverse=True
        )[:5]  # Top 5 favorite items
        
        return {
            "has_history": True,
            "total_orders": len(orders),
            "cuisine_frequency": cuisine_count,
            "favorite_items": favorite_items,
            "dominant_cuisines": dominant_cuisines,
            "tried_cuisines": list(all_cuisines_tried),
            "most_ordered_cuisine": max(cuisine_count.items(), key=lambda x: x[1])[0] if cuisine_count else None
        }
        
    except Exception as e:
        logging.error(f"Error analyzing order history: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return {
            "has_history": False,
            "total_orders": 0,
            "cuisine_frequency": {},
            "favorite_items": [],
            "dominant_cuisines": [],
            "tried_cuisines": []
        }


async def get_new_recommendations_based_on_history(user_id: str, order_history: Dict, limit: int = 3):
    """
    Get recommendations for NEW items/cuisines the user hasn't tried much
    Based on their taste profile from order history
    """
    try:
        tried_cuisines = order_history.get("tried_cuisines", [])
        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        
        if not user:
            return []
        
        # Get all available cuisines
        all_cuisines = await db.restaurants.distinct("cuisine", {"is_active": True})
        all_cuisines_flat = []
        for cuisine_list in all_cuisines:
            if isinstance(cuisine_list, list):
                all_cuisines_flat.extend(cuisine_list)
            else:
                all_cuisines_flat.append(cuisine_list)
        
        # Find cuisines they haven't tried or tried minimally
        untried_cuisines = [c for c in set(all_cuisines_flat) if c not in tried_cuisines]
        rarely_tried = [
            cuisine for cuisine, count in order_history.get("cuisine_frequency", {}).items() 
            if count < 3
        ]
        
        # Prioritize untried cuisines, then rarely tried
        target_cuisines = untried_cuisines[:2] + rarely_tried[:1] if untried_cuisines else rarely_tried[:3]
        
        if not target_cuisines:
            # Fallback: suggest popular items from less-ordered cuisines
            target_cuisines = list(set(all_cuisines_flat) - set(order_history.get("dominant_cuisines", [])))[:3]
        
        # Get items from these cuisines, matching user's spice preference
        new_items = []
        spice_pref = user.get("spice_preference", "medium")
        
        for cuisine in target_cuisines:
            # Find restaurants with this cuisine
            restaurants_cursor = db.restaurants.find({
                "cuisine": cuisine,
                "is_active": True
            }, {"_id": 0}).limit(2)
            
            restaurants = await restaurants_cursor.to_list(None)
            restaurant_ids = [r["id"] for r in restaurants]
            
            if restaurant_ids:
                # Get highly rated items from these restaurants
                items_cursor = db.menu_items.find({
                    "restaurant_id": {"$in": restaurant_ids},
                    "available": True,
                    "average_rating": {"$gte": 3.5}
                }, {"_id": 0}).limit(2)
                
                items = await items_cursor.to_list(None)
                
                for item in items:
                    restaurant = await db.restaurants.find_one(
                        {"id": item["restaurant_id"]}, 
                        {"_id": 0}
                    )
                    
                    if restaurant:
                        item["restaurant_name"] = restaurant["name"]
                        item["restaurant_rating"] = restaurant["rating"]
                        item["delivery_time"] = restaurant["delivery_time"]
                        item["restaurant_cuisine"] = restaurant.get("cuisine", [])
                        item["recommendation_reason"] = f"New {cuisine} option for you!"
                        
                        # Boost score if spice level matches
                        score = item.get("average_rating", 0) * 2 + item.get("popularity_score", 0)
                        if item.get("spice_level") == spice_pref:
                            score += 5
                        
                        item["preference_score"] = score
                        new_items.append(item)
        
        # Sort by score and return top items
        new_items = deduplicate_items_by_name(new_items)  # Add this line
        new_items.sort(key=lambda x: x.get("preference_score", 0), reverse=True) 
        return new_items[:limit]
        
    except Exception as e:
        logging.error(f"Error getting new recommendations: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return []


async def get_reorder_recommendations(order_history: Dict, limit: int = 3):
    """
    Get reorder recommendations from user's favorite items
    """
    try:
        favorite_items = order_history.get("favorite_items", [])
        
        if not favorite_items:
            return []
        
        reorder_items = []
        for fav in favorite_items[:limit]:
            item = fav["item"]
            
            # Check if item is still available
            current_item = await db.menu_items.find_one(
                {"id": item["id"], "available": True}, 
                {"_id": 0}
            )
            
            if current_item:
                restaurant = await db.restaurants.find_one(
                    {"id": current_item["restaurant_id"]}, 
                    {"_id": 0}
                )
                
                if restaurant and restaurant.get("is_active"):
                    current_item["restaurant_name"] = restaurant["name"]
                    current_item["restaurant_rating"] = restaurant["rating"]
                    current_item["delivery_time"] = restaurant["delivery_time"]
                    current_item["restaurant_cuisine"] = restaurant.get("cuisine", [])
                    current_item["order_count_history"] = fav["count"]
                    current_item["recommendation_reason"] = f"You've ordered this {fav['count']} times!"
                    reorder_items.append(current_item)
        
        return reorder_items
        
    except Exception as e:
        logging.error(f"Error getting reorder recommendations: {e}")
        return []
async def process_with_gemini_enhanced(
    message: str, 
    user_context: Dict, 
    order_history: Dict,
    reorder_items: List = [],
    new_items: List = [],
    is_new_request: bool = False
):
    """
    Enhanced Gemini processing with order history context
    """
    username = user_context.get('username', 'User')
    lang = detect_language(message)
    response_instruction = f"Respond CONCISELY in {lang}." if lang == 'ur' else "Respond CONCISELY in English."
    
    has_order_history = order_history.get("has_history", False)
    has_reorder_items = len(reorder_items) > 0
    has_new_items = len(new_items) > 0
    
    # Build order history context ONLY if user actually has history
    history_context = ""
    if has_order_history and has_reorder_items:
        total_orders = order_history.get("total_orders", 0)
        most_ordered = order_history.get("most_ordered_cuisine", "")
        dominant_cuisines = order_history.get("dominant_cuisines", [])
        
        if dominant_cuisines:
            history_context = f"\n\nOrder History: {username} has {total_orders} orders in the past month. "
            history_context += f"Frequently orders: {', '.join(dominant_cuisines)}. "
            
            if most_ordered:
                cuisine_count = order_history.get("cuisine_frequency", {}).get(most_ordered, 0)
                history_context += f"Most loved cuisine: {most_ordered} ({cuisine_count} times). "
    
    # Build recommendations context
    recs_context = ""
    
    if has_reorder_items:
        recs_context += "\n\n**PAST FAVORITES (For Reorder)**:\n"
        for idx, item in enumerate(reorder_items[:3], 1):
            recs_context += f"{idx}. {item.get('name')} from {item.get('restaurant_name')} - PKR {item.get('price')} "
            recs_context += f"(Ordered {item.get('order_count_history')} times)\n"
    
    if has_new_items:
        recs_context += "\n**RECOMMENDATIONS FOR YOU**:\n"
        for idx, item in enumerate(new_items[:3], 1):
            cuisines = ', '.join(item.get('restaurant_cuisine', []))
            recs_context += f"{idx}. {item.get('name')} from {item.get('restaurant_name')} ({cuisines}) - PKR {item.get('price')}\n"
    
    # Construct prompt based on whether user has order history
    if not has_order_history:
        # NEW USER - No order history, don't mention past orders
        prompt = f"""You are a friendly food ordering assistant for Voice Guide in Karachi.

User: {username}
Preferences: {', '.join(user_context.get('favorite_cuisines', []))}
Spice: {user_context.get('spice_preference', 'medium')}

User asked: "{message}"

{recs_context}

Task: This is a NEW USER with no order history. Present the recommendations based on their stated preferences. DO NOT mention any past orders or favorites. Keep response friendly and inviting, 2-3 sentences. {response_instruction}"""
    elif is_new_request and has_reorder_items:
        # User wants something NEW but has order history
        prompt = f"""You are a friendly food ordering assistant for Voice Guide in Karachi.

User: {username}
Preferences: {', '.join(user_context.get('favorite_cuisines', []))}
Spice: {user_context.get('spice_preference', 'medium')}
{history_context}

User asked: "{message}"

{recs_context}

Task: The user wants something NEW/UNIQUE. Briefly acknowledge their usual favorites if available, then enthusiastically present the new recommendations. Keep it friendly and encouraging, 2-3 sentences. {response_instruction}"""
    elif has_reorder_items:
        # User has history and we have reorder items to show
        prompt = f"""You are a friendly food ordering assistant for Voice Guide in Karachi.

User: {username}
Preferences: {', '.join(user_context.get('favorite_cuisines', []))}
{history_context}

User asked: "{message}"

{recs_context}

Task: Present their favorite items for reorder (mention how many times they've ordered). Then suggest new options if available. Keep response to 2-3 sentences total. {response_instruction}"""
    else:
        # Has history but no specific reorder items available
        prompt = f"""You are a friendly food ordering assistant for Voice Guide in Karachi.

User: {username}
Preferences: {', '.join(user_context.get('favorite_cuisines', []))}

User asked: "{message}"

{recs_context}

Task: Present the available recommendations in a friendly way. Keep response to 2-3 sentences. {response_instruction}"""
    
    try:
        logging.info(f"Sending enhanced prompt to Gemini (has_history={has_order_history}, has_reorder={has_reorder_items}, has_new={has_new_items}, is_new_request={is_new_request})")
        
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
        
        response = await asyncio.to_thread(
            model.generate_content,
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=250
            ),
            safety_settings=safety_settings
        )
        
        if not response.parts:
            # Fallback response - only mention order history if it exists
            if has_reorder_items:
                fallback = f"Your favorites: {reorder_items[0].get('name')} "
                fallback += f"(ordered {reorder_items[0].get('order_count_history')} times!). "
            else:
                fallback = "Here are some recommendations for you: "
            
            if has_new_items:
                if has_reorder_items:
                    fallback += f"Or try something new: {new_items[0].get('name')} from {new_items[0].get('restaurant_name')}!"
                else:
                    fallback += f"{new_items[0].get('name')} from {new_items[0].get('restaurant_name')}!"
            
            return fallback
        
        generated_text = response.text.strip()
        logging.info(f"Gemini enhanced response: {generated_text}")
        
        # Return appropriate default if empty
        if not generated_text:
            if has_order_history:
                return "Would you like to reorder your favorites or try something new?"
            else:
                return "What would you like to order today?"
        
        return generated_text
        
    except Exception as e:
        logging.error(f"Error calling Gemini: {e}")
        
        # Smart fallback - only mention history if it exists
        if has_reorder_items:
            return f"Your favorite: {reorder_items[0].get('name')} (PKR {reorder_items[0].get('price')}). Want to reorder?"
        elif has_new_items:
            return f"How about trying {new_items[0].get('name')} from {new_items[0].get('restaurant_name')}?"
        return "What would you like to order today?"
        

async def process_with_gemini(message: str, user_context: Dict = None, recommended_items: List = [], restaurants: List = []):
    """Process message with Gemini, making it more dynamic and language-aware"""

    username = user_context.get('username', 'User')
    lang = detect_language(message)
    response_instruction = f"Respond CONCISELY in {lang}." if lang == 'ur' else "Respond CONCISELY in English."

    # Build context string for Gemini
    context_parts = [f"User: {username}"]
    if user_context.get('favorite_cuisines'):
        context_parts.append(f"Prefers: {', '.join(user_context['favorite_cuisines'])}")
    if user_context.get('spice_preference'):
        context_parts.append(f"Spice Level: {user_context['spice_preference']}")
    if user_context.get('dietary_restrictions'):
        context_parts.append(f"Dietary Needs: {', '.join(user_context['dietary_restrictions'])}")

    gemini_context = ". ".join(context_parts)

    # Prepare recommendations string if available - simplified to avoid safety blocks
    recs_string = ""
    has_recommendations = False
    if recommended_items:
        has_recommendations = True
        items_list = []
        for item in recommended_items[:3]:
             items_list.append(f"{item.get('name', 'Item')} from {item.get('restaurant_name', 'Restaurant')} for PKR {item.get('price', 0)}")
        recs_string = ", ".join(items_list)
    elif restaurants:
        has_recommendations = True
        rest_list = []
        for r in restaurants[:3]:
             rest_list.append(f"{r.get('name', 'Restaurant')} ({', '.join(r.get('cuisine',[]))})")
        recs_string = ", ".join(rest_list)
    
    # Construct a cleaner prompt
    if has_recommendations:
        prompt = f"""You are a friendly food ordering assistant for Voice Guide in Karachi.

User: {username}
Preferences: {', '.join(user_context.get('favorite_cuisines', []))}
Spice: {user_context.get('spice_preference', 'medium')}
Dietary: {', '.join(user_context.get('dietary_restrictions', []))}

User asked: "{message}"

Available items: {recs_string}

Task: Briefly mention these items as recommendations in a friendly way. Keep it to 1-2 sentences. {response_instruction}"""
    else:
        prompt = f"""You are a friendly food ordering assistant for Voice Guide in Karachi.

User: {username}
Preferences: {', '.join(user_context.get('favorite_cuisines', []))}

User asked: "{message}"

Task: No specific items found. Suggest popular options based on their preferences or suggest Biryani or Burgers. Keep it to 1-2 sentences. {response_instruction}"""

    try:
        logging.info(f"Sending prompt to Gemini (lang={lang}, has_recs={has_recommendations})")
        logging.debug(f"Full prompt: {prompt[:500]}...") # Log first 500 chars
        
        model = genai.GenerativeModel('gemini-2.0-flash-exp')  # Using a more stable model
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
        response = await asyncio.to_thread(
             model.generate_content,
             prompt,
             generation_config=genai.types.GenerationConfig(
                  temperature=0.7,
                  max_output_tokens=150
             ),
             safety_settings=safety_settings
        )
        
        # Handle potential safety blocks or empty responses
        if not response.parts:
             block_reason = "Unknown"
             if hasattr(response, 'prompt_feedback'):
                 block_reason = str(response.prompt_feedback.block_reason) if response.prompt_feedback.block_reason else "Unknown"
                 logging.error(f"Gemini blocked response. Reason: {block_reason}")
                 logging.error(f"Safety ratings: {response.prompt_feedback.safety_ratings}")
             
             # Provide a helpful fallback with actual recommendations if available
             if has_recommendations and recommended_items:
                 fallback = "Here are some recommendations for you: "
                 items = [f"{item.get('name')} from {item.get('restaurant_name')} (PKR {item.get('price')})" 
                         for item in recommended_items[:3]]
                 return fallback + ", ".join(items)
             elif lang == 'ur':
                  return "یہاں کچھ مشہور اختیارات ہیں: بریانی، برگر، یا پیزا۔ کیا آپ کچھ آرڈر کرنا چاہیں گے?"
             else:
                  return "Here are some popular options: Biryani, Burgers, or Pizza. Would you like to order something?"
        
        generated_text = response.text.strip()
        logging.info(f"Gemini response: {generated_text}")
        
        if not generated_text:
             logging.warning("Gemini returned empty text.")
             if has_recommendations and recommended_items:
                 fallback = "Check out these items: "
                 items = [item.get('name') for item in recommended_items[:3]]
                 return fallback + ", ".join(items)
             elif lang == 'ur':
                 return "کیا آپ بریانی یا برگر آزمانا چاہیں گے؟"
             else:
                 return "Would you like to try Biryani or a Burger?"
                 
        return generated_text

    except Exception as e:
        logging.error(f"Error calling Gemini: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        # Better fallback with actual recommendations
        if has_recommendations and recommended_items:
            fallback = "I found these for you: "
            items = [f"{item.get('name')} (PKR {item.get('price')})" for item in recommended_items[:2]]
            return fallback + ", ".join(items)
        elif lang == 'ur':
            return "کچھ غلط ہو گیا۔ کیا آپ بریانی یا برگر آزمانا چاہیں گے؟"
        else:
            return "Something went wrong. Would you like to try Biryani or Burgers?"

# --- API Routes ---

# Authentication Routes
@api_router.post("/auth/register")
async def register_user(user_data: UserCreate):
    # Check if user exists
    existing_user = await db.users.find_one({"email": user_data.email}, {"_id": 0})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    hashed_password = hash_password(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hashed_password,
        phone=user_data.phone,
        preferences_set=False
    )
    
    await db.users.insert_one(new_user.dict())
    
    # Create access token
    access_token = create_access_token(data={"sub": new_user.id})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": new_user.id,
            "username": new_user.username,
            "email": new_user.email,
            "preferences_set": new_user.preferences_set
        }
    }

@api_router.post("/auth/login")
async def login_user(user_data: UserLogin):
    user = await db.users.find_one({"email": user_data.email}, {"_id": 0})
    if not user or not verify_password(user_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    access_token = create_access_token(data={"sub": user["id"]})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "preferences_set": user.get("preferences_set", False)
        }
    }

# User Routes
@api_router.get("/user/profile")
async def get_user_profile(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "preferences": current_user.preferences,
        "dietary_restrictions": current_user.dietary_restrictions,
        "favorite_cuisines": current_user.favorite_cuisines,
        "spice_preference": current_user.spice_preference,
        "addresses": current_user.addresses,
        "default_address_id": current_user.default_address_id,
        "phone": current_user.phone,
        "preferences_set": current_user.preferences_set
    }

@api_router.post("/user/setup-preferences")
async def setup_user_preferences(
    preferences: PreferencesSetup,
    current_user: User = Depends(get_current_user)
):
    """Setup preferences for new users"""
    update_data = {
        "favorite_cuisines": preferences.favorite_cuisines,
        "dietary_restrictions": preferences.dietary_restrictions,
        "spice_preference": preferences.spice_preference,
        "preferences_set": True,
        "updated_at": datetime.now(timezone.utc)
    }
    
    await db.users.update_one(
        {"id": current_user.id},
        {"$set": update_data}
    )
    
    return {"message": "Preferences setup completed successfully"}

@api_router.put("/user/preferences")
async def update_user_preferences(
    preferences: PreferenceUpdate,
    current_user: User = Depends(get_current_user)
):
    update_data = {}
    if preferences.favorite_cuisines is not None:
        update_data["favorite_cuisines"] = preferences.favorite_cuisines
    if preferences.dietary_restrictions is not None:
        update_data["dietary_restrictions"] = preferences.dietary_restrictions
    if preferences.spice_preference is not None:
        update_data["spice_preference"] = preferences.spice_preference
    
    update_data["updated_at"] = datetime.now(timezone.utc)
    
    await db.users.update_one(
        {"id": current_user.id},
        {"$set": update_data}
    )
    
    return {"message": "Preferences updated successfully"}

# Address Management
@api_router.get("/user/addresses")
async def get_user_addresses(current_user: User = Depends(get_current_user)):
    return {"addresses": current_user.addresses}

@api_router.post("/user/addresses")
async def add_user_address(
    address: Address,
    current_user: User = Depends(get_current_user)
):
    address_dict = address.dict()
    
    # If this is the first address or marked as default, make it default
    if not current_user.addresses or address.is_default:
        address_dict["is_default"] = True
        # Update user's default address
        await db.users.update_one(
            {"id": current_user.id},
            {
                "$push": {"addresses": address_dict},
                "$set": {"default_address_id": address.id}
            }
        )
    else:
        await db.users.update_one(
            {"id": current_user.id},
            {"$push": {"addresses": address_dict}}
        )
    
    return {"message": "Address added successfully", "address_id": address.id}

@api_router.get("/areas")
async def get_karachi_areas():
    """Get all Karachi areas organized by district"""
    return {"areas": KARACHI_AREAS}

# Restaurant and Menu Routes
@api_router.get("/restaurants")
async def get_restaurants(page: int = 1, limit: int = 10, cuisine: str = None):
    skip = (page - 1) * limit
    query = {"is_active": True}
    
    if cuisine:
        query["cuisine"] = {"$in": [cuisine]}
    
    restaurants_cursor = db.restaurants.find(query, {"_id": 0}).skip(skip).limit(limit)
    restaurants = await restaurants_cursor.to_list(None)
    total = await db.restaurants.count_documents(query)
    
    return {
        "restaurants": restaurants,
        "total": total,
        "page": page,
        "limit": limit,
        "has_more": skip + limit < total
    }

@api_router.get("/restaurants/{restaurant_id}")
async def get_restaurant_details(restaurant_id: str):
    restaurant = await db.restaurants.find_one({"id": restaurant_id}, {"_id": 0})
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    
    return {"restaurant": restaurant}

@api_router.get("/restaurants/{restaurant_id}/menu")
async def get_restaurant_menu(restaurant_id: str, category: str = None):
    query = {"restaurant_id": restaurant_id, "available": True}
    
    if category:
        query["category"] = category
    
    menu_items_cursor = db.menu_items.find(query, {"_id": 0})
    menu_items = await menu_items_cursor.to_list(None)
    return {"menu_items": menu_items}

@api_router.get("/cuisines")
async def get_available_cuisines():
    # Get distinct cuisines from restaurants
    cuisines = await db.restaurants.distinct("cuisine", {"is_active": True})
    # Flatten the list since cuisine is an array field
    all_cuisines = []
    for cuisine_list in cuisines:
        if isinstance(cuisine_list, list):
            all_cuisines.extend(cuisine_list)
        else:
            all_cuisines.append(cuisine_list)
    
    # Remove duplicates and sort
    unique_cuisines = sorted(list(set(all_cuisines)))
    return {"cuisines": unique_cuisines}

# Cart Management Routes
@api_router.get("/cart")
async def get_user_cart(current_user: User = Depends(get_current_user)):
    cart_items_cursor = db.cart_items.find({"user_id": current_user.id}, {"_id": 0})
    cart_items = await cart_items_cursor.to_list(None)
    
    # Enrich cart items with menu item details
    enriched_items = []
    total_amount = 0
    restaurant_id = None
    
    for item in cart_items:
        menu_item = await db.menu_items.find_one({"id": item["menu_item_id"]}, {"_id": 0})
        restaurant = await db.restaurants.find_one({"id": item["restaurant_id"]}, {"_id": 0})
        
        if menu_item and restaurant:
            item_total = menu_item["price"] * item["quantity"]
            total_amount += item_total
            restaurant_id = restaurant["id"]
            
            enriched_items.append({
                **item,
                "menu_item": menu_item,
                "restaurant": restaurant,
                "item_total": item_total
            })
    
    return {
        "items": enriched_items,
        "total_amount": total_amount,
        "item_count": len(enriched_items),
        "restaurant_id": restaurant_id
    }

@api_router.post("/cart/add")
async def add_to_cart(
    cart_item: CartItemAdd,
    current_user: User = Depends(get_current_user)
):
    # Check if menu item exists
    menu_item = await db.menu_items.find_one({"id": cart_item.menu_item_id}, {"_id": 0})
    if not menu_item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    
    # Check if restaurant is active
    restaurant = await db.restaurants.find_one({"id": cart_item.restaurant_id}, {"_id": 0})
    if not restaurant or not restaurant["is_active"]:
        raise HTTPException(status_code=400, detail="Restaurant is not available")
    
    # Check if user already has items from a different restaurant
    existing_cart = await db.cart_items.find_one({"user_id": current_user.id}, {"_id": 0})
    if existing_cart and existing_cart["restaurant_id"] != cart_item.restaurant_id:
        # Clear cart and add new item from different restaurant
        await db.cart_items.delete_many({"user_id": current_user.id})
    
    # Check if item already exists in cart
    existing_item = await db.cart_items.find_one({
        "user_id": current_user.id,
        "menu_item_id": cart_item.menu_item_id
    }, {"_id": 0})
    
    if existing_item:
        # Update quantity
        new_quantity = existing_item["quantity"] + cart_item.quantity
        await db.cart_items.update_one(
            {"id": existing_item["id"]},
            {"$set": {"quantity": new_quantity, "special_instructions": cart_item.special_instructions}}
        )
        return {"message": "Cart item updated successfully"}
    else:
        # Add new item to cart
        new_cart_item = CartItem(
            user_id=current_user.id,
            menu_item_id=cart_item.menu_item_id,
            restaurant_id=cart_item.restaurant_id,
            quantity=cart_item.quantity,
            special_instructions=cart_item.special_instructions
        )
        await db.cart_items.insert_one(new_cart_item.dict())
        return {"message": "Item added to cart successfully"}

@api_router.put("/cart/{item_id}")
async def update_cart_item(
    item_id: str,
    quantity: int,
    current_user: User = Depends(get_current_user)
):
    if quantity <= 0:
        await db.cart_items.delete_one({"id": item_id, "user_id": current_user.id})
        return {"message": "Item removed from cart"}
    else:
        await db.cart_items.update_one(
            {"id": item_id, "user_id": current_user.id},
            {"$set": {"quantity": quantity}}
        )
        return {"message": "Cart item updated"}

@api_router.delete("/cart/{item_id}")
async def remove_from_cart(
    item_id: str,
    current_user: User = Depends(get_current_user)
):
    result = await db.cart_items.delete_one({"id": item_id, "user_id": current_user.id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Cart item not found")
    
    return {"message": "Item removed from cart successfully"}

@api_router.delete("/cart/clear")
async def clear_cart(current_user: User = Depends(get_current_user)):
    await db.cart_items.delete_many({"user_id": current_user.id})
    return {"message": "Cart cleared successfully"}

# Order Management Routes
@api_router.post("/orders/checkout")
async def checkout_order(
    checkout_request: CheckoutRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    # Get cart items
    cart_items_cursor = db.cart_items.find({"user_id": current_user.id}, {"_id": 0})
    cart_items = await cart_items_cursor.to_list(None)
    
    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")
    
    # Get user address
    user_address = None
    for address in current_user.addresses:
        if address["id"] == checkout_request.address_id:
            user_address = address
            break
    
    if not user_address:
        raise HTTPException(status_code=404, detail="Address not found")
    
    # Calculate order details
    order_items = []
    subtotal = 0
    restaurant_id = None
    
    for cart_item in cart_items:
        menu_item = await db.menu_items.find_one({"id": cart_item["menu_item_id"]}, {"_id": 0})
        if menu_item:
            item_total = menu_item["price"] * cart_item["quantity"]
            subtotal += item_total
            restaurant_id = cart_item["restaurant_id"]
            
            order_items.append(OrderItem(
                menu_item_id=cart_item["menu_item_id"],
                quantity=cart_item["quantity"],
                price=menu_item["price"],
                special_instructions=cart_item["special_instructions"]
            ))
    
    # Get restaurant for delivery fee
    restaurant = await db.restaurants.find_one({"id": restaurant_id}, {"_id": 0})
    delivery_fee = restaurant["delivery_fee"] if restaurant else 50
    tax = subtotal * 0.05  # 5% tax
    total = subtotal + delivery_fee + tax
    
    # Create order
    order_number = generate_order_number()
    order_dict = {
        "id": str(uuid.uuid4()),
        "order_number": order_number,
        "user_id": current_user.id,
        "restaurant_id": restaurant_id,
        "items": [item.dict() for item in order_items],
        "delivery_address": user_address,
        "payment_method": checkout_request.payment_method,
        "payment_status": "pending" if checkout_request.payment_method == "easypaisa" else "cash_on_delivery",
        "order_status": "placed",
        "pricing": {
            "subtotal": float(subtotal),
            "delivery_fee": float(delivery_fee),
            "tax": float(tax),
            "total": float(total)
        },
        "estimated_delivery_time": datetime.now(timezone.utc) + timedelta(minutes=35),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    # Save order to database
    result = await db.orders.insert_one(order_dict)
    
    if not result.inserted_id:
        raise HTTPException(status_code=500, detail="Failed to create order")
    
    # Clear cart
    await db.cart_items.delete_many({"user_id": current_user.id})
    
    # Prepare order items for email
    email_items = []
    for order_item in order_items:
        menu_item = await db.menu_items.find_one({"id": order_item.menu_item_id}, {"_id": 0})
        if menu_item:
            email_items.append({
                "name": menu_item["name"],
                "quantity": order_item.quantity,
                "price": order_item.price,
                "special_instructions": order_item.special_instructions
            })
    
    # Send order confirmation email in background
    background_tasks.add_task(
        send_order_confirmation_email,
        current_user.email,
        current_user.username,
        order_dict,
        email_items
    )
    
    return {
        "message": "Order placed successfully",
        "order": {
            "id": order_dict["id"],
            "order_number": order_dict["order_number"],
            "total": total,
            "status": order_dict["order_status"],
            "estimated_delivery_time": order_dict["estimated_delivery_time"]
        }
    }

@api_router.get("/orders")
async def get_user_orders(
    page: int = 1,
    limit: int = 10,
    current_user: User = Depends(get_current_user)
):
    skip = (page - 1) * limit
    orders_cursor = db.orders.find(
        {"user_id": current_user.id},
        {"_id": 0}
    ).sort([("created_at", -1)]).skip(skip).limit(limit)
    orders = await orders_cursor.to_list(None)
    
    # Enrich orders with restaurant and menu item details
    enriched_orders = []
    for order in orders:
        restaurant = await db.restaurants.find_one({"id": order["restaurant_id"]}, {"_id": 0})
        
        # Enrich order items
        enriched_items = []
        for item in order["items"]:
            menu_item = await db.menu_items.find_one({"id": item["menu_item_id"]}, {"_id": 0})
            if menu_item:
                enriched_items.append({
                    **item,
                    "menu_item": menu_item
                })
        
        enriched_orders.append({
            **order,
            "restaurant": restaurant,
            "items": enriched_items
        })
    
    total = await db.orders.count_documents({"user_id": current_user.id})
    
    return {
        "orders": enriched_orders,
        "total": total,
        "page": page,
        "limit": limit
    }

@api_router.post("/orders/{order_id}/reorder")
async def reorder(
    order_id: str,
    current_user: User = Depends(get_current_user)
):
    # Get original order
    original_order = await db.orders.find_one(
        {"id": order_id, "user_id": current_user.id}, 
        {"_id": 0}
    )
    
    if not original_order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Clear current cart
    await db.cart_items.delete_many({"user_id": current_user.id})
    
    # Add items from original order to cart
    for item in original_order["items"]:
        # Check if menu item is still available
        menu_item = await db.menu_items.find_one(
            {"id": item["menu_item_id"], "available": True}, 
            {"_id": 0}
        )
        
        if menu_item:
            cart_item = CartItem(
                user_id=current_user.id,
                menu_item_id=item["menu_item_id"],
                restaurant_id=original_order["restaurant_id"],
                quantity=item["quantity"],
                special_instructions=item.get("special_instructions", "")
            )
            await db.cart_items.insert_one(cart_item.dict())
    
    return {"message": "Items added to cart successfully. You can now proceed to checkout."}

# Recommendation Routes
@api_router.get("/recommendations")
async def get_user_recommendations(
    limit: int = 20,
    current_user: User = Depends(get_current_user)
):
    recommendations = await recommendation_engine.get_recommendations(current_user.id, limit)
    return {"recommendations": recommendations}

# Chat Routes
@api_router.post("/chat")
async def chat_with_assistant(
    chat_request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    # Get user context
    user_context = {
        "user_id": current_user.id,
        "username": current_user.username,
        "favorite_cuisines": current_user.favorite_cuisines,
        "dietary_restrictions": current_user.dietary_restrictions,
        "spice_preference": current_user.spice_preference,
        "preferences_set": current_user.preferences_set,
        "default_address": None,
        "explicit_preferences": {
            "favorite_cuisines": current_user.favorite_cuisines,
            "dietary_restrictions": current_user.dietary_restrictions,
            "spice_preference": current_user.spice_preference,
        }
    }
    
    for address in current_user.addresses:
        if address.get('is_default'):
            user_context['default_address'] = address
            break

    message_lower = chat_request.message.lower()
    lang = detect_language(chat_request.message)

    # Analyze order history (past 30 days)
    order_history = await analyze_user_order_history(current_user.id, days=30)
    
    # Detect intent
    food_keywords = ['food', 'hungry', 'eat', 'order', 'restaurant', 'recommend', 'suggestion', 'suggest', 'want', 'show', 'mood for']
    new_keywords = ['new', 'different', 'unique', 'change', 'something else', 'try something', 'never tried', 'haven\'t tried']
    
    is_food_request = any(keyword in message_lower for keyword in food_keywords)
    is_new_request = any(keyword in message_lower for keyword in new_keywords)
    is_order_intent = any(phrase in message_lower for phrase in ['order this', 'order that', 'place order', 'yes order', 'get this'])

    reorder_items = []
    new_items = []
    show_order_card = False

    # Get recommendations based on order history
    if is_food_request:
        logging.info(f"Food request detected. Has history: {order_history.get('has_history')}, Is new request: {is_new_request}")
        
        # Always get reorder recommendations if they have history
        if order_history.get("has_history"):
            reorder_items = await get_reorder_recommendations(order_history, limit=3)
            logging.info(f"Found {len(reorder_items)} reorder items")
        
        # Get new recommendations if they ask for something new OR if getting general recommendations
        if is_new_request or (is_food_request and order_history.get("has_history")):
            new_items = await get_new_recommendations_based_on_history(
                current_user.id, 
                order_history, 
                limit=3
            )
            logging.info(f"Found {len(new_items)} new recommendation items")
        
        # If no history, use the existing cuisine-based search
        if not order_history.get("has_history"):
            # Use existing logic for users without order history
            detected_cuisines = []
            cuisine_keywords = {
                'pakistani': ['Pakistani'], 'biryani': ['Pakistani'], 'karahi': ['Pakistani'],
                'chinese': ['Chinese'], 'chowmein': ['Chinese'], 'fried rice': ['Chinese'],
                'fast food': ['Fast Food'], 'burger': ['Fast Food'], 'pizza': ['Fast Food'],
                'bbq': ['BBQ'], 'kebab': ['BBQ'], 'tikka': ['BBQ'],
                'dessert': ['Desserts'], 'desserts': ['Desserts'], 'sweet': ['Desserts'],
            }
            
            for keyword, cuisines in cuisine_keywords.items():
                if keyword in message_lower:
                    detected_cuisines.extend(cuisines)
            
            if not detected_cuisines and current_user.favorite_cuisines:
                detected_cuisines = current_user.favorite_cuisines[:3]
            
            if detected_cuisines:
                new_items = await get_menu_items_by_cuisine(
                    detected_cuisines,
                    limit=3,
                    user_preferences=user_context['explicit_preferences']
                )
        
        show_order_card = len(reorder_items) > 0 or len(new_items) > 0

    # Process with enhanced Gemini
    response_text = await process_with_gemini_enhanced(
        chat_request.message,
        user_context,
        order_history,
        reorder_items,
        new_items,
        is_new_request
    )

    # Save chat message
    chat_message = ChatMessage(
        user_id=current_user.id,
        message=chat_request.message,
        response=response_text,
        session_id=chat_request.session_id or str(uuid.uuid4())
    )
    await db.chat_messages.insert_one(chat_message.dict())

    return {
        "response": response_text,
        "reorder_items": reorder_items,  # Past favorites for reorder
        "new_items": new_items,  # New recommendations
        "order_history_summary": {
            "has_history": order_history.get("has_history"),
            "total_orders": order_history.get("total_orders", 0),
            "dominant_cuisines": order_history.get("dominant_cuisines", []),
            "most_ordered_cuisine": order_history.get("most_ordered_cuisine")
        } if order_history.get("has_history") else None,
        "show_order_card": show_order_card,
        "has_default_address": user_context['default_address'] is not None,
        "default_address": user_context['default_address'],
        "session_id": chat_message.session_id
    }

async def handle_direct_order_request(current_user, message):
    """Handle direct order placement from chat"""
    try:
        # Check if user has default address
        default_address = None
        for address in current_user.addresses:
            if address.get('is_default'):
                default_address = address
                break
        
        if not default_address:
            return {
                "response": "📍 I need a delivery address first! Please add one in your profile.",
                "restaurants": [],
                "recommended_items": [],
                "show_order_card": False,
                "needs_address": True,
                "session_id": str(uuid.uuid4())
            }
        
        # For now, return order confirmation UI
        return {
            "response": f"✅ Ready to place your order!\n📍 Delivering to: {default_address['area']}, {default_address['district']}\n💳 Payment: Cash on Delivery",
            "restaurants": [],
            "recommended_items": [],
            "show_order_card": True,
            "order_ready": True,
            "default_address": default_address,
            "session_id": str(uuid.uuid4())
        }
        
    except Exception as e:
        logging.error(f"Error handling direct order: {e}")
        return {
            "response": "Something went wrong! Please try adding items to cart manually.",
            "restaurants": [],
            "recommended_items": [],
            "show_order_card": False,
            "session_id": str(uuid.uuid4())
        }

async def get_menu_items_by_cuisine(cuisines: List[str], limit: int = 3, user_preferences: Dict = None):
    """Get menu items based on cuisine types - preference-aware with fallback"""
    try:
        if not cuisines:
            return []
        
        logging.info(f"get_menu_items_by_cuisine called with: Cuisines={cuisines}, Limit={limit}, UserPrefs provided: {bool(user_preferences)}")
        
        # Comprehensive cuisine mapping for tags and keywords
        cuisine_mapping = {
            'Pakistani': {
                'tags': ['biryani', 'rice', 'pakistani', 'karahi', 'nihari', 'pulao'],
                'name_patterns': ['biryani', 'karahi', 'nihari', 'haleem', 'pulao', 'seekh']
            },
            'Chinese': {
                'tags': ['chinese', 'noodles', 'rice', 'asian'],
                'name_patterns': ['chowmein', 'fried rice', 'manchurian', 'noodle', 'chow mein']
            },
            'Fast Food': {
                'tags': ['burger', 'fast food', 'pizza', 'fries', 'sandwich'],
                'name_patterns': ['burger', 'pizza', 'fries', 'sandwich', 'nugget', 'wings']
            },
            'BBQ': {
                'tags': ['bbq', 'grill', 'tikka', 'kebab', 'barbecue'],
                'name_patterns': ['tikka', 'kebab', 'seekh', 'boti', 'bbq', 'grill']
            },
            'Desserts': {
                'tags': ['dessert', 'sweet', 'ice cream', 'cake', 'pastry'],
                'name_patterns': ['cake', 'ice cream', 'kulfi', 'kheer', 'dessert', 'sweet', 'pastry', 'brownie']
            },
            'Japanese': {
                'tags': ['japanese', 'sushi', 'ramen', 'asian'],
                'name_patterns': ['sushi', 'sashimi', 'ramen', 'teriyaki', 'tempura', 'maki']
            },
            'Thai': {
                'tags': ['thai', 'curry', 'asian'],
                'name_patterns': ['pad thai', 'curry', 'tom yum', 'thai']
            },
            'Indian': {
                'tags': ['indian', 'curry', 'tandoori'],
                'name_patterns': ['curry', 'tandoori', 'naan', 'paneer', 'dal', 'masala']
            },
            'Italian': {
                'tags': ['italian', 'pasta', 'pizza'],
                'name_patterns': ['pasta', 'pizza', 'lasagna', 'spaghetti', 'ravioli']
            },
            'Mexican': {
                'tags': ['mexican', 'taco', 'burrito'],
                'name_patterns': ['taco', 'burrito', 'quesadilla', 'nachos']
            }
        }
        
        all_items = []
        
        # Strategy 1: Find restaurants by cuisine first
        restaurant_ids = []
        for cuisine in cuisines:
            restaurants_cursor = db.restaurants.find({
                "cuisine": cuisine,
                "is_active": True
            }, {"_id": 0})
            restaurants = await restaurants_cursor.to_list(None)
            restaurant_ids.extend([r['id'] for r in restaurants])
            logging.info(f"Found {len(restaurants)} restaurants for cuisine {cuisine}")
        
        # Get items from those restaurants
        if restaurant_ids:
            menu_items_cursor = db.menu_items.find({
                "restaurant_id": {"$in": restaurant_ids},
                "available": True
            }, {"_id": 0}).limit(limit * 3)
            restaurant_items = await menu_items_cursor.to_list(None)
            all_items.extend(restaurant_items)
            logging.info(f"Found {len(restaurant_items)} items from restaurants")
        
        # Strategy 2: Search by tags and name patterns for each cuisine
        for cuisine in cuisines:
            if cuisine in cuisine_mapping:
                mapping = cuisine_mapping[cuisine]
                
                # Build regex pattern for name search
                name_pattern = '|'.join(mapping['name_patterns'])
                
                query = {
                    "available": True,
                    "$or": [
                        {"tags": {"$in": mapping['tags']}},
                        {"name": {"$regex": name_pattern, "$options": "i"}},
                        {"category": {"$regex": cuisine, "$options": "i"}}
                    ]
                }
                
                menu_items_cursor = db.menu_items.find(query, {"_id": 0}).limit(limit * 2)
                pattern_items = await menu_items_cursor.to_list(None)
                all_items.extend(pattern_items)
                logging.info(f"Found {len(pattern_items)} items by pattern matching for {cuisine}")
        
        # Remove duplicates by ID
        seen_ids = set()
        unique_items = []
        for item in all_items:
            if item['id'] not in seen_ids:
                seen_ids.add(item['id'])
                unique_items.append(item)
        
        logging.info(f"Total unique items found: {len(unique_items)}")
        
        # Enrich items with restaurant info and score them
        for item in unique_items:
            restaurant = await db.restaurants.find_one({"id": item["restaurant_id"]}, {"_id": 0})
            if restaurant:
                item["restaurant_name"] = restaurant["name"]
                item["restaurant_rating"] = restaurant["rating"]
                item["delivery_time"] = restaurant["delivery_time"]
                item["restaurant_cuisine"] = restaurant.get("cuisine", "")
            
            # Calculate preference score
            score = 0
            if user_preferences:
                favorite_cuisines = user_preferences.get('favorite_cuisines', [])
                spice_pref = user_preferences.get('spice_preference', 'medium')
                
                # Boost if restaurant cuisine matches user preferences
                restaurant_cuisine = item.get('restaurant_cuisine', '')
                if restaurant_cuisine in favorite_cuisines:
                    score += 15
                
                # Boost if cuisine is in the requested cuisines
                if restaurant_cuisine in cuisines:
                    score += 10
                
                # Boost if spice level matches
                if item.get('spice_level') == spice_pref:
                    score += 5
                
                # Add rating boost
                score += item.get('average_rating', 0) * 2

            else:
                # Default scoring by calling the recommendation engine with an empty explicit preferences dict
                temp_user_prefs_vector = {
                    'explicit_preferences': {},
                    'cuisine_preferences': {},
                    'category_preferences': {},
                    'spice_preferences': {}
                }
                score = recommendation_engine.calculate_content_score(item, temp_user_prefs_vector)
                logging.debug(f"Scored item '{item.get('name')}' with score: {score} without user prefs.")
            
            # Add general popularity boost and finalize preference score
            score += item.get('popularity_score', 0)
            item['preference_score'] = score
        
        # Sort by preference score
        unique_items.sort(key=lambda x: x.get('preference_score', 0), reverse=True)
        
        # Return top items
        result = unique_items[:limit]
        logging.info(f"Returning {len(result)} items")
        return result
        
    except Exception as e:
        logging.error(f"Error getting menu items by cuisine: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return []

@api_router.post("/chat/order")
async def place_order_from_chat(
    request: dict,
    current_user: User = Depends(get_current_user)
):
    """Place order directly from chat - streamlined version"""
    try:
        menu_item_ids = request.get('menu_item_ids', [])
        quantities = request.get('quantities', [])
        use_default_address = request.get('use_default_address', True)
        payment_method = request.get('payment_method', 'cod')
        
        if not menu_item_ids:
            return {"success": False, "message": "No items selected"}
        
        # Get default address
        default_address = None
        if use_default_address:
            for address in current_user.addresses:
                if address.get('is_default'):
                    default_address = address
                    break
        
        if not default_address:
            return {"success": False, "message": "Please add a delivery address in your profile first! 📍"}
        
        # Calculate order directly without cart
        subtotal = 0
        order_items = []
        restaurant_id = None
        
        for i, menu_item_id in enumerate(menu_item_ids):
            menu_item = await db.menu_items.find_one({"id": menu_item_id}, {"_id": 0})
            if menu_item:
                quantity = quantities[i] if i < len(quantities) else 1
                item_total = menu_item["price"] * quantity
                subtotal += item_total
                restaurant_id = menu_item["restaurant_id"]
                
                order_items.append({
                    "menu_item_id": menu_item_id,
                    "quantity": quantity,
                    "price": menu_item["price"],
                    "special_instructions": ""
                })
        
        if not order_items:
            return {"success": False, "message": "Selected items not available"}
        
        # Get restaurant info
        restaurant = await db.restaurants.find_one({"id": restaurant_id}, {"_id": 0})
        delivery_fee = restaurant["delivery_fee"] if restaurant else 50
        tax = subtotal * 0.05
        total = subtotal + delivery_fee + tax
        
        # Create order directly
        order_number = generate_order_number()
        order_dict = {
            "id": str(uuid.uuid4()),
            "order_number": order_number,
            "user_id": current_user.id,
            "restaurant_id": restaurant_id,
            "items": order_items,
            "delivery_address": default_address,
            "payment_method": payment_method,
            "payment_status": "cash_on_delivery" if payment_method == "cod" else "pending",
            "order_status": "placed",
            "pricing": {
                "subtotal": float(subtotal),
                "delivery_fee": float(delivery_fee),
                "tax": float(tax),
                "total": float(total)
            },
            "estimated_delivery_time": datetime.now(timezone.utc) + timedelta(minutes=35),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        # Insert order
        result = await db.orders.insert_one(order_dict)
        
        if result.inserted_id:
            # Send email notification (fire and forget)
            try:
                asyncio.create_task(send_order_confirmation_email(
                    current_user.email,
                    current_user.username,
                    order_dict,
                    [{"name": item.get("name", "Item"), "quantity": item["quantity"], "price": item["price"]} for item in order_items]
                ))
            except Exception as email_error:
                logging.error(f"Email sending failed: {email_error}")
            
            return {
                "success": True,
                "message": f"Order placed! #{order_number}",
                "order_number": order_number,
                "total": float(total)
            }
        else:
            return {"success": False, "message": "Failed to save order"}
            
    except Exception as e:
        logging.error(f"Error placing order from chat: {e}")
        return {"success": False, "message": f"Order failed: {str(e)}"}

@api_router.post("/voice-order")
async def process_voice_order(
    voice_request: VoiceOrderRequest,
    current_user: User = Depends(get_current_user)
):
    # Process voice text with Gemini to extract order intent
    user_context = {
        "username": current_user.username,
        "favorite_cuisines": current_user.favorite_cuisines,
        "dietary_restrictions": current_user.dietary_restrictions,
        "spice_preference": current_user.spice_preference
    }
    
    order_prompt = f"""
    Parse this food order request and provide a helpful response:
    "{voice_request.audio_text}"
    
    User preferences: {user_context}
    
    If this sounds like an order request:
    1. Acknowledge what they want
    2. Suggest specific restaurants and items
    3. Ask if they want to add items to cart
    4. Mention delivery address will be needed
    
    Be conversational and helpful. Use Pakistani Rupee (PKR) for prices.
    """
    
    response = await process_with_gemini(order_prompt, user_context)
    
    return {
        "response": response,
        "original_text": voice_request.audio_text
    }

# Health check
@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc)}

@api_router.post("/admin/generate-embeddings")
async def generate_all_embeddings(background_tasks: BackgroundTasks):
    """Generate embeddings for all menu items (run once during setup)"""
    try:
        # Get all menu items without embeddings
        menu_items_cursor = db.menu_items.find(
            {"$or": [{"embedding": None}, {"embedding": {"$exists": False}}]},
            {"_id": 0}
        )
        menu_items = await menu_items_cursor.to_list(None)
        
        logging.info(f"Found {len(menu_items)} items without embeddings")
        
        # Generate embeddings in background
        background_tasks.add_task(process_embeddings_batch, menu_items)
        
        return {
            "message": f"Started generating embeddings for {len(menu_items)} items",
            "status": "processing"
        }
    except Exception as e:
        logging.error(f"Error starting embedding generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_embeddings_batch(menu_items: List[Dict]):
    """Process embeddings for a batch of menu items"""
    success_count = 0
    error_count = 0
    
    for item in menu_items:
        try:
            # Create text representation
            item_text = await create_menu_item_text(item)
            
            # Generate embedding
            embedding = await generate_embedding(item_text)
            
            if embedding:
                # Update in database
                await db.menu_items.update_one(
                    {"id": item['id']},
                    {
                        "$set": {
                            "embedding": embedding,
                            "embedding_text": item_text
                        }
                    }
                )
                success_count += 1
                logging.info(f"✅ Generated embedding for: {item.get('name')}")
            else:
                error_count += 1
                logging.error(f"❌ Failed to generate embedding for: {item.get('name')}")
            
            # Small delay to avoid rate limits
            await asyncio.sleep(0.1)
            
        except Exception as e:
            error_count += 1
            logging.error(f"Error processing item {item.get('name')}: {e}")
    
    logging.info(f"Embedding generation complete: {success_count} success, {error_count} errors")

@api_router.get("/admin/embedding-status")
async def get_embedding_status():
    """Check how many items have embeddings"""
    total_items = await db.menu_items.count_documents({})
    items_with_embeddings = await db.menu_items.count_documents({
        "embedding": {"$exists": True, "$ne": None}
    })
    
    return {
        "total_items": total_items,
        "items_with_embeddings": items_with_embeddings,
        "items_without_embeddings": total_items - items_with_embeddings,
        "percentage_complete": round((items_with_embeddings / total_items * 100), 2) if total_items > 0 else 0
    }

# Include router
app.include_router(api_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()