import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { MapPin, CreditCard, Plus, Check, ArrowLeft } from 'lucide-react';
import { toast } from 'sonner';
import LoadingSpinner from './ui/LoadingSpinner';
import { useCart } from './CartContext';
import AddAddressModal from './AddAddressModal';

const CheckoutPage = () => {
  const navigate = useNavigate();
  const { cart, fetchCart, clearCart } = useCart();
  const [addresses, setAddresses] = useState([]);
  const [selectedAddress, setSelectedAddress] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('cod');
  const [specialInstructions, setSpecialInstructions] = useState('');
  const [loading, setLoading] = useState(false);
  const [showAddAddress, setShowAddAddress] = useState(false);
  
  useEffect(() => {
    fetchCart();
    fetchAddresses();
  }, []);

  const fetchAddresses = async () => {
    try {
      const response = await axios.get('/api/user/addresses');
      setAddresses(response.data.addresses);
      
      // Auto-select default address
      const defaultAddr = response.data.addresses.find(addr => addr.is_default);
      if (defaultAddr) {
        setSelectedAddress(defaultAddr.id);
      }
    } catch (error) {
      console.error('Error fetching addresses:', error);
    }
  };

  const handleAddressAdded = (newAddress) => {
    setAddresses([...addresses, newAddress]);
    setSelectedAddress(newAddress.id);
    setShowAddAddress(false);
  };

  const calculatePricing = () => {
    const subtotal = cart.totalAmount;
    const deliveryFee = 50; // Default delivery fee
    const tax = subtotal * 0.05; // 5% tax
    const total = subtotal + deliveryFee + tax;
    
    return { subtotal, deliveryFee, tax, total };
  };

  const handlePlaceOrder = async () => {
    if (!selectedAddress) {
      toast.error('Please select a delivery address');
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post('/api/orders/checkout', {
        address_id: selectedAddress,
        payment_method: paymentMethod,
        special_instructions: specialInstructions
      });

      toast.success('Order placed successfully!');
      await clearCart();
      navigate('/orders', { 
        state: { 
          orderPlaced: true,
          orderData: response.data.order
        }
      });
    } catch (error) {
      const message = error.response?.data?.detail || 'Failed to place order';
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  if (cart.loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="large" />
      </div>
    );
  }

  if (cart.items.length === 0) {
    return (
      <div className="min-h-screen py-8 px-4">
        <div className="max-w-2xl mx-auto text-center">
          <h1 className="text-3xl font-bold text-gray-900 mb-4">Your cart is empty</h1>
          <p className="text-gray-600 mb-8">Add some items to proceed with checkout</p>
          <button
            onClick={() => navigate('/restaurants')}
            className="btn-primary px-8 py-3"
          >
            Browse Restaurants
          </button>
        </div>
      </div>
    );
  }

  const pricing = calculatePricing();

  return (
    <div className="min-h-screen py-8 px-4 bg-gray-50" data-testid="checkout-page">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center space-x-4 mb-8">
          <button
            onClick={() => navigate(-1)}
            className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
          >
            <ArrowLeft className="w-6 h-6 text-gray-600" />
          </button>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Checkout</h1>
            <p className="text-gray-600">Complete your order</p>
          </div>
        </div>

        <div className="grid lg:grid-cols-3 gap-8">
          {/* Left Column - Order Details */}
          <div className="lg:col-span-2 space-y-6">
            {/* Delivery Address */}
            <div className="bg-white rounded-2xl p-6 shadow-sm">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center space-x-3">
                  <MapPin className="w-6 h-6 text-orange-500" />
                  <h2 className="text-xl font-semibold text-gray-900">Delivery Address</h2>
                </div>
                <button
                  onClick={() => setShowAddAddress(true)}
                  className="flex items-center space-x-2 text-orange-500 hover:text-orange-600 font-medium"
                  data-testid="add-address-btn"
                >
                  <Plus className="w-4 h-4" />
                  <span>Add New</span>
                </button>
              </div>

              {addresses.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-gray-600 mb-4">No saved addresses</p>
                  <button
                    onClick={() => setShowAddAddress(true)}
                    className="btn-primary px-6 py-3"
                  >
                    Add Address
                  </button>
                </div>
              ) : (
                <div className="space-y-3">
                  {addresses.map((address) => (
                    <div
                      key={address.id}
                      className={`p-4 border-2 rounded-xl cursor-pointer transition-all ${
                        selectedAddress === address.id
                          ? 'border-orange-500 bg-orange-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                      onClick={() => setSelectedAddress(address.id)}
                      data-testid={`address-${address.id}`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center space-x-2 mb-1">
                            <span className="font-semibold text-gray-900">{address.label}</span>
                            {address.is_default && (
                              <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full">
                                Default
                              </span>
                            )}
                          </div>
                          <p className="text-gray-600 text-sm">
                            {address.street_address}, {address.area}, {address.district}
                          </p>
                          <p className="text-gray-500 text-sm">Phone: {address.phone}</p>
                        </div>
                        {selectedAddress === address.id && (
                          <Check className="w-5 h-5 text-orange-500" />
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Payment Method */}
            <div className="bg-white rounded-2xl p-6 shadow-sm">
              <div className="flex items-center space-x-3 mb-6">
                <CreditCard className="w-6 h-6 text-orange-500" />
                <h2 className="text-xl font-semibold text-gray-900">Payment Method</h2>
              </div>

              <div className="space-y-3">
                <div
                  className={`p-4 border-2 rounded-xl cursor-pointer transition-all ${
                    paymentMethod === 'cod'
                      ? 'border-orange-500 bg-orange-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                  onClick={() => setPaymentMethod('cod')}
                  data-testid="payment-cod"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-semibold text-gray-900">Cash on Delivery</p>
                      <p className="text-sm text-gray-600">Pay when your order arrives</p>
                    </div>
                    {paymentMethod === 'cod' && (
                      <Check className="w-5 h-5 text-orange-500" />
                    )}
                  </div>
                </div>

                <div
                  className={`p-4 border-2 rounded-xl cursor-pointer transition-all ${
                    paymentMethod === 'easypaisa'
                      ? 'border-orange-500 bg-orange-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                  onClick={() => setPaymentMethod('easypaisa')}
                  data-testid="payment-easypaisa"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-semibold text-gray-900">EasyPaisa</p>
                      <p className="text-sm text-gray-600">Pay digitally via EasyPaisa</p>
                    </div>
                    {paymentMethod === 'easypaisa' && (
                      <Check className="w-5 h-5 text-orange-500" />
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Special Instructions */}
            <div className="bg-white rounded-2xl p-6 shadow-sm">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Special Instructions (Optional)</h3>
              <textarea
                value={specialInstructions}
                onChange={(e) => setSpecialInstructions(e.target.value)}
                placeholder="Any special instructions for your order..."
                className="w-full p-4 border border-gray-300 rounded-xl resize-none h-24 focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
                data-testid="special-instructions"
              />
            </div>
          </div>

          {/* Right Column - Order Summary */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-2xl p-6 shadow-sm sticky top-8">
              <h3 className="text-xl font-semibold text-gray-900 mb-6">Order Summary</h3>
              
              {/* Order Items */}
              <div className="space-y-4 mb-6">
                {cart.items.map((item) => (
                  <div key={item.id} className="flex items-center space-x-3">
                    <img
                      src={item.menu_item.image || 'https://images.unsplash.com/photo-1546833999-b9f581a1996d?w=60'}
                      alt={item.menu_item.name}
                      className="w-12 h-12 rounded-lg object-cover"
                    />
                    <div className="flex-1">
                      <p className="font-medium text-gray-900 text-sm">{item.menu_item.name}</p>
                      <p className="text-xs text-gray-600">Qty: {item.quantity}</p>
                    </div>
                    <p className="font-semibold text-gray-900">PKR {item.item_total}</p>
                  </div>
                ))}
              </div>

              {/* Pricing Breakdown */}
              <div className="border-t border-gray-200 pt-4 space-y-3">
                <div className="flex justify-between text-gray-600">
                  <span>Subtotal</span>
                  <span>PKR {pricing.subtotal}</span>
                </div>
                <div className="flex justify-between text-gray-600">
                  <span>Delivery Fee</span>
                  <span>PKR {pricing.deliveryFee}</span>
                </div>
                <div className="flex justify-between text-gray-600">
                  <span>Tax (5%)</span>
                  <span>PKR {pricing.tax.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-xl font-bold text-gray-900 pt-3 border-t border-gray-200">
                  <span>Total</span>
                  <span>PKR {pricing.total.toFixed(2)}</span>
                </div>
              </div>

              {/* Place Order Button */}
              <button
                onClick={handlePlaceOrder}
                disabled={!selectedAddress || loading}
                className="w-full btn-primary py-4 text-lg font-semibold mt-6 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                data-testid="place-order-btn"
              >
                {loading ? (
                  <LoadingSpinner size="small" color="white" />
                ) : (
                  `Place Order • PKR ${pricing.total.toFixed(2)}`
                )}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Add Address Modal */}
      {showAddAddress && (
        <AddAddressModal
          onClose={() => setShowAddAddress(false)}
          onAddressAdded={handleAddressAdded}
        />
      )}
    </div>
  );
};

export default CheckoutPage;