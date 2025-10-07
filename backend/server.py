from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, Request
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

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Configure Gemini
genai.configure(api_key=os.environ['GEMINI_API_KEY'])

# Create the main app
app = FastAPI(title="Voice Guide API", version="1.0.0")
api_router = APIRouter(prefix="/api")

# JWT Configuration
SECRET_KEY = "voice_guide_secret_key_2024"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

# Security
security = HTTPBearer()
executor = ThreadPoolExecutor(max_workers=4)

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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

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
        user = await db.users.find_one({"id": user_id})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return User(**user)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

# --- Recommendation Engine ---
class RecommendationEngine:
    def __init__(self, db_client):
        self.db = db_client

    async def get_user_order_history(self, user_id: str, limit: int = 50):
        """Get user's order history for recommendations"""
        orders = await self.db.orders.find(
            {"user_id": user_id}, 
            sort=[("created_at", -1)]
        ).to_list(limit)
        return orders

    async def get_user_preferences_vector(self, user_id: str):
        """Create user preference vector based on order history and explicit preferences"""
        user = await self.db.users.find_one({"id": user_id})
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
                menu_item = await self.db.menu_items.find_one({"id": item['menu_item_id']})
                if menu_item:
                    # Update cuisine preferences
                    restaurant = await self.db.restaurants.find_one({"id": menu_item['restaurant_id']})
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
            menu_item = await self.db.menu_items.find_one({"id": menu_item_id})
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
            restaurants = await self.db.restaurants.find({
                "cuisine": {"$in": preferred_cuisines}
            }).to_list(100)
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
        menu_items = await self.db.menu_items.find(query).to_list(limit * 3)
        
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
        
        # Cuisine preference score
        cuisine_prefs = user_prefs.get('cuisine_preferences', {})
        # Get restaurant cuisine
        # This would need restaurant lookup, simplified here
        
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

# --- Gemini Chat Integration ---
async def process_with_gemini(message: str, user_context: Dict = None):
    """Process message with Gemini AI"""
    loop = asyncio.get_event_loop()
    
    def _process():
        try:
            model = genai.GenerativeModel('gemini-2.0-flash')
            
            # Build context-aware prompt
            context = f"""You are a helpful food delivery assistant for Voice Guide app. You can:
1. Recommend food items based on user preferences
2. Help users place orders through voice or text
3. Answer questions about restaurants and menu items
4. Assist with dietary restrictions and preferences

User context: {json.dumps(user_context or {})}

User message: {message}

Please respond naturally and helpfully. If the user wants to place an order, ask for details like restaurant preference, cuisine type, dietary restrictions, etc."""
            
            response = model.generate_content(context)
            return response.text
        except Exception as e:
            logging.error(f"Gemini processing error: {e}")
            return "I'm sorry, I'm having trouble processing your request right now. Please try again."
    
    return await loop.run_in_executor(executor, _process)

# --- API Routes ---

# Authentication Routes
@api_router.post("/auth/register")
async def register_user(user_data: UserCreate):
    # Check if user exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    hashed_password = hash_password(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hashed_password
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
            "email": new_user.email
        }
    }

@api_router.post("/auth/login")
async def login_user(user_data: UserLogin):
    user = await db.users.find_one({"email": user_data.email})
    if not user or not verify_password(user_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    access_token = create_access_token(data={"sub": user["id"]})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"]
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
        "spice_preference": current_user.spice_preference
    }

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
        "spice_preference": current_user.spice_preference
    }
    
    # Process with Gemini
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
        "session_id": chat_message.session_id
    }

@api_router.post("/voice-order")
async def process_voice_order(
    voice_request: VoiceOrderRequest,
    current_user: User = Depends(get_current_user)
):
    # Process voice text with Gemini to extract order intent
    order_prompt = f"""
    Parse this food order request and extract structured information:
    "{voice_request.audio_text}"
    
    Extract:
    1. Food items mentioned
    2. Quantities if specified
    3. Any special instructions
    4. Restaurant preference if mentioned
    5. Cuisine type if mentioned
    
    Respond in JSON format with the extracted information.
    """
    
    response = await process_with_gemini(order_prompt)
    
    return {
        "parsed_order": response,
        "original_text": voice_request.audio_text
    }

# Order Routes
@api_router.get("/orders")
async def get_user_orders(
    page: int = 1,
    limit: int = 10,
    current_user: User = Depends(get_current_user)
):
    skip = (page - 1) * limit
    orders = await db.orders.find(
        {"user_id": current_user.id}
    ).sort([("created_at", -1)]).skip(skip).limit(limit).to_list(None)
    
    total = await db.orders.count_documents({"user_id": current_user.id})
    
    return {
        "orders": orders,
        "total": total,
        "page": page,
        "limit": limit
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
    format='%(asctime)s - %(name)s - %(levelevel)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()