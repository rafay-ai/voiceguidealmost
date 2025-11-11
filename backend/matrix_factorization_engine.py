"""
Matrix Factorization Based Recommendation Engine
Uses Collaborative Filtering with SVD for personalized recommendations
FREE - No API calls, runs locally
"""

import os
import logging
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize
from scipy.sparse import csr_matrix
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MatrixFactorizationEngine:
    """
    Recommendation engine using Matrix Factorization (Collaborative Filtering)
    - User-Item interaction matrix
    - SVD decomposition for latent factors
    - Predicts ratings for unseen items
    """
    
    def __init__(self, db):
        self.db = db
        self.model = None
        self.user_item_matrix = None
        self.user_mapping = {}
        self.item_mapping = {}
        self.reverse_item_mapping = {}
        self.n_factors = 50  # Number of latent factors
        
    async def build_user_item_matrix(self):
        """Build interaction matrix from order history"""
        try:
            logger.info("Building user-item interaction matrix...")
            
            # Get ALL orders (not just delivered/completed)
            # This allows training on all historical data
            orders_cursor = self.db.orders.find(
                {},  # No filter - get all orders
                {"_id": 0, "user_id": 1, "items": 1}
            )
            orders = await orders_cursor.to_list(None)
            
            logger.info(f"Found {len(orders)} orders for matrix building")
            
            if not orders:
                logger.warning("No orders found for matrix factorization")
                return False
            
            # Build interaction data
            interactions = []
            for order in orders:
                user_id = order["user_id"]
                for item in order.get("items", []):
                    menu_item_id = item["menu_item_id"]
                    quantity = item.get("quantity", 1)
                    # Rating = quantity (implicit feedback)
                    interactions.append({
                        "user_id": user_id,
                        "item_id": menu_item_id,
                        "rating": quantity
                    })
            
            if not interactions:
                logger.warning("No interactions found")
                return False
            
            # Create DataFrame
            df = pd.DataFrame(interactions)
            
            # Aggregate ratings (sum of quantities for same user-item pairs)
            df = df.groupby(["user_id", "item_id"])["rating"].sum().reset_index()
            
            # Create user and item mappings
            unique_users = df["user_id"].unique()
            unique_items = df["item_id"].unique()
            
            self.user_mapping = {user_id: idx for idx, user_id in enumerate(unique_users)}
            self.item_mapping = {item_id: idx for idx, item_id in enumerate(unique_items)}
            self.reverse_item_mapping = {idx: item_id for item_id, idx in self.item_mapping.items()}
            
            # Map to indices
            df["user_idx"] = df["user_id"].map(self.user_mapping)
            df["item_idx"] = df["item_id"].map(self.item_mapping)
            
            # Create sparse matrix
            n_users = len(self.user_mapping)
            n_items = len(self.item_mapping)
            
            self.user_item_matrix = csr_matrix(
                (df["rating"], (df["user_idx"], df["item_idx"])),
                shape=(n_users, n_items)
            )
            
            # Train SVD model
            n_factors = min(self.n_factors, min(n_users, n_items) - 1)
            self.model = TruncatedSVD(n_components=n_factors, random_state=42)
            self.model.fit(self.user_item_matrix)
            
            logger.info(f"Matrix factorization model trained: {n_users} users, {n_items} items, {n_factors} factors")
            return True
            
        except Exception as e:
            logger.error(f"Error building user-item matrix: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    async def get_user_order_history(self, user_id: str, days: int = 30) -> Dict:
        """Analyze user's order history"""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            orders_cursor = self.db.orders.find(
                {
                    "user_id": user_id,
                    "created_at": {"$gte": cutoff_date}
                    # Removed status filter - use all orders
                },
                {"_id": 0}
            ).sort([("created_at", -1)])
            
            orders = await orders_cursor.to_list(None)
            
            if not orders:
                return {
                    "has_history": False,
                    "total_orders": 0,
                    "ordered_items": [],
                    "cuisine_preferences": {}
                }
            
            item_frequency = {}
            cuisine_frequency = {}
            
            for order in orders:
                restaurant = await self.db.restaurants.find_one(
                    {"id": order["restaurant_id"]},
                    {"_id": 0, "cuisine": 1, "name": 1}
                )
                
                if restaurant:
                    for cuisine in restaurant.get("cuisine", []):
                        cuisine_frequency[cuisine] = cuisine_frequency.get(cuisine, 0) + 1
                
                for item in order.get("items", []):
                    item_id = item["menu_item_id"]
                    if item_id not in item_frequency:
                        item_frequency[item_id] = {
                            "count": 0,
                            "last_ordered": order["created_at"],
                            "restaurant_id": order["restaurant_id"]
                        }
                    item_frequency[item_id]["count"] += item["quantity"]
            
            # Get top ordered items
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
                "cuisine_preferences": dict(sorted(cuisine_frequency.items(), key=lambda x: x[1], reverse=True))
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
        Get recommendations using Matrix Factorization
        Returns: (reorder_items, new_recommendations)
        """
        try:
            # Get order history
            order_history = await self.get_user_order_history(user_id, days=30)
            
            dietary_restrictions = user_preferences.get("dietary_restrictions", [])
            favorite_cuisines = user_preferences.get("favorite_cuisines", [])
            
            # REORDER ITEMS - from order history
            reorder_items = []
            if order_history["has_history"] and not exclude_ordered:
                for ordered in order_history["ordered_items"][:3]:
                    item = ordered["item"]
                    
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
            
            # NEW RECOMMENDATIONS using Matrix Factorization
            new_recommendations = []
            
            # Check if user exists in trained model
            user_has_cf_recs = False
            if self.model is not None and user_id in self.user_mapping:
                user_has_cf_recs = True
                user_idx = self.user_mapping[user_id]
                
                # Get user's latent vector
                user_vector = self.user_item_matrix[user_idx].toarray().reshape(1, -1)
                user_latent = self.model.transform(user_vector)
                
                # Reconstruct ratings for all items
                reconstructed = user_latent @ self.model.components_
                
                # Get items user hasn't ordered
                ordered_item_indices = self.user_item_matrix[user_idx].nonzero()[1]
                
                # Score all items
                item_scores = []
                for item_idx in range(len(self.reverse_item_mapping)):
                    if exclude_ordered and item_idx in ordered_item_indices:
                        continue
                    
                    predicted_rating = reconstructed[0, item_idx]
                    item_scores.append((item_idx, predicted_rating))
                
                # Sort by predicted rating
                item_scores.sort(key=lambda x: x[1], reverse=True)
                
                # Get top items
                for item_idx, score in item_scores[:limit * 3]:  # Get more to filter by dietary
                    item_id = self.reverse_item_mapping[item_idx]
                    
                    menu_item = await self.db.menu_items.find_one(
                        {"id": item_id, "available": True},
                        {"_id": 0}
                    )
                    
                    if not menu_item:
                        continue
                    
                    # Check dietary restrictions
                    if not self._check_dietary_compatibility(menu_item, dietary_restrictions):
                        continue
                    
                    # Get restaurant
                    restaurant = await self.db.restaurants.find_one(
                        {"id": menu_item["restaurant_id"]},
                        {"_id": 0, "cuisine": 1, "name": 1}
                    )
                    
                    new_recommendations.append({
                        "id": menu_item["id"],
                        "name": menu_item["name"],
                        "description": menu_item.get("description", ""),
                        "price": menu_item["price"],
                        "image_url": menu_item.get("image_url", ""),
                        "restaurant_id": menu_item["restaurant_id"],
                        "restaurant_name": restaurant.get("name", "Unknown") if restaurant else "Unknown",
                        "restaurant_cuisine": restaurant.get("cuisine", []) if restaurant else [],
                        "tags": menu_item.get("tags", []),
                        "spice_level": menu_item.get("spice_level", "medium"),
                        "is_vegetarian": menu_item.get("is_vegetarian", False),
                        "is_vegan": menu_item.get("is_vegan", False),
                        "average_rating": menu_item.get("average_rating", 4.0),
                        "recommendation_score": round(float(score), 2),
                        "method": "matrix_factorization"
                    })
                    
                    if len(new_recommendations) >= limit:
                        break
            
            # Fallback to content-based if no CF recommendations
            if not user_has_cf_recs or len(new_recommendations) < limit:
                logger.info(f"Using content-based fallback for user {user_id}")
                fallback_items = await self._get_content_based_recommendations(
                    user_preferences,
                    dietary_restrictions,
                    favorite_cuisines,
                    order_history,
                    limit - len(new_recommendations)
                )
                new_recommendations.extend(fallback_items)
            
            return reorder_items, new_recommendations
            
        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return [], []
    
    async def _get_content_based_recommendations(
        self,
        user_preferences: Dict,
        dietary_restrictions: List[str],
        favorite_cuisines: List[str],
        order_history: Dict,
        limit: int
    ) -> List[Dict]:
        """Fallback content-based recommendations for new users"""
        try:
            recommendations = []
            
            # Build query based on preferences
            query = {"available": True}
            
            # Get items matching favorite cuisines
            restaurant_ids = []
            if favorite_cuisines:
                restaurants_cursor = self.db.restaurants.find(
                    {"cuisine": {"$in": favorite_cuisines}, "is_active": True},
                    {"_id": 0, "id": 1}
                )
                restaurants = await restaurants_cursor.to_list(None)
                restaurant_ids = [r["id"] for r in restaurants]
            
            if restaurant_ids:
                query["restaurant_id"] = {"$in": restaurant_ids}
            
            # Get items
            items_cursor = self.db.menu_items.find(query, {"_id": 0}).limit(limit * 3)
            items = await items_cursor.to_list(None)
            
            for item in items:
                if not self._check_dietary_compatibility(item, dietary_restrictions):
                    continue
                
                restaurant = await self.db.restaurants.find_one(
                    {"id": item["restaurant_id"]},
                    {"_id": 0, "cuisine": 1, "name": 1}
                )
                
                # Calculate simple score
                score = item.get("average_rating", 4.0) * 10
                score += item.get("order_count", 0) / 10
                
                recommendations.append({
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
                    "recommendation_score": round(score, 2),
                    "method": "content_based"
                })
                
                if len(recommendations) >= limit:
                    break
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error in content-based recommendations: {e}")
            return []
    
    def _check_dietary_compatibility(self, item: Dict, dietary_restrictions: List[str]) -> bool:
        """Check if item is compatible with dietary restrictions"""
        if not dietary_restrictions:
            return True
        
        for restriction in dietary_restrictions:
            restriction_lower = restriction.lower()
            
            if restriction_lower == "vegetarian":
                if not item.get("is_vegetarian", False):
                    return False
            
            elif restriction_lower == "vegan":
                if not item.get("is_vegan", False):
                    return False
            
            elif restriction_lower == "halal":
                if not item.get("is_halal", True):
                    return False
            
            elif restriction_lower == "gluten-free":
                tags = [tag.lower() for tag in item.get("tags", [])]
                if "gluten" in tags or "wheat" in tags:
                    return False
        
        return True
