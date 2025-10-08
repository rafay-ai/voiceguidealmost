import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { Star, Clock, Sparkles, MessageCircle, Store, TrendingUp, Plus } from 'lucide-react';
import { toast } from 'sonner';
import LoadingSpinner from './ui/LoadingSpinner';
import { useCart } from './CartContext';

const DashboardPage = ({ user }) => {
  const [recommendations, setRecommendations] = useState([]);
  const [cuisines, setCuisines] = useState([]);
  const [loading, setLoading] = useState(true);
  const [userOrders, setUserOrders] = useState([]);
  const { addToCart } = useCart();

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const [recommendationsRes, cuisinesRes, ordersRes] = await Promise.all([
        axios.get('/api/recommendations?limit=8'),
        axios.get('/api/cuisines'),
        axios.get('/api/orders?limit=5')
      ]);
      
      setRecommendations(recommendationsRes.data.recommendations);
      setCuisines(cuisinesRes.data.cuisines.slice(0, 6)); // Show 6 cuisines
      setUserOrders(ordersRes.data.orders);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      toast.error('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const getSpiceIndicator = (spiceLevel) => {
    const indicators = {
      mild: { color: 'text-green-500', text: '🌶️' },
      medium: { color: 'text-yellow-500', text: '🌶️🌶️' },
      hot: { color: 'text-orange-500', text: '🌶️🌶️🌶️' },
      very_hot: { color: 'text-red-500', text: '🌶️🌶️🌶️🌶️' }
    };
    return indicators[spiceLevel] || indicators.mild;
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="large" />
      </div>
    );
  }

  return (
    <div className="min-h-screen py-8 px-4" data-testid="dashboard-page">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Welcome Header */}
        <div className="text-center mb-12">
          <h1 className="font-display text-4xl lg:text-5xl font-bold text-gray-900 mb-4">
            Welcome back, <span className="text-transparent bg-clip-text bg-gradient-to-r from-orange-500 to-rose-500">{user.username}</span>!
          </h1>
          <p className="text-xl text-gray-600">What would you like to eat today?</p>
        </div>

        {/* Quick Actions */}
        <div className="grid md:grid-cols-3 gap-6 mb-12">
          <Link 
            to="/chat" 
            className="card-hover p-8 bg-gradient-to-br from-orange-500 to-rose-500 text-white rounded-2xl text-center"
            data-testid="quick-voice-order"
          >
            <MessageCircle className="w-12 h-12 mx-auto mb-4" />
            <h3 className="text-xl font-semibold mb-2">Voice Order</h3>
            <p className="text-orange-100">Tell us what you're craving</p>
          </Link>
          
          <Link 
            to="/restaurants" 
            className="card-hover p-8 bg-gradient-to-br from-blue-500 to-purple-500 text-white rounded-2xl text-center"
            data-testid="browse-restaurants"
          >
            <Store className="w-12 h-12 mx-auto mb-4" />
            <h3 className="text-xl font-semibold mb-2">Browse Restaurants</h3>
            <p className="text-blue-100">Explore all available options</p>
          </Link>
          
          <Link
            to="/orders"
            className="card-hover p-8 bg-gradient-to-br from-green-500 to-teal-500 text-white rounded-2xl text-center block"
          >
            <TrendingUp className="w-12 h-12 mx-auto mb-4" />
            <h3 className="text-xl font-semibold mb-2">{userOrders.length} Orders</h3>
            <p className="text-green-100">Your ordering history</p>
          </Link>
        </div>

        {/* User Stats */}
        <div className="grid md:grid-cols-3 gap-6 mb-12">
          <div className="glass p-6 rounded-2xl text-center">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Total Orders</h3>
            <p className="text-3xl font-bold text-orange-500">{userOrders.length}</p>
          </div>
          <div className="glass p-6 rounded-2xl text-center">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Favorite Cuisine</h3>
            <p className="text-xl font-medium text-gray-700">{user.favorite_cuisines?.[0] || 'Not set'}</p>
          </div>
          <div className="glass p-6 rounded-2xl text-center">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Last Order</h3>
            <p className="text-xl font-medium text-gray-700">
              {userOrders.length > 0 ? 
                new Date(userOrders[0].created_at).toLocaleDateString() : 
                'No orders yet'
              }
            </p>
          </div>
        </div>

        {/* Personalized Recommendations */}
        <section className="mb-12">
          <div className="flex items-center justify-between mb-8">
            <div className="flex items-center space-x-3">
              <Sparkles className="w-6 h-6 text-orange-500" />
              <h2 className="text-3xl font-bold text-gray-900">Recommended for You</h2>
            </div>
          </div>

          {recommendations.length > 0 ? (
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
              {recommendations.map((item) => {
                const spiceInfo = getSpiceIndicator(item.spice_level);
                return (
                  <div key={item.id} className="restaurant-card" data-testid={`recommendation-${item.id}`}>
                    <div className="relative">
                      <img 
                        src={item.image || 'https://images.unsplash.com/photo-1546833999-b9f581a1996d?ixlib=rb-4.0.3&auto=format&fit=crop&w=300&q=80'} 
                        alt={item.name}
                        className="w-full h-48 object-cover"
                      />
                      {item.recommendation_reason && (
                        <div className="absolute top-3 left-3">
                          <span className="recommendation-badge">
                            {item.recommendation_reason === 'Users with similar tastes also liked this' ? 'Similar Users' : 
                             item.recommendation_reason === 'Based on your preferences' ? 'For You' : 'Popular'}
                          </span>
                        </div>
                      )}
                      <div className="absolute top-3 right-3">
                        <span className="category-badge">{item.category}</span>
                      </div>
                    </div>
                    
                    <div className="p-4">
                      <h3 className="font-semibold text-lg text-gray-900 mb-2">{item.name}</h3>
                      <p className="text-gray-600 text-sm mb-3 line-clamp-2">{item.description}</p>
                      
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center space-x-2">
                          <div className="flex items-center">
                            {[...Array(5)].map((_, i) => (
                              <Star 
                                key={i} 
                                className={`w-4 h-4 ${i < Math.floor(item.average_rating) ? 'text-yellow-400 fill-current' : 'text-gray-300'}`} 
                              />
                            ))}
                          </div>
                          <span className="text-sm text-gray-600">({item.rating_count})</span>
                        </div>
                        <div className="flex items-center space-x-1">
                          <Clock className="w-4 h-4 text-gray-400" />
                          <span className="text-sm text-gray-600">{item.preparation_time} min</span>
                        </div>
                      </div>
                      
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <span className="text-xl font-bold text-gray-900">₹{item.price}</span>
                          <span className="text-sm">{spiceInfo.text}</span>
                        </div>
                        <button 
                          onClick={() => addToCart(item.id, item.restaurant_id)}
                          className="btn-primary px-4 py-2 text-sm flex items-center space-x-1"
                        >
                          <Plus className="w-3 h-3" />
                          <span>Add to Cart</span>
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-center py-12">
              <Sparkles className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-gray-600 mb-2">No recommendations yet</h3>
              <p className="text-gray-500 mb-4">Place some orders to get personalized recommendations!</p>
              <Link to="/restaurants" className="btn-primary">
                Browse Restaurants
              </Link>
            </div>
          )}
        </section>

        {/* Cuisine Categories */}
        <section>
          <div className="flex items-center justify-between mb-8">
            <h2 className="text-3xl font-bold text-gray-900">Popular Cuisines</h2>
            <Link to="/restaurants" className="text-orange-500 hover:text-orange-400 font-medium">
              View all →
            </Link>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4" data-testid="cuisine-grid">
            {cuisines.map((cuisine, index) => {
              const cuisineImages = {
                'Pakistani': '🍛',
                'Chinese': '🥢', 
                'Fast Food': '🍔',
                'Italian': '🍝',
                'Desserts': '🍰',
                'BBQ': '🥩',
                'Indian': '🍛',
                'Mexican': '🌮',
                'Thai': '🍜',
                'Japanese': '🍱'
              };
              
              const gradients = [
                'from-emerald-500 to-teal-600',
                'from-red-500 to-pink-600', 
                'from-yellow-500 to-orange-600',
                'from-blue-500 to-purple-600',
                'from-purple-500 to-pink-600',
                'from-orange-500 to-red-600'
              ];
              
              return (
                <Link
                  key={cuisine}
                  to={`/restaurants?cuisine=${encodeURIComponent(cuisine)}`}
                  className="card-hover"
                  data-testid={`cuisine-${cuisine.toLowerCase().replace(' ', '-')}`}
                >
                  <div className={`bg-gradient-to-br ${gradients[index % gradients.length]} p-6 rounded-2xl text-center text-white`}>
                    <div className="text-4xl mb-3">{cuisineImages[cuisine] || '🍽️'}</div>
                    <h3 className="font-semibold text-sm">{cuisine}</h3>
                  </div>
                </Link>
              );
            })}
          </div>
        </section>
      </div>
    </div>
  );
};

export default DashboardPage;