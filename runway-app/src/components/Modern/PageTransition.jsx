// src/components/Modern/PageTransition.jsx
import React, { useEffect, useState } from 'react';

/**
 * PageTransition - Smooth fade transitions between pages
 * Mobile-first design with performance optimizations
 */

export default function PageTransition({ children, pageKey }) {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    // Reset animation on page change
    setIsVisible(false);
    const timer = setTimeout(() => {
      setIsVisible(true);
    }, 10);

    return () => clearTimeout(timer);
  }, [pageKey]);

  return (
    <div
      className={`w-full h-full transition-all duration-300 ease-out ${
        isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
      }`}
    >
      {children}
    </div>
  );
}
