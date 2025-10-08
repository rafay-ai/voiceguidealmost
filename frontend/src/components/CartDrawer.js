import React, { useState, useEffect } from 'react';
import { X, Plus, Minus, ShoppingBag, Trash2 } from 'lucide-react';
import { useCart } from './CartContext';
import { useNavigate } from 'react-router-dom';
import LoadingSpinner from './ui/LoadingSpinner';

const CartDrawer = ({ isOpen, onClose }) => {
  const { cart, updateCartItem, removeFromCart, clearCart } = useCart();
  const navigate = useNavigate();

  const handleQuantityChange = async (itemId, currentQuantity, change) => {
    const newQuantity = Math.max(0, currentQuantity + change);
    if (newQuantity === 0) {
      await removeFromCart(itemId);
    } else {
      await updateCartItem(itemId, newQuantity);
    }
  };

  const handleCheckout = () => {
    onClose();
    navigate('/checkout');
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black bg-opacity-50 z-40"
        onClick={onClose}
      />
      
      {/* Drawer */}
      <div className="fixed right-0 top-0 h-full w-full max-w-md bg-white shadow-2xl z-50 transform transition-transform duration-300 ease-in-out">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 bg-gradient-to-r from-orange-500 to-rose-500">
          <div className="flex items-center space-x-3">
            <ShoppingBag className="w-6 h-6 text-white" />
            <h2 className="text-xl font-bold text-white">Your Cart</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-full bg-white bg-opacity-20 hover:bg-opacity-30 transition-colors"
            data-testid="close-cart"
          >
            <X className="w-5 h-5 text-white" />
          </button>
        </div>

        {/* Content */}
        <div className="flex flex-col h-full">
          {cart.loading ? (
            <div className="flex-1 flex items-center justify-center">
              <LoadingSpinner size="large" />
            </div>
          ) : cart.items.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
              <div className="w-24 h-24 bg-gray-100 rounded-full flex items-center justify-center mb-6">
                <ShoppingBag className="w-8 h-8 text-gray-400" />
              </div>
              <h3 className="text-xl font-semibold text-gray-600 mb-2">Your cart is empty</h3>
              <p className="text-gray-500 mb-6">Add some delicious items to get started!</p>
              <button
                onClick={onClose}
                className="btn-primary px-6 py-3"
              >
                Continue Shopping
              </button>
            </div>
          ) : (
            <>
              {/* Cart Items */}
              <div className="flex-1 overflow-y-auto p-6">
                <div className="space-y-6">
                  {cart.items.map((item) => (
                    <div key={item.id} className="bg-gray-50 rounded-xl p-4" data-testid={`cart-item-${item.id}`}>
                      <div className="flex items-start space-x-4">
                        <img
                          src={item.menu_item.image || 'https://images.unsplash.com/photo-1546833999-b9f581a1996d?w=100'}
                          alt={item.menu_item.name}
                          className="w-16 h-16 rounded-lg object-cover"
                        />
                        <div className="flex-1">
                          <h3 className="font-semibold text-gray-900 mb-1">{item.menu_item.name}</h3>
                          <p className="text-sm text-gray-600 mb-2">{item.restaurant.name}</p>
                          <p className="text-lg font-bold text-orange-600">PKR {item.menu_item.price}</p>
                          
                          {item.special_instructions && (
                            <p className="text-xs text-gray-500 mt-1 italic">
                              Note: {item.special_instructions}
                            </p>
                          )}
                        </div>
                      </div>
                      
                      <div className="flex items-center justify-between mt-4">
                        <div className="flex items-center space-x-3">
                          <button
                            onClick={() => handleQuantityChange(item.id, item.quantity, -1)}
                            className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center hover:bg-gray-300 transition-colors"
                            data-testid={`decrease-${item.id}`}
                          >
                            <Minus className="w-4 h-4" />
                          </button>
                          <span className="font-semibold text-lg w-8 text-center">{item.quantity}</span>
                          <button
                            onClick={() => handleQuantityChange(item.id, item.quantity, 1)}
                            className="w-8 h-8 rounded-full bg-orange-500 text-white flex items-center justify-center hover:bg-orange-600 transition-colors"
                            data-testid={`increase-${item.id}`}
                          >
                            <Plus className="w-4 h-4" />
                          </button>
                        </div>
                        
                        <div className="flex items-center space-x-3">
                          <span className="font-bold text-lg">PKR {item.item_total}</span>
                          <button
                            onClick={() => removeFromCart(item.id)}
                            className="p-2 text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                            data-testid={`remove-${item.id}`}
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Footer */}
              <div className="border-t border-gray-200 p-6 bg-gray-50">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-lg font-semibold text-gray-900">Total</span>
                  <span className="text-2xl font-bold text-orange-600">PKR {cart.totalAmount}</span>
                </div>
                
                <div className="space-y-3">
                  <button
                    onClick={handleCheckout}
                    className="w-full btn-primary py-4 text-lg font-semibold"
                    data-testid="checkout-button"
                  >
                    Proceed to Checkout ({cart.itemCount} items)
                  </button>
                  
                  <button
                    onClick={clearCart}
                    className="w-full text-gray-600 hover:text-red-600 transition-colors font-medium"
                    data-testid="clear-cart"
                  >
                    Clear Cart
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </>
  );
};

export default CartDrawer;