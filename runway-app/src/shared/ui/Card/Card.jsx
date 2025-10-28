import React from 'react';

/**
 * Reusable Card Component
 */
export default function Card({ 
  children, 
  className = '', 
  padding = 'p-6',
  shadow = 'shadow-lg',
  bg = 'bg-white',
  rounded = 'rounded-xl',
  hover = false 
}) {
  const hoverClass = hover ? 'transition-all hover:shadow-2xl hover:-translate-y-1' : '';
  
  return (
    <div className={`
      ${bg}
      ${rounded}
      ${shadow}
      ${padding}
      ${hoverClass}
      ${className}
    `}>
      {children}
    </div>
  );
}
