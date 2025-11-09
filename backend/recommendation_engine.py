"""
Enhanced Recommendation Engine with Gemini Embeddings
Provides intelligent, context-aware recommendations based on:
- User order history
- Dietary preferences and restrictions
- Semantic similarity using embeddings
- Time-based patterns
"""

import os
import logging
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple
import google.generativeai as genai
from motor.motor_asyncio import AsyncIOMotorClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)


class RecommendationEngine:
    """Advanced recommendation engine using embeddings and order history"""
    
    def __init__(self, db):
        self.db = db
        self.embedding_model = "models/embedding-001"  # Gemini embedding model
        
    async def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using Gemini"""
        try:
            result = genai.embed_content(
                model=self.embedding_model,
                content=text,
                task_type="retrieval_document"
            )
            return result['embedding']
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return []
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            vec1 = np.array(vec1)
            vec2 = np.array(vec2)
            return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0
    
    async def generate_item_embeddings(self, limit: int = None):
        """Generate and store embeddings for all menu items"""
        try:
            query = {"available": True}
            cursor = self.db.menu_items.find(query, {"_id": 0})
            
            if limit:
                cursor = cursor.limit(limit)
            
            items = await cursor.to_list(None)
            updated_count = 0
            
            for item in items:
                # Check if embedding already exists
                if item.get("embedding"):
                    continue
                
                # Create rich text description for embedding
                text_for_embedding = f"{item.get('name', '')} {item.get('description', '')} "
                text_for_embedding += f"{' '.join(item.get('tags', []))} "
                text_for_embedding += f"spice: {item.get('spice_level', '')} "
                text_for_embedding += f"vegetarian: {item.get('is_vegetarian', False)}"
                
                # Generate embedding
                embedding = await self.get_embedding(text_for_embedding)
                
                if embedding:
                    # Store embedding in database
                    await self.db.menu_items.update_one(
                        {"id": item["id"]},
                        {"$set": {"embedding": embedding}}
                    )
                    updated_count += 1
            
            logger.info(f"Generated embeddings for {updated_count} items")
            return updated_count
            
        except Exception as e:
            logger.error(f"Error generating item embeddings: {e}")
            return 0
    
    async def get_user_order_history(self, user_id: str, days: int = 30) -> Dict:
        """Analyze user's order history for the past N days"""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            orders_cursor = self.db.orders.find(
                {
                    "user_id": user_id,
                    "created_at": {"$gte": cutoff_date},
                    "status": {"$in": ["delivered", "completed"]}
                },
                {"_id": 0}
            ).sort([("created_at", -1)])
            
            orders = await orders_cursor.to_list(None)
            
            if not orders:
                return {
                    "has_history": False,
                    "total_orders": 0,
                    "ordered_items": [],
                    "cuisine_preferences": {},
                    "order_frequency": {}
                }
            
            # Track ordered items and their frequency
            item_frequency = {}
            cuisine_frequency = {}
            
            for order in orders:
                # Get restaurant info
                restaurant = await self.db.restaurants.find_one(
                    {"id": order["restaurant_id"]},
                    {"_id": 0, "cuisine": 1, "name": 1}
                )
                
                # Track cuisines
                if restaurant:
                    for cuisine in restaurant.get("cuisine", []):
                        cuisine_frequency[cuisine] = cuisine_frequency.get(cuisine, 0) + 1
                
                # Track items
                for item in order.get("items", []):
                    item_id = item["menu_item_id"]
                    if item_id not in item_frequency:
                        item_frequency[item_id] = {
                            "count": 0,
                            "last_ordered": order["created_at"],
                            "restaurant_id": order["restaurant_id"]
                        }
                    item_frequency[item_id]["count"] += item["quantity"]
            
            # Get top ordered items with details
            ordered_items = []
            for item_id, data in sorted(item_frequency.items(), key=lambda x: x[1]["count"], reverse=True)[:10]:
                menu_item = await self.db.menu_items.find_one(
                    {"id": item_id},
                    {"_id": 0}
                )
                
                if menu_item:
                    restaurant = await self.db.restaurants.find_one(
                        {"id": data["restaurant_id"]},
                        {"_id": 0, "name": 1}
                    )
                    
                    ordered_items.append({
                        "item": menu_item,
                        "count": data["count"],
                        "last_ordered": data["last_ordered"],
                        "restaurant_name": restaurant.get("name", "Unknown") if restaurant else "Unknown"
                    })
            
            return {
                "has_history": True,
                "total_orders": len(orders),
                "ordered_items": ordered_items,
                "cuisine_preferences": dict(sorted(cuisine_frequency.items(), key=lambda x: x[1], reverse=True)),
                "order_frequency": item_frequency
            }
            
        except Exception as e:
            logger.error(f"Error analyzing order history: {e}")
            return {"has_history": False, "total_orders": 0, "ordered_items": [], "cuisine_preferences": {}}
    
    async def get_recommendations(
        self,
        user_id: str,
        user_preferences: Dict,
        query: str = "",
        limit: int = 6,
        exclude_ordered: bool = False
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Get personalized recommendations using embeddings and order history
        Returns: (reorder_items, new_recommendations)
        """
        try:
            # Get user order history
            order_history = await self.get_user_order_history(user_id, days=30)
            
            # Get user dietary restrictions
            dietary_restrictions = user_preferences.get("dietary_restrictions", [])
            favorite_cuisines = user_preferences.get("favorite_cuisines", [])
            spice_preference = user_preferences.get("spice_preference", "medium")
            
            # REORDER RECOMMENDATIONS - Items user has ordered before
            reorder_items = []
            if order_history["has_history"] and not exclude_ordered:
                for ordered in order_history["ordered_items"][:3]:
                    item = ordered["item"]
                    
                    # Check dietary restrictions
                    if self._check_dietary_compatibility(item, dietary_restrictions):
                        reorder_items.append({
                            "id": item["id"],
                            "name": item["name"],
                            "description": item.get("description", ""),
                            "price": item["price"],
                            "image_url": item.get("image_url", ""),
                            "restaurant_id": item["restaurant_id"],
                            "restaurant_name": ordered["restaurant_name"],
                            "order_count": ordered["count"],
                            "last_ordered": ordered["last_ordered"],
                            "tags": item.get("tags", []),
                            "spice_level": item.get("spice_level", "medium"),
                            "is_vegetarian": item.get("is_vegetarian", False),
                            "is_vegan": item.get("is_vegan", False),
                            "average_rating": item.get("average_rating", 4.0)
                        })
            
            # NEW RECOMMENDATIONS - Items user hasn't tried
            new_recommendations = []
            
            # Generate query embedding if query provided
            query_embedding = None
            if query:
                query_embedding = await self.get_embedding(query)
            
            # Build filter for menu items
            item_filter = {"available": True}
            
            # Exclude previously ordered items if requested
            if exclude_ordered and order_history["has_history"]:
                ordered_item_ids = list(order_history["order_frequency"].keys())
                item_filter["id"] = {"$nin": ordered_item_ids}
            
            # Get all available items with embeddings
            items_cursor = self.db.menu_items.find(item_filter, {"_id": 0})
            all_items = await items_cursor.to_list(None)
            
            # Score and rank items
            scored_items = []
            for item in all_items:
                # Check dietary restrictions (STRICT)
                if not self._check_dietary_compatibility(item, dietary_restrictions):
                    continue
                
                score = 0.0
                
                # Embedding similarity score
                if query_embedding and item.get("embedding"):
                    similarity = self.cosine_similarity(query_embedding, item["embedding"])
                    score += similarity * 40  # 40% weight
                
                # Cuisine preference score
                restaurant = await self.db.restaurants.find_one(
                    {"id": item["restaurant_id"]},
                    {"_id": 0, "cuisine": 1, "name": 1, "rating": 1}
                )
                
                if restaurant:
                    item_cuisines = restaurant.get("cuisine", [])
                    for cuisine in item_cuisines:
                        if cuisine in favorite_cuisines:
                            score += 15  # 15% weight per matching cuisine
                        if cuisine in order_history.get("cuisine_preferences", {}):
                            score += 10  # 10% weight for previously ordered cuisine
                
                # Spice preference match
                item_spice = item.get("spice_level", "medium")
                if item_spice == spice_preference:
                    score += 10  # 10% weight
                
                # Popularity score
                rating = item.get("average_rating", 4.0)
                order_count = item.get("order_count", 0)
                popularity_score = (rating / 5.0) * 10 + min(order_count / 100, 10)
                score += popularity_score  # Up to 20% weight
                
                # Add dietary preference bonus
                if "vegetarian" in dietary_restrictions and item.get("is_vegetarian"):
                    score += 5
                if "vegan" in dietary_restrictions and item.get("is_vegan"):
                    score += 5
                if "halal" in dietary_restrictions and item.get("is_halal"):
                    score += 5
                
                scored_items.append({
                    "item": item,
                    "score": score,
                    "restaurant": restaurant
                })
            
            # Sort by score and take top items
            scored_items.sort(key=lambda x: x["score"], reverse=True)
            
            for scored in scored_items[:limit]:
                item = scored["item"]
                restaurant = scored["restaurant"]
                
                new_recommendations.append({
                    "id": item["id"],
                    "name": item["name"],
                    "description": item.get("description", ""),
                    "price": item["price"],
                    "image_url": item.get("image_url", ""),
                    "restaurant_id": item["restaurant_id"],
                    "restaurant_name": restaurant.get("name", "Unknown") if restaurant else "Unknown",
                    "restaurant_cuisine": restaurant.get("cuisine", []) if restaurant else [],
                    "tags": item.get("tags", []),
                    "spice_level": item.get("spice_level", "medium"),
                    "is_vegetarian": item.get("is_vegetarian", False),
                    "is_vegan": item.get("is_vegan", False),
                    "average_rating": item.get("average_rating", 4.0),
                    "recommendation_score": round(scored["score"], 2)
                })
            
            return reorder_items, new_recommendations
            
        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return [], []
    
    def _check_dietary_compatibility(self, item: Dict, dietary_restrictions: List[str]) -> bool:
        """Check if item is compatible with user's dietary restrictions"""
        if not dietary_restrictions:
            return True
        
        # STRICT checking for dietary restrictions
        for restriction in dietary_restrictions:
            restriction_lower = restriction.lower()
            
            if restriction_lower == "vegetarian":
                if not item.get("is_vegetarian", False):
                    return False
            
            elif restriction_lower == "vegan":
                if not item.get("is_vegan", False):
                    return False
            
            elif restriction_lower == "halal":
                if not item.get("is_halal", True):  # Default to halal if not specified
                    return False
            
            elif restriction_lower == "gluten-free":
                tags = [tag.lower() for tag in item.get("tags", [])]
                if "gluten" in tags or "wheat" in tags:
                    return False
        
        return True


async def initialize_embeddings(db):
    """Initialize embeddings for all menu items"""
    engine = RecommendationEngine(db)
    count = await engine.generate_item_embeddings()
    logger.info(f"Initialized {count} item embeddings")
    return count
