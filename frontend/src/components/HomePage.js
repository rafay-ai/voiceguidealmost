import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Mic, Star, Clock, Users, Shield, Zap } from 'lucide-react';

const HomePage = () => {
  const [isListening, setIsListening] = useState(false);

  const handleVoiceDemo = () => {
    setIsListening(true);
    // Simulate voice recognition
    setTimeout(() => {
      setIsListening(false);
    }, 3000);
  };

  const features = [
    {
      icon: <Mic className="w-8 h-8" />,
      title: "Voice Ordering",
      description: "Order your favorite food using natural speech with our AI-powered voice assistant"
    },
    {
      icon: <Star className="w-8 h-8" />,
      title: "Smart Recommendations",
      description: "Personalized food suggestions based on your preferences and order history"
    },
    {
      icon: <Clock className="w-8 h-8" />,
      title: "Quick Delivery",
      description: "Fast and reliable delivery from your favorite local restaurants"
    },
    {
      icon: <Shield className="w-8 h-8" />,
      title: "Secure & Private",
      description: "Your preferences and data are protected with advanced security measures"
    }
  ];

  const cuisines = [
    { name: "Pakistani", image: "🍛", color: "from-emerald-500 to-teal-600" },
    { name: "Chinese", image: "🥢", color: "from-red-500 to-pink-600" },
    { name: "Fast Food", image: "🍔", color: "from-yellow-500 to-orange-600" },
    { name: "Italian", image: "🍝", color: "from-green-500 to-emerald-600" },
    { name: "Desserts", image: "🍰", color: "from-purple-500 to-pink-600" },
    { name: "BBQ", image: "🥩", color: "from-orange-500 to-red-600" }
  ];

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="relative overflow-hidden py-20 px-4">
        <div className="absolute inset-0 bg-gradient-to-br from-orange-100 via-rose-50 to-pink-100"></div>
        <div className="relative max-w-7xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            {/* Left Content */}
            <div className="text-center lg:text-left">
              <h1 className="font-display text-5xl lg:text-7xl font-bold text-gray-900 mb-6 leading-tight">
                Voice Guide
                <span className="block text-transparent bg-clip-text bg-gradient-to-r from-orange-500 to-rose-500">
                  Food Delivery
                </span>
              </h1>
              <p className="text-xl text-gray-600 mb-8 leading-relaxed max-w-2xl">
                Experience the future of food ordering with our AI-powered voice assistant. 
                Simply speak your cravings and let us handle the rest with personalized recommendations.
              </p>
              
              {/* Voice Demo Button */}
              <div className="flex flex-col sm:flex-row gap-4 justify-center lg:justify-start mb-12">
                <button
                  onClick={handleVoiceDemo}
                  className={`voice-button ${isListening ? 'recording' : ''} mx-auto sm:mx-0`}
                  data-testid="voice-demo-button"
                >
                  <Mic className="w-6 h-6" />
                </button>
                <div className="flex flex-col justify-center">
                  <p className="text-sm text-gray-500 mb-1">Try saying:</p>
                  <p className="text-gray-700 font-medium">"I want spicy Pakistani food"</p>
                </div>
              </div>

              {/* CTA Buttons */}
              <div className="flex flex-col sm:flex-row gap-4 justify-center lg:justify-start">
                <Link 
                  to="/register" 
                  className="btn-primary text-center px-8 py-4 text-lg"
                  data-testid="get-started-btn"
                >
                  Get Started
                </Link>
                <Link 
                  to="/login" 
                  className="btn-secondary text-center px-8 py-4 text-lg"
                  data-testid="login-btn"
                >
                  Sign In
                </Link>
              </div>
            </div>

            {/* Right Content - Hero Image */}
            <div className="relative">
              <div className="relative z-10">
                <img
                  src="https://images.unsplash.com/photo-1609405978461-63be963705b5?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1200&q=80"
                  alt="Voice Guide Food Delivery App"
                  className="rounded-2xl shadow-2xl w-full max-w-lg mx-auto float"
                />
              </div>
              <div className="absolute -top-4 -right-4 w-24 h-24 bg-gradient-to-br from-orange-400 to-rose-500 rounded-full opacity-20 blur-2xl"></div>
              <div className="absolute -bottom-4 -left-4 w-32 h-32 bg-gradient-to-br from-pink-400 to-purple-500 rounded-full opacity-20 blur-2xl"></div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 px-4 bg-white" data-testid="features-section">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="font-display text-4xl lg:text-5xl font-bold text-gray-900 mb-6">
              Why Choose Voice Guide?
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Revolutionary AI-powered features that make food ordering effortless and personalized
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature, index) => (
              <div key={index} className="text-center card-hover p-8 rounded-2xl bg-gradient-to-br from-white to-gray-50 border border-gray-100">
                <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-orange-500 to-rose-500 text-white rounded-2xl mb-6">
                  {feature.icon}
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-4">{feature.title}</h3>
                <p className="text-gray-600 leading-relaxed">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Cuisines Preview */}
      <section className="py-20 px-4 bg-gradient-to-br from-gray-50 to-white">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="font-display text-4xl lg:text-5xl font-bold text-gray-900 mb-6">
              Explore Diverse Cuisines
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              From traditional Pakistani dishes to international favorites, discover flavors from around the world
            </p>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6">
            {cuisines.map((cuisine, index) => (
              <div key={index} className="card-hover">
                <div className={`bg-gradient-to-br ${cuisine.color} p-8 rounded-2xl text-center text-white`}>
                  <div className="text-4xl mb-4">{cuisine.image}</div>
                  <h3 className="font-semibold text-lg">{cuisine.name}</h3>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-20 px-4 bg-gradient-to-r from-orange-500 to-rose-500 text-white">
        <div className="max-w-7xl mx-auto">
          <div className="grid md:grid-cols-3 gap-8 text-center">
            <div className="card-hover p-8">
              <div className="flex items-center justify-center mb-4">
                <Users className="w-8 h-8" />
              </div>
              <h3 className="text-4xl font-bold mb-2">10,000+</h3>
              <p className="text-orange-100">Happy Customers</p>
            </div>
            <div className="card-hover p-8">
              <div className="flex items-center justify-center mb-4">
                <Star className="w-8 h-8" />
              </div>
              <h3 className="text-4xl font-bold mb-2">4.8</h3>
              <p className="text-orange-100">Average Rating</p>
            </div>
            <div className="card-hover p-8">
              <div className="flex items-center justify-center mb-4">
                <Zap className="w-8 h-8" />
              </div>
              <h3 className="text-4xl font-bold mb-2">25 min</h3>
              <p className="text-orange-100">Avg. Delivery Time</p>
            </div>
          </div>
        </div>
      </section>

      {/* Call to Action */}
      <section className="py-20 px-4 bg-gradient-to-br from-gray-900 to-gray-800 text-white">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="font-display text-4xl lg:text-5xl font-bold mb-6">
            Ready to Experience Voice Ordering?
          </h2>
          <p className="text-xl text-gray-300 mb-8 leading-relaxed">
            Join thousands of users who have revolutionized their food ordering experience with Voice Guide
          </p>
          <Link 
            to="/register" 
            className="btn-primary text-lg px-10 py-4 inline-block"
            data-testid="cta-register-btn"
          >
            Start Ordering Now
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-white py-12 px-4 border-t border-gray-200">
        <div className="max-w-7xl mx-auto text-center">
          <div className="mb-8">
            <h3 className="font-display text-2xl font-bold text-gray-900 mb-2">Voice Guide</h3>
            <p className="text-gray-600">The future of food delivery is here</p>
          </div>
          <div className="text-sm text-gray-500">
            © 2024 Voice Guide. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  );
};

export default HomePage;