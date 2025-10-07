import React from 'react';

const LoadingSpinner = ({ size = 'medium', color = 'orange' }) => {
  const sizeClasses = {
    small: 'w-4 h-4',
    medium: 'w-8 h-8', 
    large: 'w-12 h-12'
  };

  const colorClasses = {
    orange: 'border-orange-500',
    white: 'border-white',
    gray: 'border-gray-500'
  };

  return (
    <div className={`loading-spinner ${sizeClasses[size]} border-4 border-gray-200 ${colorClasses[color]} border-t-4 rounded-full`}></div>
  );
};

export default LoadingSpinner;