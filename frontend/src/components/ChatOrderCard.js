import React, { useState } from 'react';
import { Star, MapPin, CreditCard, Check, X, Plus } from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';
import LoadingSpinner from './ui/LoadingSpinner';

const ChatOrderCard = ({ items, address, onOrderSuccess, onClose }) => {
  const [selectedItems, setSelectedItems] = useState({});
  const [loading, setLoading] = useState(false);

  const toggleItem = (itemId) => {
    setSelectedItems(prev => ({
      ...prev,
      [itemId]: !prev[itemId]
    }));
  };

  const getSelectedItems = () => {
    return Object.keys(selectedItems).filter(id => selectedItems[id]);
  };

  const calculateTotal = () => {
    return getSelectedItems().reduce((total, itemId) => {
      const item = items.find(i => i.id === itemId);
      return total + (item ? item.price : 0);
    }, 0);
  };

  const handleQuickOrder = async () => {
    const selectedIds = getSelectedItems();
    if (selectedIds.length === 0) {
      toast.error('Please select at least one item');
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post('/api/chat/order', {
        menu_item_ids: selectedIds,
        quantities: selectedIds.map(() => 1),
        use_default_address: true,
        payment_method: 'cod'
      });

      if (response.data.success) {
        toast.success('Order placed successfully! 🎉');
        onOrderSuccess(response.data);
        onClose();
      } else {
        toast.error(response.data.message);
      }
    } catch (error) {
      console.error('Error placing order:', error);
      toast.error('Failed to place order');
    } finally {
      setLoading(false);
    }
  };

  if (!items || items.length === 0) return null;

  return (
    <div className="bg-white rounded-xl shadow-lg border border-gray-200 p-4 mt-3 max-w-sm">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <div className="w-8 h-8 bg-orange-500 rounded-full flex items-center justify-center">
            <Check className="w-4 h-4 text-white" />
          </div>
          <h3 className="font-semibold text-gray-900">Quick Order</h3>
        </div>
        <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded-full">
          <X className="w-4 h-4 text-gray-500" />
        </button>
      </div>

      {/* Items Selection */}
      <div className="space-y-3 mb-4">
        {items.map((item) => (
          <div
            key={item.id}
            onClick={() => toggleItem(item.id)}
            className={`p-3 border rounded-lg cursor-pointer transition-all ${
              selectedItems[item.id] 
                ? 'border-orange-300 bg-orange-50' 
                : 'border-gray-200 hover:border-gray-300'
            }`}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center space-x-2 mb-1">
                  <p className="font-medium text-sm text-gray-900">{item.name}</p>
                  {selectedItems[item.id] && (
                    <Check className="w-4 h-4 text-orange-600" />
                  )}
                </div>
                <p className="text-xs text-gray-600">{item.restaurant_name}</p>
                <div className="flex items-center space-x-2 mt-1">
                  <span className="text-lg font-bold text-orange-600">PKR {item.price}</span>
                  <div className="flex items-center space-x-1">
                    <Star className="w-3 h-3 text-yellow-400 fill-current" />
                    <span className="text-xs">{item.average_rating || '4.5'}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Delivery Info */}
      {address && (
        <div className="bg-gray-50 p-3 rounded-lg mb-4">
          <div className="flex items-start space-x-2">
            <MapPin className="w-4 h-4 text-gray-500 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-gray-900">Delivery Address</p>
              <p className="text-xs text-gray-600">{address.area}, {address.district}</p>
            </div>
          </div>
          <div className="flex items-start space-x-2 mt-2">
            <CreditCard className="w-4 h-4 text-gray-500 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-gray-900">Cash on Delivery</p>
              <p className="text-xs text-gray-600">Pay when delivered</p>
            </div>
          </div>
        </div>
      )}

      {/* Order Button */}
      <div className="space-y-3">
        {getSelectedItems().length > 0 && (
          <div className="flex justify-between items-center text-sm">
            <span className="text-gray-600">{getSelectedItems().length} items selected</span>
            <span className="font-semibold">Total: PKR {calculateTotal()}</span>
          </div>
        )}
        
        <button
          onClick={handleQuickOrder}
          disabled={getSelectedItems().length === 0 || loading}
          className="w-full btn-primary py-3 font-semibold disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
        >
          {loading ? (
            <LoadingSpinner size="small" color="white" />
          ) : (
            <>
              <Plus className="w-4 h-4" />
              <span>
                {getSelectedItems().length === 0 
                  ? 'Select items to order' 
                  : `Order ${getSelectedItems().length} item${getSelectedItems().length !== 1 ? 's' : ''}`
                }
              </span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};

export default ChatOrderCard;