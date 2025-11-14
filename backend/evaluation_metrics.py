"""
Comprehensive Evaluation Metrics for Recommendation System
All 6 metrics requested for FYP:
1. Precision - How many recommended items are relevant?
2. Recall - How many relevant items were recommended?
3. NDCG - Ranking quality
4. Hit Rate - Did we recommend at least 1 item user liked?
5. Coverage - % of items we can recommend
6. Diversity - Variety of recommendations
"""

import asyncio
import numpy as np
from motor.motor_asyncio import AsyncIOMotorClient
from collections import defaultdict
import os
from dotenv import load_dotenv
from datetime import datetime
import json
import math

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "voice_guide")

BASE_URL = "http://127.0.0.1:8001"


class RecommendationEvaluator:
    """Evaluate recommendation system with all 6 metrics"""
    
    def __init__(self, db):
        self.db = db
        self.metrics = {}
    
    async def get_ground_truth(self, user_id: str, k: int = 10):
        """
        Get ground truth - items user actually liked (rating >= 4)
        """
        ratings_cursor = self.db.ratings.find(
            {"user_id": user_id, "rating": {"$gte": 4}},
            {"_id": 0, "menu_item_id": 1, "rating": 1}
        ).sort([("rating", -1)])
        
        liked_items = await ratings_cursor.to_list(None)
        return [item["menu_item_id"] for item in liked_items[:k]]
    
    async def get_recommendations(self, user_id: str, k: int = 10):
        """
        Get top-k recommendations from the system
        (In real implementation, this would call the recommendation engine)
        """
        # For evaluation, we'll simulate getting recommendations
        # In production, this would call your actual recommendation API
        
        # Get user's order history
        orders = await self.db.orders.find(
            {"user_id": user_id, "order_status": "Delivered"},
            {"_id": 0, "items": 1}
        ).to_list(None)
        
        ordered_items = set()
        for order in orders:
            for item in order.get("items", []):
                ordered_items.add(item["menu_item_id"])
        
        # Get items user hasn't ordered
        all_items_cursor = self.db.menu_items.find(
            {"available": True},
            {"_id": 0, "id": 1}
        )
        all_items = await all_items_cursor.to_list(None)
        
        new_items = [item["id"] for item in all_items if item["id"] not in ordered_items]
        
        # Return top-k (in reality, these would be sorted by recommendation score)
        return new_items[:k]
    
    def calculate_precision_at_k(self, recommended: list, relevant: list, k: int = 10):
        """
        Precision@K = (# of recommended items that are relevant) / k
        Measures accuracy of recommendations
        """
        recommended_k = recommended[:k]
        hits = len(set(recommended_k) & set(relevant))
        precision = hits / k if k > 0 else 0
        return precision
    
    def calculate_recall_at_k(self, recommended: list, relevant: list, k: int = 10):
        """
        Recall@K = (# of recommended items that are relevant) / (total # of relevant items)
        Measures completeness of recommendations
        """
        recommended_k = recommended[:k]
        hits = len(set(recommended_k) & set(relevant))
        recall = hits / len(relevant) if len(relevant) > 0 else 0
        return recall
    
    def calculate_ndcg_at_k(self, recommended: list, relevant: list, k: int = 10):
        """
        NDCG@K (Normalized Discounted Cumulative Gain)
        Measures ranking quality - higher ranking of relevant items = better
        """
        recommended_k = recommended[:k]
        
        # DCG (Discounted Cumulative Gain)
        dcg = 0.0
        for i, item_id in enumerate(recommended_k):
            if item_id in relevant:
                # rel = 1 if relevant, 0 if not
                dcg += 1.0 / math.log2(i + 2)  # i+2 because positions start at 1
        
        # IDCG (Ideal DCG) - best possible ranking
        idcg = 0.0
        for i in range(min(len(relevant), k)):
            idcg += 1.0 / math.log2(i + 2)
        
        # NDCG
        ndcg = dcg / idcg if idcg > 0 else 0.0
        return ndcg
    
    def calculate_hit_rate_at_k(self, recommended: list, relevant: list, k: int = 10):
        """
        Hit Rate@K = Did we recommend at least 1 relevant item?
        Binary metric: 1 if yes, 0 if no
        """
        recommended_k = recommended[:k]
        hit = 1 if len(set(recommended_k) & set(relevant)) > 0 else 0
        return hit
    
    async def calculate_coverage(self, all_recommendations: list):
        """
        Coverage = (# of unique items recommended) / (total # of items in catalog)
        Measures variety - can we recommend diverse items?
        """
        unique_recommended = set()
        for rec_list in all_recommendations:
            unique_recommended.update(rec_list)
        
        total_items = await self.db.menu_items.count_documents({"available": True})
        
        coverage = len(unique_recommended) / total_items if total_items > 0 else 0
        return coverage
    
    def calculate_diversity_at_k(self, recommended: list, item_features: dict, k: int = 10):
        """
        Diversity@K = Average pairwise distance between recommended items
        Measures variety in recommendations (different restaurants, cuisines, etc.)
        """
        recommended_k = recommended[:k]
        
        if len(recommended_k) < 2:
            return 0.0
        
        # Calculate pairwise diversity
        diversity_sum = 0.0
        pair_count = 0
        
        for i in range(len(recommended_k)):
            for j in range(i + 1, len(recommended_k)):
                item1_id = recommended_k[i]
                item2_id = recommended_k[j]
                
                # Get features for both items
                feat1 = item_features.get(item1_id, {})
                feat2 = item_features.get(item2_id, {})
                
                # Calculate distance (different restaurant = 1, same = 0)
                if feat1.get("restaurant_id") != feat2.get("restaurant_id"):
                    diversity_sum += 1.0
                
                pair_count += 1
        
        diversity = diversity_sum / pair_count if pair_count > 0 else 0.0
        return diversity
    
    async def evaluate_all_metrics(self, k: int = 10):
        """
        Evaluate all 6 metrics for all users
        """
        print("\n" + "="*80)
        print("COMPREHENSIVE RECOMMENDATION EVALUATION")
        print("="*80)
        
        # Get all users with ratings
        users_cursor = self.db.ratings.distinct("user_id")
        user_ids = await users_cursor
        
        print(f"\nEvaluating {len(user_ids)} users with ratings...")
        
        # Collect metrics for all users
        precision_scores = []
        recall_scores = []
        ndcg_scores = []
        hit_rate_scores = []
        all_recommendations = []
        
        # Get item features for diversity calculation
        items_cursor = self.db.menu_items.find(
            {"available": True},
            {"_id": 0, "id": 1, "restaurant_id": 1, "tags": 1}
        )
        items = await items_cursor.to_list(None)
        item_features = {item["id"]: item for item in items}
        
        diversity_scores = []
        
        for i, user_id in enumerate(user_ids[:50], 1):  # Evaluate first 50 users
            # Get ground truth (items user liked)
            relevant_items = await self.get_ground_truth(user_id, k)
            
            if not relevant_items:
                continue  # Skip users with no liked items
            
            # Get recommendations
            recommended_items = await self.get_recommendations(user_id, k)
            
            if not recommended_items:
                continue  # Skip if no recommendations
            
            all_recommendations.append(recommended_items)
            
            # Calculate all metrics
            precision = self.calculate_precision_at_k(recommended_items, relevant_items, k)
            recall = self.calculate_recall_at_k(recommended_items, relevant_items, k)
            ndcg = self.calculate_ndcg_at_k(recommended_items, relevant_items, k)
            hit_rate = self.calculate_hit_rate_at_k(recommended_items, relevant_items, k)
            diversity = self.calculate_diversity_at_k(recommended_items, item_features, k)
            
            precision_scores.append(precision)
            recall_scores.append(recall)
            ndcg_scores.append(ndcg)
            hit_rate_scores.append(hit_rate)
            diversity_scores.append(diversity)
            
            if i % 10 == 0:
                print(f"  Progress: {i}/50 users evaluated...")
        
        # Calculate coverage
        coverage = await self.calculate_coverage(all_recommendations)
        
        # Calculate average metrics
        results = {
            "precision_at_k": {
                "mean": np.mean(precision_scores) if precision_scores else 0,
                "std": np.std(precision_scores) if precision_scores else 0,
                "description": "Accuracy of recommendations"
            },
            "recall_at_k": {
                "mean": np.mean(recall_scores) if recall_scores else 0,
                "std": np.std(recall_scores) if recall_scores else 0,
                "description": "Completeness of recommendations"
            },
            "ndcg_at_k": {
                "mean": np.mean(ndcg_scores) if ndcg_scores else 0,
                "std": np.std(ndcg_scores) if ndcg_scores else 0,
                "description": "Ranking quality"
            },
            "hit_rate_at_k": {
                "mean": np.mean(hit_rate_scores) if hit_rate_scores else 0,
                "std": np.std(hit_rate_scores) if hit_rate_scores else 0,
                "description": "% of users with at least 1 relevant recommendation"
            },
            "coverage": {
                "value": coverage,
                "description": "% of catalog items that can be recommended"
            },
            "diversity_at_k": {
                "mean": np.mean(diversity_scores) if diversity_scores else 0,
                "std": np.std(diversity_scores) if diversity_scores else 0,
                "description": "Variety in recommendations (different restaurants)"
            },
            "k": k,
            "users_evaluated": len(precision_scores),
            "timestamp": datetime.now().isoformat()
        }
        
        self.metrics = results
        return results
    
    def print_results(self):
        """Print evaluation results in a formatted way"""
        if not self.metrics:
            print("No metrics available. Run evaluate_all_metrics() first.")
            return
        
        print("\n" + "="*80)
        print("EVALUATION RESULTS")
        print("="*80)
        
        print(f"\n📊 Evaluated {self.metrics['users_evaluated']} users")
        print(f"   Top-K: {self.metrics['k']}")
        print()
        
        print(f"1. PRECISION@{self.metrics['k']}: {self.metrics['precision_at_k']['mean']:.4f} (±{self.metrics['precision_at_k']['std']:.4f})")
        print(f"   → {self.metrics['precision_at_k']['description']}")
        print(f"   → {self.metrics['precision_at_k']['mean']*100:.2f}% of recommended items are relevant")
        print()
        
        print(f"2. RECALL@{self.metrics['k']}: {self.metrics['recall_at_k']['mean']:.4f} (±{self.metrics['recall_at_k']['std']:.4f})")
        print(f"   → {self.metrics['recall_at_k']['description']}")
        print(f"   → Found {self.metrics['recall_at_k']['mean']*100:.2f}% of all relevant items")
        print()
        
        print(f"3. NDCG@{self.metrics['k']}: {self.metrics['ndcg_at_k']['mean']:.4f} (±{self.metrics['ndcg_at_k']['std']:.4f})")
        print(f"   → {self.metrics['ndcg_at_k']['description']}")
        print(f"   → Ranking quality score: {self.metrics['ndcg_at_k']['mean']*100:.2f}%")
        print()
        
        print(f"4. HIT RATE@{self.metrics['k']}: {self.metrics['hit_rate_at_k']['mean']:.4f} (±{self.metrics['hit_rate_at_k']['std']:.4f})")
        print(f"   → {self.metrics['hit_rate_at_k']['description']}")
        print(f"   → {self.metrics['hit_rate_at_k']['mean']*100:.2f}% of users got at least 1 relevant item")
        print()
        
        print(f"5. COVERAGE: {self.metrics['coverage']['value']:.4f}")
        print(f"   → {self.metrics['coverage']['description']}")
        print(f"   → Can recommend {self.metrics['coverage']['value']*100:.2f}% of catalog")
        print()
        
        print(f"6. DIVERSITY@{self.metrics['k']}: {self.metrics['diversity_at_k']['mean']:.4f} (±{self.metrics['diversity_at_k']['std']:.4f})")
        print(f"   → {self.metrics['diversity_at_k']['description']}")
        print(f"   → Variety score: {self.metrics['diversity_at_k']['mean']*100:.2f}%")
        print()
    
    def save_results(self, filename: str = None):
        """Save results to JSON file"""
        if not self.metrics:
            print("No metrics to save")
            return
        
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"evaluation_metrics_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.metrics, f, indent=2)
        
        print(f"✅ Results saved to: {filename}")
        
        # Also save a formatted text report
        txt_filename = filename.replace('.json', '.txt')
        with open(txt_filename, 'w') as f:
            f.write("RECOMMENDATION SYSTEM EVALUATION REPORT\n")
            f.write("="*80 + "\n\n")
            f.write(f"Generated: {self.metrics['timestamp']}\n")
            f.write(f"Users Evaluated: {self.metrics['users_evaluated']}\n")
            f.write(f"Top-K: {self.metrics['k']}\n\n")
            f.write("="*80 + "\n\n")
            
            f.write("METRICS:\n\n")
            f.write(f"1. Precision@{self.metrics['k']}: {self.metrics['precision_at_k']['mean']:.4f}\n")
            f.write(f"   {self.metrics['precision_at_k']['mean']*100:.2f}% of recommended items are relevant\n\n")
            
            f.write(f"2. Recall@{self.metrics['k']}: {self.metrics['recall_at_k']['mean']:.4f}\n")
            f.write(f"   Found {self.metrics['recall_at_k']['mean']*100:.2f}% of all relevant items\n\n")
            
            f.write(f"3. NDCG@{self.metrics['k']}: {self.metrics['ndcg_at_k']['mean']:.4f}\n")
            f.write(f"   Ranking quality: {self.metrics['ndcg_at_k']['mean']*100:.2f}%\n\n")
            
            f.write(f"4. Hit Rate@{self.metrics['k']}: {self.metrics['hit_rate_at_k']['mean']:.4f}\n")
            f.write(f"   {self.metrics['hit_rate_at_k']['mean']*100:.2f}% of users got relevant recommendations\n\n")
            
            f.write(f"5. Coverage: {self.metrics['coverage']['value']:.4f}\n")
            f.write(f"   Can recommend {self.metrics['coverage']['value']*100:.2f}% of catalog\n\n")
            
            f.write(f"6. Diversity@{self.metrics['k']}: {self.metrics['diversity_at_k']['mean']:.4f}\n")
            f.write(f"   Variety score: {self.metrics['diversity_at_k']['mean']*100:.2f}%\n\n")
            
            f.write("="*80 + "\n\n")
            f.write("FOR FYP PRESENTATION:\n\n")
            f.write("These metrics demonstrate:\n")
            f.write("- High precision means accurate recommendations\n")
            f.write("- High recall means comprehensive coverage\n")
            f.write("- High NDCG means good ranking quality\n")
            f.write("- High hit rate means most users find relevant items\n")
            f.write("- High coverage means system isn't biased to few items\n")
            f.write("- High diversity means varied recommendations\n")
        
        print(f"✅ Text report saved to: {txt_filename}")


async def run_evaluation():
    """Run complete evaluation"""
    print("\n🔍 Starting Recommendation System Evaluation...")
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    evaluator = RecommendationEvaluator(db)
    
    # Evaluate with top-10 recommendations
    await evaluator.evaluate_all_metrics(k=10)
    
    # Print results
    evaluator.print_results()
    
    # Save results
    evaluator.save_results()
    
    client.close()
    
    print("\n✅ Evaluation complete!\n")


if __name__ == "__main__":
    asyncio.run(run_evaluation())
