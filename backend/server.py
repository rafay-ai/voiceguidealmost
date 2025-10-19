from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, Request, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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
        """Get personalized recommendations for a user"""
        user_prefs = await self.get_user_preferences_vector(user_id)
        if not user_prefs:
            # Return popular items for new users
            return await self.get_popular_items(limit)

        # Get similar users for collaborative filtering
        similar_users = await self.get_similar_users(user_id)
        
        # Get items ordered by similar users
        collaborative_items = await self.get_collaborative_recommendations(user_id, similar_users, limit // 2)
        
        # Get content-based recommendations
        content_based_items = await self.get_content_based_recommendations(user_prefs, limit // 2)
        
        # Combine and remove duplicates
        all_recommendations = []
        seen_items = set()
        
        # Add collaborative filtering results first (higher weight)
        for item in collaborative_items:
            if item['id'] not in seen_items:
                item['recommendation_reason'] = 'Users with similar tastes also liked this'
                all_recommendations.append(item)
                seen_items.add(item['id'])
        
        # Add content-based results
        for item in content_based_items:
            if item['id'] not in seen_items:
                item['recommendation_reason'] = 'Based on your preferences'
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
        """Get recommendations based on user's content preferences"""
        cuisine_prefs = user_prefs.get('cuisine_preferences', {})
        category_prefs = user_prefs.get('category_preferences', {})
        
        # Build query based on preferences
        query_conditions = []
        
        # Filter by preferred cuisines if available
        if cuisine_prefs:
            preferred_cuisines = list(cuisine_prefs.keys())
            restaurants_cursor = self.db.restaurants.find({
                "cuisine": {"$in": preferred_cuisines}
            }, {"_id": 0}).limit(100)
            restaurants = await restaurants_cursor.to_list(None)
            restaurant_ids = [r['id'] for r in restaurants]
            
            if restaurant_ids:
                query_conditions.append({"restaurant_id": {"$in": restaurant_ids}})
        
        # Filter by preferred categories
        if category_prefs:
            preferred_categories = list(category_prefs.keys())
            query_conditions.append({"category": {"$in": preferred_categories}})

        # Base query for available items
        base_query = {"available": True}
        
        if query_conditions:
            query = {"$and": [base_query, {"$or": query_conditions}]}
        else:
            query = base_query

        # Get items and score them
        menu_items_cursor = self.db.menu_items.find(query, {"_id": 0}).limit(limit * 3)
        menu_items = await menu_items_cursor.to_list(None)
        
        # Score items based on preferences
        scored_items = []
        for item in menu_items:
            score = self.calculate_content_score(item, user_prefs)
            item['recommendation_score'] = score
            scored_items.append(item)

        # Sort by score and return top items
        scored_items.sort(key=lambda x: x['recommendation_score'], reverse=True)
        return scored_items[:limit]

    def calculate_content_score(self, menu_item: Dict, user_prefs: Dict):
        """Calculate content-based score for a menu item"""
        score = 0.0
        
        # Base score from popularity
        score += menu_item.get('popularity_score', 0) * 2
        score += menu_item.get('average_rating', 0) * 0.5
        
        # Category preference score
        category_prefs = user_prefs.get('category_preferences', {})
        category = menu_item.get('category', '')
        if category in category_prefs:
            score += category_prefs[category] * 0.8
        
        # Spice preference score
        spice_prefs = user_prefs.get('spice_preferences', {})
        spice_level = menu_item.get('spice_level', '')
        if spice_level in spice_prefs:
            score += spice_prefs[spice_level] * 0.3

        return score

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

async def process_with_gemini(message: str, user_context: Dict = None, include_restaurants: bool = True):
    """Process message with ultra-brief, action-focused responses"""
    
    # Simple keyword-based responses for faster, more predictable behavior
    message_lower = message.lower()
    username = user_context.get('username', 'User')
    
    # Direct food requests
    if any(word in message_lower for word in ['hungry', 'eat', 'food', 'order']):
        return f"🍽️ Perfect! Here are great options for you:"
    
    # Recommendation requests
    if any(word in message_lower for word in ['recommend', 'suggestion', 'suggest']):
        return f"✨ Here are my top recommendations based on your taste:"
    
    # Specific cuisine requests with emojis
    if 'biryani' in message_lower or 'pakistani' in message_lower:
        return f"🍛 Excellent choice! Best Pakistani options:"
    
    if 'chinese' in message_lower or 'chowmein' in message_lower:
        return f"🥢 Great! Top Chinese restaurants:"
    
    if 'fast food' in message_lower or 'burger' in message_lower:
        return f"🍔 Perfect! Fast food favorites:"
    
    if any(word in message_lower for word in ['dessert', 'sweet', 'cake', 'ice cream', 'kulfi']):
        return f"🍰 Sweet cravings? Here are the best dessert spots:"
    
    if 'japanese' in message_lower or 'sushi' in message_lower:
        return f"🍱 Fantastic! Authentic Japanese cuisine:"
    
    if 'thai' in message_lower or 'pad thai' in message_lower:
        return f"🍜 Wonderful! Best Thai restaurants:"
    
    if 'bbq' in message_lower or 'tikka' in message_lower or 'kebab' in message_lower:
        return f"🥩 Great choice! Top BBQ spots:"
    
    if 'indian' in message_lower or 'curry' in message_lower:
        return f"🍛 Excellent! Best Indian options:"
    
    if 'italian' in message_lower or 'pasta' in message_lower or 'pizza' in message_lower:
        return f"🍝 Delizioso! Italian favorites:"
    
    if 'mexican' in message_lower or 'taco' in message_lower:
        return f"🌮 Olé! Mexican delights:"
    
    # Order confirmation requests
    if any(phrase in message_lower for phrase in ['order this', 'order that', 'place order', 'yes order']):
        return f"✅ Perfect! I'll place this order for you right now!"
    
    # Budget requests
    if any(word in message_lower for word in ['budget', 'cheap', 'affordable']):
        return f"💰 Great value meals under PKR 500:"
    
    # Default friendly response
    return f"Hi {username}! 👋 Try: 'I'm hungry' or 'recommend me something' for instant help!"

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
    # Get user context for better responses
    user_context = {
        "user_id": current_user.id,
        "username": current_user.username,
        "favorite_cuisines": current_user.favorite_cuisines,
        "dietary_restrictions": current_user.dietary_restrictions,
        "spice_preference": current_user.spice_preference,
        "preferences_set": current_user.preferences_set,
        "default_address": None
    }
    
    # Check if user has default address
    for address in current_user.addresses:
        if address.get('is_default'):
            user_context['default_address'] = address
            break
    
    message_lower = chat_request.message.lower()
    
    # Handle direct order requests
    if any(phrase in message_lower for phrase in ['order this', 'order that', 'place order', 'yes order']):
        return await handle_direct_order_request(current_user, chat_request.message)
    
    # Get restaurant recommendations and menu items for food requests
    restaurants = []
    recommended_items = []
    show_order_card = False
    
    # Comprehensive cuisine keywords
    cuisine_keywords = {
        'pakistani': ['Pakistani'], 'biryani': ['Pakistani'], 'karahi': ['Pakistani'],
        'chinese': ['Chinese'], 'chowmein': ['Chinese'], 'fried rice': ['Chinese'],
        'fast food': ['Fast Food'], 'burger': ['Fast Food'], 'pizza': ['Fast Food'], 
        'bbq': ['BBQ'], 'kebab': ['BBQ'], 'tikka': ['BBQ'],
        'dessert': ['Desserts'], 'desserts': ['Desserts'], 'sweet': ['Desserts'], 'sweets': ['Desserts'], 
        'ice cream': ['Desserts'], 'cake': ['Desserts'],
        'japanese': ['Japanese'], 'sushi': ['Japanese'], 'ramen': ['Japanese'],
        'thai': ['Thai'], 'pad thai': ['Thai'], 'curry': ['Thai'],
        'indian': ['Indian'], 'tandoori': ['Indian'],
        'italian': ['Italian'], 'pasta': ['Italian'],
        'mexican': ['Mexican'], 'taco': ['Mexican']
    }
    
    food_keywords = ['food', 'hungry', 'eat', 'order', 'restaurant', 'recommend', 'suggestion', 'suggest']
    
    if any(keyword in message_lower for keyword in food_keywords):
        restaurants = await get_restaurant_recommendations_for_chat(chat_request.message, user_context)
        
        # Detect cuisines from message
        detected_cuisines = []
        for keyword, cuisines in cuisine_keywords.items():
            if keyword in message_lower:
                detected_cuisines.extend(cuisines)
        
        # Remove duplicates
        detected_cuisines = list(set(detected_cuisines))
        
        # If no specific cuisine detected but user asks for food/recommendations, use their preferences
        if not detected_cuisines and any(word in message_lower for word in ['hungry', 'recommend', 'suggestion', 'food', 'eat']):
            user_prefs = current_user.favorite_cuisines
            if user_prefs:
                detected_cuisines = user_prefs[:3]  # Use top 3 preferences
        
        # Get menu items for detected cuisines
        if detected_cuisines:
            recommended_items = await get_menu_items_by_cuisine(
                detected_cuisines, 
                limit=3,
                user_preferences={
                    'favorite_cuisines': current_user.favorite_cuisines,
                    'spice_preference': current_user.spice_preference
                }
            )
            show_order_card = len(recommended_items) > 0
    
    # Process with ultra-brief response
    response = await process_with_gemini(chat_request.message, user_context)
    
    # Save chat message
    chat_message = ChatMessage(
        user_id=current_user.id,
        message=chat_request.message,
        response=response,
        session_id=chat_request.session_id or str(uuid.uuid4())
    )
    
    await db.chat_messages.insert_one(chat_message.dict())
    
    return {
        "response": response,
        "restaurants": restaurants,
        "recommended_items": recommended_items,
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
        
        logging.info(f"Searching for cuisines: {cuisines}")
        
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
                # Default scoring by rating and popularity
                score = item.get('average_rating', 0) * 2 + item.get('popularity_score', 0)
            
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