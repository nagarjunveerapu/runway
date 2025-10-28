// src/components/Modern/ModernProfile.jsx
import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';

/**
 * ModernProfile - Simple, clean profile page
 * Inspired by Jupiter, Fi Money, CRED profiles
 */

export default function ModernProfile({ onNavigate }) {
  const { user, logout } = useAuth();
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);

  const handleLogout = () => {
    logout();
  };

  const menuItems = [
    {
      icon: '⚙️',
      label: 'App Settings',
      description: 'Preferences & configuration',
      onClick: () => onNavigate('settings'),
      color: 'from-blue-500 to-cyan-500'
    },
    {
      icon: '🔔',
      label: 'Notifications',
      description: 'Manage alerts & reminders',
      disabled: true,
      color: 'from-gray-400 to-gray-500'
    },
    {
      icon: '🔒',
      label: 'Privacy & Security',
      description: 'Protect your data',
      disabled: true,
      color: 'from-gray-400 to-gray-500'
    },
    {
      icon: '❓',
      label: 'Help & Support',
      description: 'Get assistance',
      disabled: true,
      color: 'from-gray-400 to-gray-500'
    }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 pb-24">
      {/* Header with User Info */}
      <div className="bg-gradient-to-br from-purple-600 to-indigo-700 text-white px-4 pt-8 pb-12">
        <div className="max-w-lg mx-auto">
          {/* Avatar & Name */}
          <div className="flex items-center gap-4 mb-6">
            <div className="w-20 h-20 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center text-3xl font-bold border-4 border-white/30">
              {user?.username ? user.username[0].toUpperCase() : '?'}
            </div>
            <div>
              <h1 className="text-2xl font-bold">{user?.username || 'User'}</h1>
              <p className="text-sm text-white/80 mt-1">{user?.email || 'user@runway.app'}</p>
            </div>
          </div>

        </div>
      </div>

      {/* Menu Items */}
      <div className="max-w-lg mx-auto px-4 -mt-6">
        <div className="bg-white rounded-2xl shadow-lg p-2 space-y-2">
          {menuItems.map((item, index) => (
            <button
              key={index}
              onClick={item.onClick}
              disabled={item.disabled}
              className={`w-full flex items-center gap-4 p-4 rounded-xl transition-all ${
                item.disabled
                  ? 'opacity-50 cursor-not-allowed'
                  : 'hover:bg-gray-50 active:scale-98'
              }`}
            >
              <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${item.color} flex items-center justify-center text-2xl flex-shrink-0 ${
                item.disabled ? 'opacity-60' : ''
              }`}>
                {item.icon}
              </div>
              <div className="flex-1 text-left">
                <div className="font-semibold text-gray-900">{item.label}</div>
                <div className="text-sm text-gray-500 mt-0.5">{item.description}</div>
              </div>
              {!item.disabled && (
                <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Account Section */}
      <div className="max-w-lg mx-auto px-4 mt-6">
        <div className="bg-white rounded-2xl shadow-sm p-2">
          <button
            onClick={() => setShowLogoutConfirm(true)}
            className="w-full flex items-center gap-4 p-4 rounded-xl hover:bg-red-50 active:scale-98 transition-all"
          >
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-red-500 to-rose-600 flex items-center justify-center text-2xl">
              🚪
            </div>
            <div className="flex-1 text-left">
              <div className="font-semibold text-red-600">Logout</div>
              <div className="text-sm text-red-400 mt-0.5">Sign out of your account</div>
            </div>
            <svg className="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      </div>

      {/* App Version */}
      <div className="max-w-lg mx-auto px-4 mt-6 text-center">
        <div className="text-xs text-gray-400">Runway v1.0.0</div>
        <div className="text-xs text-gray-400 mt-1">Made with ❤️ for smarter finances</div>
      </div>

      {/* Logout Confirmation Modal */}
      {showLogoutConfirm && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl p-6 max-w-sm w-full shadow-2xl">
            <div className="text-center mb-6">
              <div className="w-16 h-16 rounded-full bg-red-100 mx-auto flex items-center justify-center text-3xl mb-4">
                🚪
              </div>
              <h2 className="text-xl font-bold text-gray-900 mb-2">Logout?</h2>
              <p className="text-sm text-gray-500">Are you sure you want to sign out?</p>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setShowLogoutConfirm(false)}
                className="flex-1 py-3 px-4 rounded-xl border-2 border-gray-200 font-semibold text-gray-700 hover:bg-gray-50 active:scale-95 transition-all"
              >
                Cancel
              </button>
              <button
                onClick={handleLogout}
                className="flex-1 py-3 px-4 rounded-xl bg-gradient-to-r from-red-500 to-rose-600 text-white font-semibold hover:shadow-lg active:scale-95 transition-all"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
