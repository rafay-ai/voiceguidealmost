import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Search, Filter, Star, Clock, MapPin, ChevronLeft, ChevronRight, Plus } from 'lucide-react';
import { toast } from 'sonner';
import LoadingSpinner from './ui/LoadingSpinner';
import RestaurantModal from './RestaurantModal';

const RestaurantsPage = ({ user }) => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const [restaurants, setRestaurants] = useState([]);
  const [cuisines, setCuisines] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCuisine, setSelectedCuisine] = useState(searchParams.get('cuisine') || '');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [selectedRestaurant, setSelectedRestaurant] = useState(null);

  const restaurantsPerPage = 6;

  useEffect(() => {
    fetchCuisines();
  }, []);

  useEffect(() => {
    fetchRestaurants();
  }, [currentPage, selectedCuisine]);

  const fetchCuisines = async () => {
    try {
      const response = await axios.get('/api/cuisines');
      setCuisines(response.data.cuisines);
    } catch (error) {
      console.error('Error fetching cuisines:', error);
      toast.error('Failed to load cuisines');
    }
  };

  const fetchRestaurants = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams({
        page: currentPage.toString(),
        limit: restaurantsPerPage.toString()
      });
      
      if (selectedCuisine) {
        params.append('cuisine', selectedCuisine);
      }

      const response = await axios.get(`/api/restaurants?${params}`);
      const data = response.data;
      
      setRestaurants(data.restaurants);
      setTotalPages(Math.ceil(data.total / restaurantsPerPage));
      setHasMore(data.has_more);
    } catch (error) {
      console.error('Error fetching restaurants:', error);
      toast.error('Failed to load restaurants');
    } finally {
      setLoading(false);
    }
  };

  const handleCuisineFilter = (cuisine) => {
    setSelectedCuisine(cuisine);
    setCurrentPage(1);
    
    // Update URL params
    if (cuisine) {
      setSearchParams({ cuisine });
    } else {
      setSearchParams({});
    }
  };

  const handlePageChange = (page) => {
    setCurrentPage(page);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const filteredRestaurants = restaurants.filter(restaurant => 
    restaurant.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    restaurant.description.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="min-h-screen py-8 px-4" data-testid="restaurants-page">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="font-display text-4xl lg:text-5xl font-bold text-gray-900 mb-4">
            Restaurants
          </h1>
          <p className="text-xl text-gray-600">Discover amazing food from local restaurants</p>
        </div>

        {/* Search and Filters */}
        <div className="mb-8 space-y-6">
          {/* Search Bar */}
          <div className="relative max-w-md mx-auto">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Search className="h-5 w-5 text-gray-400" />
            </div>
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search restaurants..."
              className="input-field pl-10 w-full"
              data-testid="restaurant-search"
            />
          </div>

          {/* Cuisine Filters */}
          <div className="flex flex-wrap justify-center gap-3">
            <button
              onClick={() => handleCuisineFilter('')}
              className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
                selectedCuisine === '' 
                  ? 'bg-orange-500 text-white' 
                  : 'bg-white text-gray-600 border border-gray-300 hover:border-orange-300'
              }`}
              data-testid="cuisine-filter-all"
            >
              All Cuisines
            </button>
            {cuisines.slice(0, 6).map((cuisine) => (
              <button
                key={cuisine}
                onClick={() => handleCuisineFilter(cuisine)}
                className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
                  selectedCuisine === cuisine
                    ? 'bg-orange-500 text-white'
                    : 'bg-white text-gray-600 border border-gray-300 hover:border-orange-300'
                }`}
                data-testid={`cuisine-filter-${cuisine.toLowerCase().replace(' ', '-')}`}
              >
                {cuisine}
              </button>
            ))}
          </div>
        </div>

        {/* Loading State */}
        {loading ? (
          <div className="flex justify-center py-12">
            <LoadingSpinner size="large" />
          </div>
        ) : (
          <>
            {/* Results Count */}
            <div className="mb-6 text-center text-gray-600">
              {filteredRestaurants.length === 0 ? (
                'No restaurants found'
              ) : (
                `Showing ${filteredRestaurants.length} restaurant${filteredRestaurants.length !== 1 ? 's' : ''}`
              )}
            </div>

            {/* Restaurants Grid */}
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12" data-testid="restaurants-grid">
              {filteredRestaurants.map((restaurant) => (
                <div key={restaurant.id} className="restaurant-card" data-testid={`restaurant-${restaurant.id}`}>
                  <div className="relative">
                    <img 
                      src={`https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&q=80`}
                      alt={restaurant.name}
                      className="w-full h-48 object-cover"
                    />
                    <div className="absolute top-3 right-3">
                      <span className={`category-badge ${
                        restaurant.price_range === 'Budget' ? 'bg-green-500' :
                        restaurant.price_range === 'Moderate' ? 'bg-yellow-500' : 'bg-purple-500'
                      }`}>
                        {restaurant.price_range}
                      </span>
                    </div>
                    {!restaurant.is_active && (
                      <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center">
                        <span className="text-white font-semibold">Currently Closed</span>
                      </div>
                    )}
                  </div>
                  
                  <div className="p-6">
                    <div className="flex items-start justify-between mb-2">
                      <h3 className="font-semibold text-xl text-gray-900">{restaurant.name}</h3>
                      <div className="flex items-center space-x-1">
                        <Star className="w-4 h-4 text-yellow-400 fill-current" />
                        <span className="text-sm font-medium">{restaurant.rating}</span>
                      </div>
                    </div>
                    
                    <p className="text-gray-600 text-sm mb-4 line-clamp-2">{restaurant.description}</p>
                    
                    <div className="space-y-2 mb-4">
                      <div className="flex items-center text-sm text-gray-600">
                        <Clock className="w-4 h-4 mr-2" />
                        <span>{restaurant.delivery_time}</span>
                      </div>
                      <div className="flex items-center text-sm text-gray-600">
                        <MapPin className="w-4 h-4 mr-2" />
                        <span>PKR {restaurant.delivery_fee} delivery • Min PKR {restaurant.minimum_order}</span>
                      </div>
                    </div>
                    
                    {/* Cuisine Tags */}
                    <div className="flex flex-wrap gap-1 mb-4">
                      {restaurant.cuisine.slice(0, 3).map((cuisine, index) => (
                        <span 
                          key={index}
                          className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded-md"
                        >
                          {cuisine}
                        </span>
                      ))}
                      {restaurant.cuisine.length > 3 && (
                        <span className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded-md">
                          +{restaurant.cuisine.length - 3}
                        </span>
                      )}
                    </div>
                    
                    <button 
                      className="w-full btn-primary py-3 font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
                      disabled={!restaurant.is_active}
                      onClick={() => setSelectedRestaurant(restaurant)}
                    >
                      {restaurant.is_active ? 'View Menu' : 'Closed'}
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {/* Empty State */}
            {filteredRestaurants.length === 0 && !loading && (
              <div className="text-center py-12">
                <div className="w-24 h-24 mx-auto mb-4 bg-gray-100 rounded-full flex items-center justify-center">
                  <Search className="w-8 h-8 text-gray-400" />
                </div>
                <h3 className="text-xl font-semibold text-gray-600 mb-2">No restaurants found</h3>
                <p className="text-gray-500 mb-4">
                  {searchTerm ? 'Try adjusting your search terms' : 'Try selecting a different cuisine'}
                </p>
                <button 
                  onClick={() => {
                    setSearchTerm('');
                    setSelectedCuisine('');
                    setSearchParams({});
                  }}
                  className="btn-secondary"
                >
                  Clear Filters
                </button>
              </div>
            )}

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex justify-center items-center space-x-4" data-testid="pagination">
                <button
                  onClick={() => handlePageChange(currentPage - 1)}
                  disabled={currentPage === 1}
                  className="flex items-center px-4 py-2 text-sm font-medium text-gray-500 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronLeft className="w-4 h-4 mr-2" />
                  Previous
                </button>
                
                <div className="flex items-center space-x-2">
                  {[...Array(totalPages)].map((_, index) => {
                    const page = index + 1;
                    return (
                      <button
                        key={page}
                        onClick={() => handlePageChange(page)}
                        className={`w-10 h-10 text-sm font-medium rounded-lg transition-all ${
                          currentPage === page
                            ? 'bg-orange-500 text-white'
                            : 'text-gray-500 hover:bg-gray-50'
                        }`}
                      >
                        {page}
                      </button>
                    );
                  })}
                </div>
                
                <button
                  onClick={() => handlePageChange(currentPage + 1)}
                  disabled={currentPage === totalPages}
                  className="flex items-center px-4 py-2 text-sm font-medium text-gray-500 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                  <ChevronRight className="w-4 h-4 ml-2" />
                </button>
              </div>
            )}
          </>
        )}
      </div>
      
      {/* Restaurant Modal */}
      {selectedRestaurant && (
        <RestaurantModal 
          restaurant={selectedRestaurant}
          onClose={() => setSelectedRestaurant(null)}
        />
      )}
    </div>
  );
};

export default RestaurantsPage;