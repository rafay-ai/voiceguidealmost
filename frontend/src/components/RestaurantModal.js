import React, { useState, useEffect } from 'react';
import { X, Star, Clock, Plus, Minus } from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';
import LoadingSpinner from './ui/LoadingSpinner';
import { useCart } from './CartContext';

const RestaurantModal = ({ restaurant, onClose }) => {
  const [menuItems, setMenuItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('');
  const [itemQuantities, setItemQuantities] = useState({});
  const { addToCart } = useCart();

  useEffect(() => {
    fetchMenuItems();
  }, [restaurant.id]);

  const fetchMenuItems = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`/api/restaurants/${restaurant.id}/menu`);
      const items = response.data.menu_items;
      setMenuItems(items);
      
      // Extract categories
      const uniqueCategories = [...new Set(items.map(item => item.category))];
      setCategories(uniqueCategories);
    } catch (error) {
      console.error('Error fetching menu items:', error);
      toast.error('Failed to load menu items');
    } finally {
      setLoading(false);
    }
  };

  const filteredItems = selectedCategory 
    ? menuItems.filter(item => item.category === selectedCategory)
    : menuItems;

  const updateQuantity = (itemId, quantity) => {
    setItemQuantities(prev => ({
      ...prev,
      [itemId]: Math.max(0, quantity)
    }));
  };

  const handleAddToCart = async (item) => {
    const quantity = itemQuantities[item.id] || 1;
    const success = await addToCart(item.id, restaurant.id, quantity);
    if (success) {
      setItemQuantities(prev => ({ ...prev, [item.id]: 0 }));
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

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="relative">
          <img 
            src={restaurant.image || `https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80`}
            alt={restaurant.name}
            className="w-full h-48 object-cover"
          />
          <div className="absolute inset-0 bg-black bg-opacity-40"></div>
          
          {/* Close Button */}
          <button
            onClick={onClose}
            className="absolute top-4 right-4 p-2 bg-white rounded-full hover:bg-gray-100 transition-colors"
            data-testid="close-restaurant-modal"
          >
            <X className="w-5 h-5 text-gray-600" />
          </button>
          
          {/* Restaurant Info */}
          <div className="absolute bottom-0 left-0 right-0 p-6 text-white">
            <h2 className="text-3xl font-bold mb-2">{restaurant.name}</h2>
            <p className="text-gray-200 mb-3">{restaurant.description}</p>
            <div className="flex items-center space-x-6 text-sm">
              <div className="flex items-center space-x-1">
                <Star className="w-4 h-4 fill-current text-yellow-400" />
                <span>{restaurant.rating}</span>
              </div>
              <div className="flex items-center space-x-1">
                <Clock className="w-4 h-4" />
                <span>{restaurant.delivery_time}</span>
              </div>
              <div>
                <span className={`px-2 py-1 rounded-full text-xs ${
                  restaurant.price_range === 'Budget' ? 'bg-green-500' :
                  restaurant.price_range === 'Moderate' ? 'bg-yellow-500' : 'bg-purple-500'
                }`}>
                  {restaurant.price_range}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="flex flex-col h-[calc(90vh-12rem)]">
          {/* Category Filter */}
          <div className="p-6 border-b border-gray-200">
            <div className="flex space-x-3 overflow-x-auto">
              <button
                onClick={() => setSelectedCategory('')}
                className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-all ${
                  selectedCategory === ''
                    ? 'bg-orange-500 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
                data-testid="category-all"
              >
                All Items
              </button>
              {categories.map((category) => (
                <button
                  key={category}
                  onClick={() => setSelectedCategory(category)}
                  className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-all ${
                    selectedCategory === category
                      ? 'bg-orange-500 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                  data-testid={`category-${category.toLowerCase().replace(' ', '-')}`}
                >
                  {category}
                </button>
              ))}
            </div>
          </div>

          {/* Menu Items */}
          <div className="flex-1 overflow-y-auto p-6">
            {loading ? (
              <div className="flex justify-center py-12">
                <LoadingSpinner size="large" />
              </div>
            ) : filteredItems.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-gray-500 text-lg">No items found in this category</p>
              </div>
            ) : (
              <div className="grid gap-6">
                {filteredItems.map((item) => {
                  const spiceInfo = getSpiceIndicator(item.spice_level);
                  const quantity = itemQuantities[item.id] || 0;
                  
                  return (
                    <div key={item.id} className="bg-gray-50 rounded-xl p-6" data-testid={`menu-item-${item.id}`}>
                      <div className="grid md:grid-cols-4 gap-4">
                        {/* Item Image */}
                        <div className="md:col-span-1">
                          <img
                            src={item.image || 'https://images.unsplash.com/photo-1546833999-b9f581a1996d?w=200'}
                            alt={item.name}
                            className="w-full h-24 md:h-full object-cover rounded-lg"
                          />
                        </div>
                        
                        {/* Item Details */}
                        <div className="md:col-span-2">
                          <div className="flex items-start justify-between mb-2">
                            <h3 className="text-lg font-semibold text-gray-900">{item.name}</h3>
                            <div className="flex items-center space-x-2 ml-4">
                              {item.is_vegetarian && <span className="text-green-600 text-sm">🥬</span>}
                              {item.is_halal && <span className="text-blue-600 text-sm">☪️</span>}
                            </div>
                          </div>
                          
                          <p className="text-gray-600 text-sm mb-3 line-clamp-2">{item.description}</p>
                          
                          <div className="flex items-center space-x-4 text-sm text-gray-500">
                            <div className="flex items-center space-x-1">
                              <Clock className="w-4 h-4" />
                              <span>{item.preparation_time} min</span>
                            </div>
                            <div className="flex items-center space-x-1">
                              <span>{spiceInfo.text}</span>
                              <span className="capitalize">{item.spice_level}</span>
                            </div>
                            <div className="flex items-center space-x-1">
                              <Star className="w-4 h-4 text-yellow-400 fill-current" />
                              <span>{item.average_rating || 'N/A'}</span>
                            </div>
                          </div>
                        </div>
                        
                        {/* Price and Add to Cart */}
                        <div className="md:col-span-1 flex flex-col justify-between">
                          <div className="text-right">
                            <p className="text-2xl font-bold text-orange-600 mb-2">PKR {item.price}</p>
                            {item.tags && item.tags.length > 0 && (
                              <div className="flex flex-wrap gap-1 justify-end mb-3">
                                {item.tags.slice(0, 2).map((tag, index) => (
                                  <span key={index} className="text-xs bg-gray-200 text-gray-700 px-2 py-1 rounded-full">
                                    {tag}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                          
                          <div className="flex flex-col space-y-3">
                            {/* Quantity Selector */}
                            <div className="flex items-center justify-center space-x-3">
                              <button
                                onClick={() => updateQuantity(item.id, quantity - 1)}
                                disabled={quantity <= 0}
                                className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center hover:bg-gray-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                data-testid={`decrease-${item.id}`}
                              >
                                <Minus className="w-4 h-4" />
                              </button>
                              <span className="font-semibold text-lg w-8 text-center">{quantity}</span>
                              <button
                                onClick={() => updateQuantity(item.id, quantity + 1)}
                                className="w-8 h-8 rounded-full bg-orange-500 text-white flex items-center justify-center hover:bg-orange-600 transition-colors"
                                data-testid={`increase-${item.id}`}
                              >
                                <Plus className="w-4 h-4" />
                              </button>
                            </div>
                            
                            {/* Add to Cart Button */}
                            <button
                              onClick={() => handleAddToCart(item)}
                              disabled={!item.available || quantity === 0}
                              className="w-full btn-primary py-2 text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-1"
                              data-testid={`add-to-cart-${item.id}`}
                            >
                              <Plus className="w-3 h-3" />
                              <span>
                                {quantity === 0 ? 'Add to Cart' : `Add ${quantity} to Cart`}
                              </span>
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default RestaurantModal;