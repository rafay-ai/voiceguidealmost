"""
Rating System Implementation
- User can rate menu items 1-5 stars
- Low rated items (< 3) won't be recommended again
- Integrated with Matrix Factorization
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ItemRating(BaseModel):
    """Item rating model"""
    id: str
    user_id: str
    menu_item_id: str
    restaurant_id: str
    rating: int  # 1-5 stars
    review: Optional[str] = ""
    created_at: datetime = datetime.now()


# Add to server.py - Rating endpoints

@api_router.post("/ratings")
async def rate_menu_item(
    menu_item_id: str,
    rating: int,
    review: str = "",
    current_user: User = Depends(get_current_user)
):
    """
    Rate a menu item (1-5 stars)
    - Rating < 3 means user disliked it
    - These items won't be recommended again
    """
    try:
        # Validate rating
        if rating < 1 or rating > 5:
            raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
        
        # Get menu item
        menu_item = await db.menu_items.find_one({"id": menu_item_id}, {"_id": 0})
        if not menu_item:
            raise HTTPException(status_code=404, detail="Menu item not found")
        
        # Check if user already rated this item
        existing_rating = await db.ratings.find_one({
            "user_id": current_user.id,
            "menu_item_id": menu_item_id
        })
        
        rating_data = {
            "id": str(uuid.uuid4()),
            "user_id": current_user.id,
            "menu_item_id": menu_item_id,
            "restaurant_id": menu_item["restaurant_id"],
            "rating": rating,
            "review": review,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        if existing_rating:
            # Update existing rating
            await db.ratings.update_one(
                {"user_id": current_user.id, "menu_item_id": menu_item_id},
                {"$set": rating_data}
            )
            message = "Rating updated successfully"
        else:
            # Create new rating
            await db.ratings.insert_one(rating_data)
            message = "Rating added successfully"
        
        # Update item's average rating
        await update_item_average_rating(menu_item_id)
        
        return {
            "message": message,
            "rating": rating_data
        }
        
    except Exception as e:
        logging.error(f"Error rating item: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/ratings/my-ratings")
async def get_my_ratings(
    current_user: User = Depends(get_current_user)
):
    """Get all ratings by current user"""
    try:
        ratings_cursor = db.ratings.find(
            {"user_id": current_user.id},
            {"_id": 0}
        ).sort([("created_at", -1)])
        
        ratings = await ratings_cursor.to_list(None)
        
        # Get menu item details for each rating
        for rating in ratings:
            menu_item = await db.menu_items.find_one(
                {"id": rating["menu_item_id"]},
                {"_id": 0, "name": 1, "image_url": 1}
            )
            if menu_item:
                rating["menu_item_name"] = menu_item.get("name")
                rating["menu_item_image"] = menu_item.get("image_url")
        
        return {"ratings": ratings}
        
    except Exception as e:
        logging.error(f"Error getting ratings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def update_item_average_rating(menu_item_id: str):
    """Update menu item's average rating"""
    try:
        # Get all ratings for this item
        ratings_cursor = db.ratings.find(
            {"menu_item_id": menu_item_id},
            {"_id": 0, "rating": 1}
        )
        ratings = await ratings_cursor.to_list(None)
        
        if ratings:
            avg_rating = sum(r["rating"] for r in ratings) / len(ratings)
            await db.menu_items.update_one(
                {"id": menu_item_id},
                {"$set": {
                    "average_rating": round(avg_rating, 2),
                    "total_ratings": len(ratings)
                }}
            )
    except Exception as e:
        logging.error(f"Error updating average rating: {e}")


async def get_user_disliked_items(user_id: str) -> list:
    """
    Get items user has rated < 3 stars (disliked)
    These should not be recommended again
    """
    try:
        disliked_cursor = db.ratings.find(
            {"user_id": user_id, "rating": {"$lt": 3}},
            {"_id": 0, "menu_item_id": 1}
        )
        disliked = await disliked_cursor.to_list(None)
        return [item["menu_item_id"] for item in disliked]
    except Exception as e:
        logging.error(f"Error getting disliked items: {e}")
        return []
