import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import axios from 'axios';
import { Toaster, toast } from 'sonner';
import HomePage from './components/HomePage';
import LoginPage from './components/LoginPage';
import RegisterPage from './components/RegisterPage';
import DashboardPage from './components/DashboardPage';
import ChatPage from './components/ChatPage';
import RestaurantsPage from './components/RestaurantsPage';
import ProfilePage from './components/ProfilePage';
import CheckoutPage from './components/CheckoutPage';
import OrdersPage from './components/OrdersPage';
import Navigation from './components/Navigation';
import PreferencesOnboarding from './components/PreferencesOnboarding';
import { CartProvider } from './components/CartContext';
import LoadingSpinner from './components/ui/LoadingSpinner';
import './App.css';

// Configure axios defaults
const API_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';
axios.defaults.baseURL = API_URL;

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [showOnboarding, setShowOnboarding] = useState(false);

  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      fetchUserProfile();
    } else {
      setLoading(false);
    }
  }, [token]);

  const fetchUserProfile = async () => {
    try {
      const response = await axios.get('/api/user/profile');
      const userData = response.data;
      setUser(userData);
      
      // Show onboarding if preferences not set
      if (!userData.preferences_set) {
        setShowOnboarding(true);
      }
    } catch (error) {
      console.error('Error fetching user profile:', error);
      // Clear invalid token
      logout();
    } finally {
      setLoading(false);
    }
  };

  const login = (userData, authToken) => {
    localStorage.setItem('token', authToken);
    setToken(authToken);
    setUser(userData);
    axios.defaults.headers.common['Authorization'] = `Bearer ${authToken}`;
    toast.success(`Welcome ${userData.preferences_set ? 'back' : 'to Voice Guide'}, ${userData.username}!`);
    
    // Show onboarding for new users
    if (!userData.preferences_set) {
      setShowOnboarding(true);
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    delete axios.defaults.headers.common['Authorization'];
    toast.info('You have been logged out');
  };

  const handleOnboardingComplete = () => {
    setShowOnboarding(false);
    setUser(prev => ({ ...prev, preferences_set: true }));
    toast.success('Great! Your preferences have been saved. Let\'s start ordering! 🎉');
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-orange-50 via-rose-50 to-pink-50 flex items-center justify-center">
        <LoadingSpinner size="large" />
      </div>
    );
  }

  return (
    <Router>
      <CartProvider>
        <div className="min-h-screen bg-gradient-to-br from-orange-50 via-rose-50 to-pink-50">
          <Toaster 
            position="top-right" 
            richColors 
            closeButton
            toastOptions={{
              duration: 4000,
              style: {
                background: 'white',
                color: '#333',
                border: '1px solid #e5e7eb',
                borderRadius: '12px',
              }
            }}
          />
          
          {user && <Navigation user={user} onLogout={logout} />}
          
          <Routes>
            {!user ? (
              <>
                <Route path="/" element={<HomePage />} />
                <Route path="/login" element={<LoginPage onLogin={login} />} />
                <Route path="/register" element={<RegisterPage onLogin={login} />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </>
            ) : (
              <>
                <Route path="/dashboard" element={<DashboardPage user={user} />} />
                <Route path="/chat" element={<ChatPage user={user} />} />
                <Route path="/restaurants" element={<RestaurantsPage user={user} />} />
                <Route path="/profile" element={<ProfilePage user={user} onUserUpdate={setUser} />} />
                <Route path="/checkout" element={<CheckoutPage />} />
                <Route path="/orders" element={<OrdersPage />} />
                <Route path="/" element={<Navigate to="/dashboard" replace />} />
                <Route path="*" element={<Navigate to="/dashboard" replace />} />
              </>
            )}
          </Routes>
          
          {/* Preferences Onboarding Modal */}
          {showOnboarding && (
            <PreferencesOnboarding onComplete={handleOnboardingComplete} />
          )}
        </div>
      </CartProvider>
    </Router>
  );
}

export default App;