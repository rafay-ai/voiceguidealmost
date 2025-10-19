import React, { useState } from 'react';
import axios from 'axios';
import { User, Settings, Heart, Utensils, Shield, Save } from 'lucide-react';
import { toast } from 'sonner';
import LoadingSpinner from './ui/LoadingSpinner';

const ProfilePage = ({ user, onUserUpdate }) => {
  const [loading, setLoading] = useState(false);
  const [preferences, setPreferences] = useState({
    favorite_cuisines: user.favorite_cuisines || [],
    dietary_restrictions: user.dietary_restrictions || [],
    spice_preference: user.spice_preference || 'medium'
  });

  const availableCuisines = [
    'Pakistani', 'Chinese', 'Italian', 'Mexican', 'Indian', 'Thai', 
    'Fast Food', 'BBQ', 'Japanese', 'Mediterranean', 'Desserts', 'Vegetarian'
  ];

  const dietaryOptions = [
    'Vegetarian', 'Vegan', 'Halal', 'Gluten-Free', 'Dairy-Free', 
    'Nut-Free', 'Low-Sodium', 'Keto', 'Diabetic-Friendly'
  ];

  const spiceOptions = [
    { value: 'mild', label: 'Mild 🌶️', color: 'text-green-500' },
    { value: 'medium', label: 'Medium 🌶️🌶️', color: 'text-yellow-500' },
    { value: 'hot', label: 'Hot 🌶️🌶️🌶️', color: 'text-orange-500' },
    { value: 'very_hot', label: 'Very Hot 🌶️🌶️🌶️🌶️', color: 'text-red-500' }
  ];

  const handleCuisineToggle = (cuisine) => {
    const newCuisines = preferences.favorite_cuisines.includes(cuisine)
      ? preferences.favorite_cuisines.filter(c => c !== cuisine)
      : [...preferences.favorite_cuisines, cuisine];
    
    setPreferences({ ...preferences, favorite_cuisines: newCuisines });
  };

  const handleDietaryToggle = (restriction) => {
    const newRestrictions = preferences.dietary_restrictions.includes(restriction)
      ? preferences.dietary_restrictions.filter(r => r !== restriction)
      : [...preferences.dietary_restrictions, restriction];
    
    setPreferences({ ...preferences, dietary_restrictions: newRestrictions });
  };

  const handleSpiceChange = (spiceLevel) => {
    setPreferences({ ...preferences, spice_preference: spiceLevel });
  };

  const handleSavePreferences = async () => {
    setLoading(true);
    try {
      await axios.put('/api/user/preferences', preferences);
      
      // Update the user object with new preferences
      const updatedUser = { 
        ...user, 
        ...preferences 
      };
      onUserUpdate(updatedUser);
      
      toast.success('Preferences saved successfully!');
    } catch (error) {
      console.error('Error saving preferences:', error);
      toast.error('Failed to save preferences');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen py-8 px-4" data-testid="profile-page">
      <div className="max-w-4xl mx-auto space-y-8">
        {/* Header */}
        <div className="text-center">
          <div className="w-20 h-20 bg-gradient-to-br from-orange-500 to-rose-500 rounded-full flex items-center justify-center text-white text-2xl font-bold mx-auto mb-4">
            {user.username.charAt(0).toUpperCase()}
          </div>
          <h1 className="font-display text-4xl font-bold text-gray-900 mb-2">{user.username}</h1>
          <p className="text-xl text-gray-600">{user.email}</p>
        </div>

        {/* Profile Information */}
        <div className="glass rounded-2xl p-8">
          <div className="flex items-center space-x-3 mb-6">
            <User className="w-6 h-6 text-orange-500" />
            <h2 className="text-2xl font-bold text-gray-900">Profile Information</h2>
          </div>
          
          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Username</label>
              <div className="input-field bg-gray-50 cursor-not-allowed">
                {user.username}
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Email</label>
              <div className="input-field bg-gray-50 cursor-not-allowed">
                {user.email}
              </div>
            </div>
          </div>
        </div>

        {/* Food Preferences */}
        <div className="glass rounded-2xl p-8">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-3">
              <Settings className="w-6 h-6 text-orange-500" />
              <h2 className="text-2xl font-bold text-gray-900">Food Preferences</h2>
            </div>
            <button
              onClick={handleSavePreferences}
              disabled={loading}
              className="btn-primary px-6 py-3 flex items-center space-x-2"
              data-testid="save-preferences-btn"
            >
              {loading ? (
                <LoadingSpinner size="small" color="white" />
              ) : (
                <>
                  <Save className="w-4 h-4" />
                  <span>Save Changes</span>
                </>
              )}
            </button>
          </div>

          <div className="space-y-8">
            {/* Favorite Cuisines */}
            <div>
              <div className="flex items-center space-x-2 mb-4">
                <Heart className="w-5 h-5 text-rose-500" />
                <h3 className="text-lg font-semibold text-gray-900">Favorite Cuisines</h3>
              </div>
              <p className="text-gray-600 mb-4">Select cuisines you enjoy to get better recommendations</p>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                {availableCuisines.map((cuisine) => (
                  <button
                    key={cuisine}
                    onClick={() => handleCuisineToggle(cuisine)}
                    className={`p-3 rounded-xl text-sm font-medium transition-all ${
                      preferences.favorite_cuisines.includes(cuisine)
                        ? 'bg-orange-500 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                    data-testid={`cuisine-${cuisine.toLowerCase().replace(' ', '-')}`}
                  >
                    {cuisine}
                  </button>
                ))}
              </div>
            </div>

            {/* Dietary Restrictions */}
            <div>
              <div className="flex items-center space-x-2 mb-4">
                <Shield className="w-5 h-5 text-emerald-500" />
                <h3 className="text-lg font-semibold text-gray-900">Dietary Restrictions</h3>
              </div>
              <p className="text-gray-600 mb-4">Help us filter options that match your dietary needs</p>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                {dietaryOptions.map((restriction) => (
                  <button
                    key={restriction}
                    onClick={() => handleDietaryToggle(restriction)}
                    className={`p-3 rounded-xl text-sm font-medium transition-all ${
                      preferences.dietary_restrictions.includes(restriction)
                        ? 'bg-emerald-500 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                    data-testid={`dietary-${restriction.toLowerCase().replace(/[^a-z0-9]/g, '-')}`}
                  >
                    {restriction}
                  </button>
                ))}
              </div>
            </div>

            {/* Spice Preference */}
            <div>
              <div className="flex items-center space-x-2 mb-4">
                <Utensils className="w-5 h-5 text-red-500" />
                <h3 className="text-lg font-semibold text-gray-900">Spice Preference</h3>
              </div>
              <p className="text-gray-600 mb-4">How spicy do you like your food?</p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {spiceOptions.map((option) => (
                  <button
                    key={option.value}
                    onClick={() => handleSpiceChange(option.value)}
                    className={`p-4 rounded-xl text-sm font-medium transition-all border-2 ${
                      preferences.spice_preference === option.value
                        ? 'border-orange-500 bg-orange-50 text-orange-700'
                        : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'
                    }`}
                    data-testid={`spice-${option.value}`}
                  >
                    <div className={`text-lg mb-1 ${option.color}`}>
                      {option.label.split(' ')[1]}
                    </div>
                    <div>{option.label.split(' ')[0]}</div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Order Statistics */}
        <div className="glass rounded-2xl p-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">Order Statistics</h2>
          <div className="grid md:grid-cols-3 gap-6">
            <div className="text-center p-6 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl">
              <div className="text-3xl font-bold text-blue-600 mb-2">24</div>
              <div className="text-gray-600">Total Orders</div>
            </div>
            <div className="text-center p-6 bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl">
              <div className="text-3xl font-bold text-green-600 mb-2">PKR 4,850</div>
              <div className="text-gray-600">Total Spent</div>
            </div>
            <div className="text-center p-6 bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl">
              <div className="text-3xl font-bold text-purple-600 mb-2">4.8</div>
              <div className="text-gray-600">Avg Rating Given</div>
            </div>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="glass rounded-2xl p-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">Recent Activity</h2>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl">
              <div>
                <p className="font-medium text-gray-900">Chicken Biryani from Student Biryani</p>
                <p className="text-sm text-gray-600">Delivered • 2 days ago</p>
              </div>
              <div className="text-right">
                <p className="font-semibold text-gray-900">PKR 350</p>
                <div className="flex items-center space-x-1">
                  {[...Array(5)].map((_, i) => (
                    <div key={i} className={`w-3 h-3 rounded-full ${i < 4 ? 'bg-yellow-400' : 'bg-gray-300'}`}></div>
                  ))}
                </div>
              </div>
            </div>
            <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl">
              <div>
                <p className="font-medium text-gray-900">Zinger Burger from KFC</p>
                <p className="text-sm text-gray-600">Delivered • 5 days ago</p>
              </div>
              <div className="text-right">
                <p className="font-semibold text-gray-900">PKR 320</p>
                <div className="flex items-center space-x-1">
                  {[...Array(5)].map((_, i) => (
                    <div key={i} className={`w-3 h-3 rounded-full ${i < 5 ? 'bg-yellow-400' : 'bg-gray-300'}`}></div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProfilePage;