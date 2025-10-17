import React, { useState, useRef, useEffect } from 'react';
import { Mic, MicOff, Send, MessageCircle, Sparkles, Clock, ShoppingBag } from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';
import LoadingSpinner from './ui/LoadingSpinner';
import RestaurantCard from './RestaurantCard';
import ChatOrderCard from './ChatOrderCard';

const ChatPage = ({ user }) => {
  const [messages, setMessages] = useState([
    {
      id: '1',
      type: 'assistant',
      content: `Hi ${user.username}! 👋 Try: "I'm hungry" or "Order biryani"`,
      timestamp: new Date()
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId] = useState(() => Date.now().toString());
  
  const messagesEndRef = useRef(null);
  const recognitionRef = useRef(null);
  const mediaRecorderRef = useRef(null);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Initialize Speech Recognition
  useEffect(() => {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      
      recognitionRef.current.continuous = true;
      recognitionRef.current.interimResults = true;
      recognitionRef.current.lang = 'en-US';

      recognitionRef.current.onresult = (event) => {
        const transcript = Array.from(event.results)
          .map(result => result[0])
          .map(result => result.transcript)
          .join('');

        if (event.results[event.results.length - 1].isFinal) {
          setInputMessage(transcript);
          setIsRecording(false);
          // Auto-send the message after recording
          setTimeout(() => sendMessage(transcript), 500);
        }
      };

      recognitionRef.current.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        setIsRecording(false);
        toast.error('Voice recognition failed. Please try again.');
      };

      recognitionRef.current.onend = () => {
        setIsRecording(false);
      };
    }
  }, []);

  const startRecording = () => {
    if (!recognitionRef.current) {
      toast.error('Voice recognition is not supported in this browser');
      return;
    }

    try {
      setIsRecording(true);
      setInputMessage('');
      recognitionRef.current.start();
      toast.info('Listening... Speak now!');
    } catch (error) {
      console.error('Error starting recording:', error);
      setIsRecording(false);
      toast.error('Failed to start voice recognition');
    }
  };

  const stopRecording = () => {
    if (recognitionRef.current && isRecording) {
      recognitionRef.current.stop();
      setIsRecording(false);
    }
  };

  const sendMessage = async (messageText = inputMessage) => {
    if (!messageText.trim() || isLoading) return;

    const userMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: messageText,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      const response = await axios.post('/api/chat', {
        message: messageText,
        user_id: user.id,
        session_id: sessionId
      });

      const assistantMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: response.data.response,
        restaurants: response.data.restaurants || [],
        recommendedItems: response.data.recommended_items || [],
        showOrderCard: response.data.show_order_card || false,
        hasDefaultAddress: response.data.has_default_address || false,
        defaultAddress: response.data.default_address || null,
        orderReady: response.data.order_ready || false,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: "Something went wrong! Try asking me about food recommendations 🍽️",
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
      toast.error('Failed to send message');
    } finally {
      setIsLoading(false);
    }
  };

  const handleOrderFromChat = async (menuItemIds, restaurant) => {
    try {
      setIsLoading(true);
      
      const response = await axios.post('/api/chat/order', {
        menu_item_ids: menuItemIds,
        quantities: menuItemIds.map(() => 1), // Default quantity 1
        use_default_address: true,
        payment_method: 'cod'
      });

      if (response.data.success) {
        toast.success(`${response.data.message} 🎉`);
        
        // Add success message to chat
        const successMessage = {
          id: Date.now().toString(),
          type: 'assistant', 
          content: `Perfect! ${response.data.message} Total: PKR ${response.data.total}. Check your email for confirmation! 📧`,
          timestamp: new Date()
        };
        setMessages(prev => [...prev, successMessage]);
      } else {
        toast.error(response.data.message);
        
        const errorMessage = {
          id: Date.now().toString(),
          type: 'assistant',
          content: response.data.message.includes('address') 
            ? 'Please add a delivery address first in your profile! 📍'
            : 'Something went wrong. Try again or add items to cart manually.',
          timestamp: new Date()
        };
        setMessages(prev => [...prev, errorMessage]);
      }
    } catch (error) {
      console.error('Error placing order from chat:', error);
      toast.error('Failed to place order');
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const quickActions = [
    "I'm hungry 🍽️",
    "Order biryani 🍛", 
    "Chinese food 🥢",
    "Fast food 🍔",
    "Desserts 🍰",
    "Budget meal 💰"
  ];

  return (
    <div className="min-h-screen py-8 px-4" data-testid="chat-page">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center space-x-3 mb-4">
            <div className="w-12 h-12 bg-gradient-to-br from-orange-500 to-rose-500 rounded-full flex items-center justify-center">
              <MessageCircle className="w-6 h-6 text-white" />
            </div>
            <h1 className="font-display text-4xl font-bold text-gray-900">Voice Assistant</h1>
          </div>
          <p className="text-xl text-gray-600">Speak or type to order food, get recommendations, and more!</p>
        </div>

        {/* Quick Actions */}
        <div className="mb-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <Sparkles className="w-5 h-5 text-orange-500 mr-2" />
            Quick Actions
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {quickActions.map((action, index) => (
              <button
                key={index}
                onClick={() => sendMessage(action)}
                className="text-left p-3 bg-white rounded-xl border border-gray-200 hover:border-orange-300 hover:bg-orange-50 transition-all text-sm"
                data-testid={`quick-action-${index}`}
              >
                "{action}"
              </button>
            ))}
          </div>
        </div>

        {/* Chat Container */}
        <div className="bg-white rounded-2xl shadow-xl overflow-hidden">
          {/* Messages Area */}
          <div className="h-96 overflow-y-auto p-6 space-y-4" data-testid="chat-messages">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div className={`${message.type === 'user' ? 'ml-auto' : 'mr-auto'} max-w-xs lg:max-w-md xl:max-w-lg`}>
                  <div
                    className={`${
                      message.type === 'user' 
                        ? 'chat-bubble-user' 
                        : 'chat-bubble-assistant'
                    }`}
                  >
                    <p className="text-sm">{message.content}</p>
                    <div className="flex items-center mt-2 space-x-1 text-xs opacity-70">
                      <Clock className="w-3 h-3" />
                      <span>{message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    </div>
                  </div>
                  
                  {/* Direct Order Card */}
                  {message.showOrderCard && message.recommendedItems && message.recommendedItems.length > 0 && (
                    <div className="mt-3">
                      <ChatOrderCard
                        items={message.recommendedItems}
                        address={message.defaultAddress}
                        onOrderSuccess={(orderData) => {
                          const successMessage = {
                            id: Date.now().toString(),
                            type: 'assistant',
                            content: `🎉 Order placed! #${orderData.order_number} - PKR ${orderData.total}`,
                            timestamp: new Date()
                          };
                          setMessages(prev => [...prev, successMessage]);
                        }}
                        onClose={() => {}}
                      />
                    </div>
                  )}
                  
                  {/* Restaurant Cards */}
                  {message.restaurants && message.restaurants.length > 0 && !message.showOrderCard && (
                    <div className="mt-3 space-y-2">
                      <p className="text-xs text-gray-600 mb-2">Great options:</p>
                      {message.restaurants.slice(0, 2).map((restaurant) => (
                        <RestaurantCard
                          key={restaurant.id}
                          restaurant={restaurant}
                          onOrderFromChat={handleOrderFromChat}
                          compact={true}
                        />
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
            
            {isLoading && (
              <div className="flex justify-start">
                <div className="chat-bubble-assistant">
                  <div className="flex items-center space-x-2">
                    <LoadingSpinner size="small" />
                    <span className="text-sm">Thinking...</span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="border-t border-gray-200 p-6">
            <div className="flex space-x-4">
              {/* Voice Button */}
              <button
                onClick={isRecording ? stopRecording : startRecording}
                className={`voice-button ${isRecording ? 'recording' : ''}`}
                disabled={isLoading}
                data-testid="voice-button"
              >
                {isRecording ? <MicOff className="w-6 h-6" /> : <Mic className="w-6 h-6" />}
              </button>

              {/* Text Input */}
              <div className="flex-1 flex space-x-3">
                <textarea
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder={isRecording ? "Listening..." : "Type your message or use voice..."}
                  className="flex-1 input-field resize-none py-4"
                  rows="1"
                  disabled={isRecording || isLoading}
                  data-testid="chat-input"
                />
                <button
                  onClick={() => sendMessage()}
                  disabled={!inputMessage.trim() || isLoading || isRecording}
                  className="btn-primary px-6 py-4 disabled:opacity-50 disabled:cursor-not-allowed"
                  data-testid="send-button"
                >
                  <Send className="w-5 h-5" />
                </button>
              </div>
            </div>
            
            {/* Status Indicators */}
            <div className="mt-4 flex items-center justify-between text-sm text-gray-500">
              <div className="flex items-center space-x-4">
                {isRecording && (
                  <div className="flex items-center space-x-2 text-red-500">
                    <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
                    <span>Recording...</span>
                  </div>
                )}
                {!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) && (
                  <span className="text-orange-500">Voice recognition not supported in this browser</span>
                )}
              </div>
              <div>
                <span>Press Enter to send • Click mic to speak</span>
              </div>
            </div>
          </div>
        </div>

        {/* Tips */}
        <div className="mt-8 p-6 bg-gradient-to-r from-orange-50 to-rose-50 rounded-2xl">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">💡 Quick Tips:</h3>
          <ul className="space-y-2 text-gray-700 text-sm">
            <li>• Say "I'm hungry" for instant recommendations</li>
            <li>• Try "Order biryani" for direct ordering</li>
            <li>• I'll show restaurant cards you can order from!</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default ChatPage;