import React, { useState, useEffect } from 'react';
import { X, MapPin, Search } from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';
import LoadingSpinner from './ui/LoadingSpinner';

const AddAddressModal = ({ onClose, onAddressAdded }) => {
  const [formData, setFormData] = useState({
    label: '',
    district: '',
    area: '',
    street_address: '',
    landmark: '',
    phone: '',
    is_default: false
  });
  const [areas, setAreas] = useState({});
  const [filteredAreas, setFilteredAreas] = useState([]);
  const [areaSearch, setAreaSearch] = useState('');
  const [showAreaDropdown, setShowAreaDropdown] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchAreas();
  }, []);

  useEffect(() => {
    if (areaSearch && formData.district) {
      const districtAreas = areas[formData.district] || [];
      const filtered = districtAreas.filter(area =>
        area.toLowerCase().includes(areaSearch.toLowerCase())
      );
      setFilteredAreas(filtered);
      setShowAreaDropdown(true);
    } else {
      setShowAreaDropdown(false);
    }
  }, [areaSearch, formData.district, areas]);

  const fetchAreas = async () => {
    try {
      const response = await axios.get('/api/areas');
      setAreas(response.data.areas);
    } catch (error) {
      console.error('Error fetching areas:', error);
      toast.error('Failed to load areas');
    }
  };

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleDistrictChange = (district) => {
    setFormData(prev => ({
      ...prev,
      district,
      area: ''
    }));
    setAreaSearch('');
  };

  const handleAreaSelect = (area) => {
    setFormData(prev => ({
      ...prev,
      area
    }));
    setAreaSearch(area);
    setShowAreaDropdown(false);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.district || !formData.area || !formData.street_address || !formData.phone) {
      toast.error('Please fill all required fields');
      return;
    }

    setLoading(true);
    try {
      const addressData = {
        ...formData,
        id: Date.now().toString(), // Generate temporary ID
        area: formData.area || areaSearch
      };

      const response = await axios.post('/api/user/addresses', addressData);
      toast.success('Address added successfully!');
      onAddressAdded(addressData);
    } catch (error) {
      const message = error.response?.data?.detail || 'Failed to add address';
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center space-x-3">
            <MapPin className="w-6 h-6 text-orange-500" />
            <h2 className="text-xl font-semibold text-gray-900">Add New Address</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            data-testid="close-address-modal"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Address Label */}
          <div>
            <label htmlFor="label" className="block text-sm font-medium text-gray-700 mb-2">
              Address Label <span className="text-red-500">*</span>
            </label>
            <select
              id="label"
              name="label"
              value={formData.label}
              onChange={handleInputChange}
              className="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
              required
              data-testid="address-label"
            >
              <option value="">Select label</option>
              <option value="Home">Home</option>
              <option value="Office">Office</option>
              <option value="Other">Other</option>
            </select>
          </div>

          {/* District */}
          <div>
            <label htmlFor="district" className="block text-sm font-medium text-gray-700 mb-2">
              District <span className="text-red-500">*</span>
            </label>
            <select
              id="district"
              name="district"
              value={formData.district}
              onChange={(e) => handleDistrictChange(e.target.value)}
              className="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
              required
              data-testid="district-select"
            >
              <option value="">Select district</option>
              {Object.keys(areas).map(district => (
                <option key={district} value={district}>{district}</option>
              ))}
            </select>
          </div>

          {/* Area with Search */}
          <div className="relative">
            <label htmlFor="area" className="block text-sm font-medium text-gray-700 mb-2">
              Area <span className="text-red-500">*</span>
            </label>
            <div className="relative">
              <input
                type="text"
                id="area"
                value={areaSearch}
                onChange={(e) => setAreaSearch(e.target.value)}
                onFocus={() => formData.district && setShowAreaDropdown(true)}
                placeholder={formData.district ? "Search area..." : "Select district first"}
                className="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-orange-500 pr-10"
                disabled={!formData.district}
                required
                data-testid="area-search"
              />
              <Search className="absolute right-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            </div>
            
            {showAreaDropdown && filteredAreas.length > 0 && (
              <div className="absolute top-full left-0 right-0 bg-white border border-gray-300 rounded-xl mt-1 max-h-48 overflow-y-auto z-10 shadow-lg">
                {filteredAreas.map((area) => (
                  <button
                    key={area}
                    type="button"
                    onClick={() => handleAreaSelect(area)}
                    className="w-full text-left p-3 hover:bg-orange-50 transition-colors"
                    data-testid={`area-option-${area.toLowerCase().replace(/\s+/g, '-')}`}
                  >
                    {area}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Street Address */}
          <div>
            <label htmlFor="street_address" className="block text-sm font-medium text-gray-700 mb-2">
              Street Address <span className="text-red-500">*</span>
            </label>
            <textarea
              id="street_address"
              name="street_address"
              value={formData.street_address}
              onChange={handleInputChange}
              placeholder="House/flat number, street name..."
              className="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-orange-500 resize-none h-20"
              required
              data-testid="street-address"
            />
          </div>

          {/* Landmark */}
          <div>
            <label htmlFor="landmark" className="block text-sm font-medium text-gray-700 mb-2">
              Landmark (Optional)
            </label>
            <input
              type="text"
              id="landmark"
              name="landmark"
              value={formData.landmark}
              onChange={handleInputChange}
              placeholder="Near shopping mall, hospital, etc."
              className="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
              data-testid="landmark"
            />
          </div>

          {/* Phone */}
          <div>
            <label htmlFor="phone" className="block text-sm font-medium text-gray-700 mb-2">
              Phone Number <span className="text-red-500">*</span>
            </label>
            <input
              type="tel"
              id="phone"
              name="phone"
              value={formData.phone}
              onChange={handleInputChange}
              placeholder="03XXXXXXXXX"
              className="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
              required
              data-testid="phone"
            />
          </div>

          {/* Default Address */}
          <div className="flex items-center space-x-3">
            <input
              type="checkbox"
              id="is_default"
              name="is_default"
              checked={formData.is_default}
              onChange={handleInputChange}
              className="w-4 h-4 text-orange-500 border-gray-300 rounded focus:ring-orange-500"
              data-testid="is-default"
            />
            <label htmlFor="is_default" className="text-sm font-medium text-gray-700">
              Set as default address
            </label>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={loading}
            className="w-full btn-primary py-4 font-semibold disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
            data-testid="save-address-btn"
          >
            {loading ? (
              <LoadingSpinner size="small" color="white" />
            ) : (
              'Save Address'
            )}
          </button>
        </form>
      </div>
    </div>
  );
};

export default AddAddressModal;