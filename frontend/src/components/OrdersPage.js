import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Clock, MapPin, CreditCard, Package, RefreshCw, Star } from 'lucide-react';
import { toast } from 'sonner';
import LoadingSpinner from './ui/LoadingSpinner';

const OrdersPage = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [reorderingId, setReorderingId] = useState(null);

  useEffect(() => {
    fetchOrders();
    
    // Show success message if coming from checkout
    if (location.state?.orderPlaced) {
      const orderData = location.state.orderData;
      toast.success(
        <div>
          <p className="font-semibold">Order placed successfully! 🎉</p>
          <p className="text-sm">Order #{orderData.order_number}</p>
          <p className="text-sm">Check your email for confirmation</p>
        </div>,
        { duration: 5000 }
      );
    }
  }, [location.state]);

  const fetchOrders = async () => {
    try {
      setLoading(true);
      const response = await axios.get('/api/orders');
      setOrders(response.data.orders);
    } catch (error) {
      console.error('Error fetching orders:', error);
      toast.error('Failed to load orders');
    } finally {
      setLoading(false);
    }
  };

  const handleReorder = async (orderId) => {
    setReorderingId(orderId);
    try {
      await axios.post(`/api/orders/${orderId}/reorder`);
      toast.success('Items added to cart! You can now checkout.');
      navigate('/checkout');
    } catch (error) {
      const message = error.response?.data?.detail || 'Failed to reorder';
      toast.error(message);
    } finally {
      setReorderingId(null);
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      'placed': 'bg-blue-100 text-blue-800',
      'confirmed': 'bg-yellow-100 text-yellow-800',
      'preparing': 'bg-purple-100 text-purple-800',
      'on_the_way': 'bg-orange-100 text-orange-800',
      'delivered': 'bg-green-100 text-green-800',
      'cancelled': 'bg-red-100 text-red-800'
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="large" />
      </div>
    );
  }

  return (
    <div className="min-h-screen py-8 px-4" data-testid="orders-page">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="font-display text-4xl font-bold text-gray-900 mb-4">Your Orders</h1>
          <p className="text-xl text-gray-600">Track and manage your food orders</p>
        </div>

        {/* Orders List */}
        {orders.length === 0 ? (
          <div className="text-center py-16">
            <div className="w-24 h-24 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <Package className="w-8 h-8 text-gray-400" />
            </div>
            <h3 className="text-2xl font-semibold text-gray-600 mb-4">No orders yet</h3>
            <p className="text-gray-500 mb-8">When you place your first order, it will appear here</p>
            <button
              onClick={() => navigate('/restaurants')}
              className="btn-primary px-8 py-3"
            >
              Start Ordering
            </button>
          </div>
        ) : (
          <div className="space-y-6">
            {orders.map((order) => (
              <div key={order.id} className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden" data-testid={`order-${order.id}`}>
                {/* Order Header */}
                <div className="bg-gradient-to-r from-orange-500 to-rose-500 p-6 text-white">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between">
                    <div>
                      <h3 className="text-xl font-semibold mb-1">Order #{order.order_number}</h3>
                      <p className="text-orange-100">{order.restaurant?.name}</p>
                    </div>
                    <div className="mt-4 sm:mt-0 text-right">
                      <div className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(order.order_status)} bg-white bg-opacity-20 text-white`}>
                        {order.order_status.replace('_', ' ').toUpperCase()}
                      </div>
                      <p className="text-orange-100 text-sm mt-1">
                        {formatDate(order.created_at)}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="p-6">
                  {/* Order Items */}
                  <div className="mb-6">
                    <h4 className="text-lg font-semibold text-gray-900 mb-4">Order Items</h4>
                    <div className="space-y-3">
                      {order.items.map((item, index) => (
                        <div key={index} className="flex items-center space-x-4 p-3 bg-gray-50 rounded-xl">
                          <img
                            src={item.menu_item?.image || 'https://images.unsplash.com/photo-1546833999-b9f581a1996d?w=60'}
                            alt={item.menu_item?.name}
                            className="w-12 h-12 rounded-lg object-cover"
                          />
                          <div className="flex-1">
                            <h5 className="font-semibold text-gray-900">{item.menu_item?.name}</h5>
                            <p className="text-sm text-gray-600">Quantity: {item.quantity}</p>
                            {item.special_instructions && (
                              <p className="text-xs text-gray-500 italic">Note: {item.special_instructions}</p>
                            )}
                          </div>
                          <div className="text-right">
                            <p className="font-semibold text-gray-900">PKR {item.price * item.quantity}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Order Details Grid */}
                  <div className="grid md:grid-cols-2 gap-6 mb-6">
                    {/* Delivery Info */}
                    <div className="bg-gray-50 p-4 rounded-xl">
                      <div className="flex items-start space-x-3">
                        <MapPin className="w-5 h-5 text-orange-500 mt-0.5" />
                        <div>
                          <h5 className="font-semibold text-gray-900 mb-1">Delivery Address</h5>
                          <p className="text-sm text-gray-600">
                            {order.delivery_address.area}, {order.delivery_address.district}
                          </p>
                          <p className="text-sm text-gray-600">{order.delivery_address.street_address}</p>
                          <p className="text-sm text-gray-500">Phone: {order.delivery_address.phone}</p>
                        </div>
                      </div>
                    </div>

                    {/* Payment Info */}
                    <div className="bg-gray-50 p-4 rounded-xl">
                      <div className="flex items-start space-x-3">
                        <CreditCard className="w-5 h-5 text-orange-500 mt-0.5" />
                        <div>
                          <h5 className="font-semibold text-gray-900 mb-1">Payment</h5>
                          <p className="text-sm text-gray-600 capitalize">
                            {order.payment_method === 'cod' ? 'Cash on Delivery' : order.payment_method}
                          </p>
                          <p className="text-sm text-gray-500 capitalize">
                            Status: {order.payment_status.replace('_', ' ')}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Timing Info */}
                  {order.estimated_delivery_time && (
                    <div className="bg-blue-50 p-4 rounded-xl mb-6">
                      <div className="flex items-center space-x-3">
                        <Clock className="w-5 h-5 text-blue-500" />
                        <div>
                          <p className="font-medium text-blue-900">
                            Estimated Delivery: {formatDate(order.estimated_delivery_time)}
                          </p>
                          {order.actual_delivery_time && (
                            <p className="text-sm text-blue-700">
                              Delivered: {formatDate(order.actual_delivery_time)}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Order Total & Actions */}
                  <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center pt-6 border-t border-gray-200">
                    <div>
                      <p className="text-2xl font-bold text-gray-900">
                        Total: PKR {order.pricing.total}
                      </p>
                      <p className="text-sm text-gray-500">
                        Including delivery fee and tax
                      </p>
                    </div>
                    
                    <div className="flex space-x-3 mt-4 sm:mt-0">
                      <button
                        onClick={() => handleReorder(order.id)}
                        disabled={reorderingId === order.id}
                        className="flex items-center space-x-2 px-4 py-2 text-orange-600 border border-orange-600 rounded-lg hover:bg-orange-50 transition-colors disabled:opacity-50"
                        data-testid={`reorder-${order.id}`}
                      >
                        {reorderingId === order.id ? (
                          <LoadingSpinner size="small" color="orange" />
                        ) : (
                          <RefreshCw className="w-4 h-4" />
                        )}
                        <span>Reorder</span>
                      </button>
                      
                      {order.order_status === 'delivered' && (
                        <button className="flex items-center space-x-2 px-4 py-2 text-yellow-600 border border-yellow-600 rounded-lg hover:bg-yellow-50 transition-colors">
                          <Star className="w-4 h-4" />
                          <span>Rate</span>
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default OrdersPage;