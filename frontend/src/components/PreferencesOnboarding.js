import React, { useState } from 'react';
import axios from 'axios';
import { Heart, Shield, Utensils, CheckCircle } from 'lucide-react';
import { toast } from 'sonner';
import LoadingSpinner from './ui/LoadingSpinner';

const PreferencesOnboarding = ({ onComplete }) => {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [preferences, setPreferences] = useState({
    favorite_cuisines: [],
    dietary_restrictions: [],
    spice_preference: 'medium'
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
    { value: 'mild', label: 'Mild 🌶️', color: 'text-green-500', desc: 'Light and gentle flavors' },
    { value: 'medium', label: 'Medium 🌶️🌶️', color: 'text-yellow-500', desc: 'Perfect balance of heat' },
    { value: 'hot', label: 'Hot 🌶️🌶️🌶️', color: 'text-orange-500', desc: 'Spicy and flavorful' },
    { value: 'very_hot', label: 'Very Hot 🌶️🌶️🌶️🌶️', color: 'text-red-500', desc: 'Extra hot and fiery' }
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

  const canProceed = () => {
    if (step === 1) return preferences.favorite_cuisines.length > 0;
    if (step === 2) return true; // Dietary restrictions are optional
    if (step === 3) return preferences.spice_preference;
    return false;
  };

  const handleNext = () => {
    if (step < 3) {
      setStep(step + 1);
    } else {
      handleSubmit();
    }
  };

  const handleSubmit = async () => {
    setLoading(true);
    try {
      await axios.post('/api/user/setup-preferences', preferences);
      toast.success('Preferences saved! Welcome to Voice Guide!');
      onComplete();
    } catch (error) {
      console.error('Error saving preferences:', error);
      toast.error('Failed to save preferences. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-3xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="bg-gradient-to-r from-orange-500 to-rose-500 p-8 text-white text-center rounded-t-3xl">
          <h1 className="font-display text-3xl font-bold mb-2">Welcome to Voice Guide!</h1>
          <p className="text-orange-100">Let's personalize your food experience</p>
          <div className="flex justify-center mt-6 space-x-2">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className={`w-3 h-3 rounded-full transition-all ${
                  i <= step ? 'bg-white' : 'bg-orange-300'
                }`}
              />
            ))}
          </div>
        </div>

        <div className="p-8">
          {/* Step 1: Favorite Cuisines */}
          {step === 1 && (
            <div data-testid="cuisines-step">
              <div className="text-center mb-8">
                <Heart className="w-16 h-16 text-rose-500 mx-auto mb-4" />
                <h2 className="text-2xl font-bold text-gray-900 mb-2">What cuisines do you love?</h2>
                <p className="text-gray-600">Select at least one to get better recommendations</p>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8">
                {availableCuisines.map((cuisine) => (
                  <button
                    key={cuisine}
                    onClick={() => handleCuisineToggle(cuisine)}
                    className={`p-4 rounded-xl text-sm font-medium transition-all ${
                      preferences.favorite_cuisines.includes(cuisine)
                        ? 'bg-orange-500 text-white transform scale-105'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                    data-testid={`cuisine-${cuisine.toLowerCase().replace(' ', '-')}`}
                  >
                    {cuisine}
                  </button>
                ))}
              </div>

              <p className="text-sm text-gray-500 text-center mb-6">
                Selected: {preferences.favorite_cuisines.length} cuisine{preferences.favorite_cuisines.length !== 1 ? 's' : ''}
              </p>
            </div>
          )}

          {/* Step 2: Dietary Restrictions */}
          {step === 2 && (
            <div data-testid="dietary-step">
              <div className="text-center mb-8">
                <Shield className="w-16 h-16 text-emerald-500 mx-auto mb-4" />
                <h2 className="text-2xl font-bold text-gray-900 mb-2">Any dietary restrictions?</h2>
                <p className="text-gray-600">Help us filter options that match your needs (optional)</p>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8">
                {dietaryOptions.map((restriction) => (
                  <button
                    key={restriction}
                    onClick={() => handleDietaryToggle(restriction)}
                    className={`p-4 rounded-xl text-sm font-medium transition-all ${
                      preferences.dietary_restrictions.includes(restriction)
                        ? 'bg-emerald-500 text-white transform scale-105'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                    data-testid={`dietary-${restriction.toLowerCase().replace(/[^a-z0-9]/g, '-')}`}
                  >
                    {restriction}
                  </button>
                ))}
              </div>

              <p className="text-sm text-gray-500 text-center mb-6">
                Selected: {preferences.dietary_restrictions.length} restriction{preferences.dietary_restrictions.length !== 1 ? 's' : ''}
              </p>
            </div>
          )}

          {/* Step 3: Spice Preference */}
          {step === 3 && (
            <div data-testid="spice-step">
              <div className="text-center mb-8">
                <Utensils className="w-16 h-16 text-red-500 mx-auto mb-4" />
                <h2 className="text-2xl font-bold text-gray-900 mb-2">How spicy do you like it?</h2>
                <p className="text-gray-600">This helps us recommend the right spice level for you</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
                {spiceOptions.map((option) => (
                  <button
                    key={option.value}
                    onClick={() => handleSpiceChange(option.value)}
                    className={`p-6 rounded-xl transition-all border-2 ${
                      preferences.spice_preference === option.value
                        ? 'border-orange-500 bg-orange-50 transform scale-105'
                        : 'border-gray-200 bg-white hover:border-gray-300'
                    }`}
                    data-testid={`spice-${option.value}`}
                  >
                    <div className={`text-2xl mb-2 ${option.color}`}>
                      {option.label.split(' ').slice(1).join(' ')}
                    </div>
                    <div className="font-semibold text-lg text-gray-900 mb-1">
                      {option.label.split(' ')[0]}
                    </div>
                    <div className="text-sm text-gray-600">
                      {option.desc}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Navigation Buttons */}
          <div className="flex justify-between items-center pt-6 border-t border-gray-200">
            <button
              onClick={() => setStep(Math.max(1, step - 1))}
              disabled={step === 1}
              className={`px-6 py-3 rounded-xl font-medium transition-all ${
                step === 1
                  ? 'text-gray-400 cursor-not-allowed'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              Previous
            </button>

            <div className="flex items-center space-x-2 text-sm text-gray-500">
              <span>Step {step} of 3</span>
            </div>

            <button
              onClick={handleNext}
              disabled={!canProceed() || loading}
              className={`px-8 py-3 rounded-xl font-semibold transition-all flex items-center space-x-2 ${
                canProceed() && !loading
                  ? 'bg-orange-500 text-white hover:bg-orange-600 transform hover:scale-105'
                  : 'bg-gray-300 text-gray-500 cursor-not-allowed'
              }`}
              data-testid="next-button"
            >
              {loading ? (
                <LoadingSpinner size="small" color="white" />
              ) : (
                <>
                  {step === 3 ? (
                    <>
                      <CheckCircle className="w-4 h-4" />
                      <span>Complete Setup</span>
                    </>
                  ) : (
                    <span>Next</span>
                  )}
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PreferencesOnboarding;