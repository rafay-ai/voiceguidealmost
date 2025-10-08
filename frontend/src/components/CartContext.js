import React, { createContext, useContext, useReducer, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';

const CartContext = createContext();

const cartReducer = (state, action) => {
  switch (action.type) {
    case 'SET_CART':
      return {
        ...state,
        items: action.payload.items,
        totalAmount: action.payload.total_amount,
        itemCount: action.payload.item_count,
        restaurantId: action.payload.restaurant_id
      };
    case 'ADD_ITEM':
      return {
        ...state,
        itemCount: state.itemCount + 1
      };
    case 'CLEAR_CART':
      return {
        items: [],
        totalAmount: 0,
        itemCount: 0,
        restaurantId: null
      };
    case 'SET_LOADING':
      return {
        ...state,
        loading: action.payload
      };
    default:
      return state;
  }
};

export const CartProvider = ({ children }) => {
  const [cart, dispatch] = useReducer(cartReducer, {
    items: [],
    totalAmount: 0,
    itemCount: 0,
    restaurantId: null,
    loading: false
  });

  const fetchCart = async () => {
    try {
      dispatch({ type: 'SET_LOADING', payload: true });
      const response = await axios.get('/api/cart');
      dispatch({ type: 'SET_CART', payload: response.data });
    } catch (error) {
      console.error('Error fetching cart:', error);
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  };

  const addToCart = async (menuItemId, restaurantId, quantity = 1, specialInstructions = '') => {
    try {
      await axios.post('/api/cart/add', {
        menu_item_id: menuItemId,
        restaurant_id: restaurantId,
        quantity,
        special_instructions: specialInstructions
      });
      
      dispatch({ type: 'ADD_ITEM' });
      await fetchCart();
      toast.success('Item added to cart!');
      return true;
    } catch (error) {
      const message = error.response?.data?.detail || 'Failed to add item to cart';
      toast.error(message);
      return false;
    }
  };

  const updateCartItem = async (itemId, quantity) => {
    try {
      await axios.put(`/api/cart/${itemId}`, null, {
        params: { quantity }
      });
      await fetchCart();
      toast.success('Cart updated!');
    } catch (error) {
      toast.error('Failed to update cart');
    }
  };

  const removeFromCart = async (itemId) => {
    try {
      await axios.delete(`/api/cart/${itemId}`);
      await fetchCart();
      toast.success('Item removed from cart');
    } catch (error) {
      toast.error('Failed to remove item');
    }
  };

  const clearCart = async () => {
    try {
      await axios.delete('/api/cart/clear');
      dispatch({ type: 'CLEAR_CART' });
      toast.success('Cart cleared');
    } catch (error) {
      toast.error('Failed to clear cart');
    }
  };

  return (
    <CartContext.Provider value={{
      cart,
      fetchCart,
      addToCart,
      updateCartItem,
      removeFromCart,
      clearCart
    }}>
      {children}
    </CartContext.Provider>
  );
};

export const useCart = () => {
  const context = useContext(CartContext);
  if (!context) {
    throw new Error('useCart must be used within a CartProvider');
  }
  return context;
};

export default CartContext;