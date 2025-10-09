import React, { useState, useEffect } from 'react';
import { Star, Clock, Plus, Check } from 'lucide-react';
import axios from 'axios';
import LoadingSpinner from './ui/LoadingSpinner';

const RestaurantCard = ({ restaurant, onOrderFromChat, compact = true }) => {
  const [menuItems, setMenuItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedItems, setSelectedItems] = useState({});
  const [showMenu, setShowMenu] = useState(false);

  const fetchMenuItems = async () => {
    if (showMenu && menuItems.length === 0) {
      setLoading(true);
      try {
        const response = await axios.get(`/api/restaurants/${restaurant.id}/menu`);
        setMenuItems(response.data.menu_items.slice(0, 5)); // Show top 5 items
      } catch (error) {
        console.error('Error fetching menu:', error);
      } finally {
        setLoading(false);
      }
    }
  };

  useEffect(() => {
    fetchMenuItems();
  }, [showMenu]);

  const toggleItem = (itemId) => {
    setSelectedItems(prev => ({
      ...prev,
      [itemId]: !prev[itemId]
    }));
  };

  const handleQuickOrder = () => {
    const selectedIds = Object.keys(selectedItems).filter(id => selectedItems[id]);
    if (selectedIds.length > 0) {
      onOrderFromChat(selectedIds, restaurant);
    }
  };

  const getSelectedCount = () => {
    return Object.values(selectedItems).filter(Boolean).length;
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden mb-4 max-w-sm">
      {/* Restaurant Header */}
      <div className="p-4">
        <div className="flex items-start justify-between mb-2">
          <div className="flex-1">
            <h3 className="font-semibold text-gray-900 text-sm">{restaurant.name}</h3>
            <p className="text-xs text-gray-600 line-clamp-1">{restaurant.description}</p>
          </div>
          <span className={`text-xs px-2 py-1 rounded-full ${
            restaurant.price_range === 'Budget' ? 'bg-green-100 text-green-800' :
            restaurant.price_range === 'Moderate' ? 'bg-yellow-100 text-yellow-800' : 
            'bg-purple-100 text-purple-800'
          }`}>
            {restaurant.price_range}
          </span>
        </div>
        
        <div className="flex items-center justify-between text-xs text-gray-500 mb-3">
          <div className="flex items-center space-x-1">
            <Star className="w-3 h-3 text-yellow-400 fill-current" />
            <span>{restaurant.rating}</span>
          </div>
          <div className="flex items-center space-x-1">
            <Clock className="w-3 h-3" />
            <span>{restaurant.delivery_time}</span>
          </div>
          <div>PKR {restaurant.delivery_fee} delivery</div>
        </div>

        {/* Quick Order Button */}
        <button
          onClick={() => setShowMenu(!showMenu)}
          className={`w-full py-2 px-3 rounded-lg text-sm font-medium transition-all ${
            showMenu 
              ? 'bg-gray-100 text-gray-700' 
              : 'bg-orange-500 text-white hover:bg-orange-600'
          }`}
        >
          {showMenu ? 'Hide Menu' : 'Quick Order'}
        </button>
      </div>

      {/* Menu Items */}
      {showMenu && (
        <div className="border-t border-gray-200 p-4 bg-gray-50">
          {loading ? (
            <div className="flex justify-center py-4">
              <LoadingSpinner size="small" />
            </div>
          ) : (
            <div className="space-y-3">
              {menuItems.slice(0, 4).map((item) => (
                <div
                  key={item.id}
                  className={`flex items-center justify-between p-2 rounded-lg cursor-pointer transition-all ${
                    selectedItems[item.id] 
                      ? 'bg-orange-100 border-orange-300' 
                      : 'bg-white hover:bg-gray-50'
                  } border`}
                  onClick={() => toggleItem(item.id)}
                >
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900">{item.name}</p>
                    <p className="text-xs text-gray-600">PKR {item.price}</p>
                  </div>
                  <div className="ml-2">
                    {selectedItems[item.id] ? (
                      <Check className="w-4 h-4 text-orange-600" />
                    ) : (
                      <Plus className="w-4 h-4 text-gray-400" />
                    )}
                  </div>
                </div>
              ))}
              
              {getSelectedCount() > 0 && (
                <button
                  onClick={handleQuickOrder}
                  className="w-full mt-3 py-2 bg-orange-500 text-white rounded-lg text-sm font-semibold hover:bg-orange-600 transition-colors"
                >
                  Order {getSelectedCount()} Item{getSelectedCount() !== 1 ? 's' : ''}
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default RestaurantCard;