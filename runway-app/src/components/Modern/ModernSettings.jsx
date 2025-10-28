// src/components/Modern/ModernSettings.jsx
import React, { useState, useEffect } from 'react';

/**
 * ModernSettings - Comprehensive settings page for Runway
 * Features: Display preferences, FIRE goals, optimization settings, notifications, security, data backup
 */

const DEFAULT_SETTINGS = {
  // Display & Preferences
  theme: 'auto',
  currency: 'INR',
  numberFormat: 'indian',
  dateFormat: 'DD/MM/YYYY',
  language: 'en',

  // FIRE Goals
  fireTargetAmount: 0,
  currentAge: 30,
  targetRetirementAge: 45,
  annualExpenses: 0,
  safeWithdrawalRate: 4,
  fireType: 'regular',

  // Optimization
  autoSweepEnabled: false,
  sweepThreshold: 50000,
  emergencyFundMonths: 6,
  loanPrepaymentStrategy: 'avalanche',
  savingsRateGoal: 50,

  // Notifications
  largeTransactionAlert: true,
  largeTransactionThreshold: 10000,
  salaryCredits: true,
  unusualSpending: true,
  emiReminders: true,
  insuranceReminders: true,
  subscriptionReminders: true,
  monthlyNetWorth: true,
  milestoneAchievements: true,
  weeklySavingsRate: true,
  quietHoursEnabled: true,
  quietHoursStart: '22:00',
  quietHoursEnd: '08:00',
  notificationDelivery: 'push',

  // Security & Privacy
  biometricLogin: false,
  pinCode: '',
  sessionTimeout: '15',
  hideAmountsOnSwitch: true,
  requireAuthSensitive: true,
  hideDataInNotifications: false,

  // Data & Backup
  autoBackup: 'weekly',
  lastBackupDate: null
};

export default function ModernSettings({ onNavigate }) {
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [expandedSection, setExpandedSection] = useState('display');
  const [hasChanges, setHasChanges] = useState(false);
  const [showSaveSuccess, setShowSaveSuccess] = useState(false);

  // Load settings from localStorage on mount
  useEffect(() => {
    const savedSettings = localStorage.getItem('runwaySettings');
    if (savedSettings) {
      setSettings({ ...DEFAULT_SETTINGS, ...JSON.parse(savedSettings) });
    }
  }, []);

  const handleSettingChange = (key, value) => {
    setSettings(prev => ({ ...prev, [key]: value }));
    setHasChanges(true);
  };

  const handleSave = () => {
    localStorage.setItem('runwaySettings', JSON.stringify(settings));
    setHasChanges(false);
    setShowSaveSuccess(true);
    setTimeout(() => setShowSaveSuccess(false), 3000);
  };

  const handleReset = () => {
    if (window.confirm('Reset all settings to default values?')) {
      setSettings(DEFAULT_SETTINGS);
      localStorage.removeItem('runwaySettings');
      setHasChanges(false);
    }
  };

  const toggleSection = (section) => {
    setExpandedSection(expandedSection === section ? null : section);
  };

  const SettingSection = ({ id, title, icon, children }) => {
    const isExpanded = expandedSection === id;
    return (
      <div className="bg-white rounded-2xl shadow-sm overflow-hidden mb-3">
        <button
          onClick={() => toggleSection(id)}
          className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
        >
          <div className="flex items-center gap-3">
            <div className="text-2xl">{icon}</div>
            <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
          </div>
          <svg
            className={`w-5 h-5 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        {isExpanded && (
          <div className="p-4 pt-0 space-y-4 border-t border-gray-100">
            {children}
          </div>
        )}
      </div>
    );
  };

  const ToggleSetting = ({ label, description, value, onChange }) => (
    <div className="flex items-start justify-between py-2">
      <div className="flex-1 pr-4">
        <div className="font-medium text-gray-900">{label}</div>
        {description && <div className="text-sm text-gray-500 mt-0.5">{description}</div>}
      </div>
      <button
        onClick={() => onChange(!value)}
        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
          value ? 'bg-green-500' : 'bg-gray-300'
        }`}
      >
        <span
          className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
            value ? 'translate-x-6' : 'translate-x-1'
          }`}
        />
      </button>
    </div>
  );

  const SelectSetting = ({ label, value, options, onChange }) => (
    <div className="py-2">
      <label className="block font-medium text-gray-900 mb-2">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
      >
        {options.map(opt => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
    </div>
  );

  const InputSetting = ({ label, value, onChange, type = 'text', placeholder, prefix, suffix }) => (
    <div className="py-2">
      <label className="block font-medium text-gray-900 mb-2">{label}</label>
      <div className="relative">
        {prefix && (
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">{prefix}</span>
        )}
        <input
          type={type}
          value={value}
          onChange={(e) => onChange(type === 'number' ? parseFloat(e.target.value) || 0 : e.target.value)}
          placeholder={placeholder}
          className={`w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent ${
            prefix ? 'pl-8' : ''
          } ${suffix ? 'pr-12' : ''}`}
        />
        {suffix && (
          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500">{suffix}</span>
        )}
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 pb-32">
      {/* Header */}
      <div className="bg-gradient-to-br from-purple-600 to-indigo-700 text-white px-4 pt-8 pb-6">
        <div className="max-w-lg mx-auto">
          <div className="flex items-center gap-3 mb-2">
            <button onClick={() => onNavigate('profile')} className="p-2 hover:bg-white/10 rounded-lg">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <h1 className="text-2xl font-bold">App Settings</h1>
          </div>
          <p className="text-sm text-white/80 ml-14">Customize your Runway experience</p>
        </div>
      </div>

      <div className="max-w-lg mx-auto px-4 -mt-2">
        {/* Display & Preferences */}
        <SettingSection id="display" title="Display & Preferences" icon="🎨">
          <SelectSetting
            label="Theme"
            value={settings.theme}
            onChange={(val) => handleSettingChange('theme', val)}
            options={[
              { value: 'light', label: 'Light' },
              { value: 'dark', label: 'Dark' },
              { value: 'auto', label: 'Auto (System)' }
            ]}
          />
          <SelectSetting
            label="Currency"
            value={settings.currency}
            onChange={(val) => handleSettingChange('currency', val)}
            options={[
              { value: 'INR', label: '₹ Indian Rupee (INR)' },
              { value: 'USD', label: '$ US Dollar (USD)' },
              { value: 'EUR', label: '€ Euro (EUR)' },
              { value: 'GBP', label: '£ British Pound (GBP)' }
            ]}
          />
          <SelectSetting
            label="Number Format"
            value={settings.numberFormat}
            onChange={(val) => handleSettingChange('numberFormat', val)}
            options={[
              { value: 'indian', label: 'Indian (1,00,000.00)' },
              { value: 'international', label: 'International (100,000.00)' }
            ]}
          />
          <SelectSetting
            label="Date Format"
            value={settings.dateFormat}
            onChange={(val) => handleSettingChange('dateFormat', val)}
            options={[
              { value: 'DD/MM/YYYY', label: 'DD/MM/YYYY' },
              { value: 'MM/DD/YYYY', label: 'MM/DD/YYYY' },
              { value: 'YYYY-MM-DD', label: 'YYYY-MM-DD' }
            ]}
          />
        </SettingSection>

        {/* FIRE Goals */}
        <SettingSection id="fire" title="FIRE Goals & Targets" icon="🎯">
          <div className="bg-gradient-to-br from-green-50 to-emerald-50 border border-green-200 rounded-xl p-4 mb-4">
            <div className="text-sm font-medium text-green-800 mb-1">Your Financial Independence Journey</div>
            <div className="text-xs text-green-600">Set your FIRE targets for personalized optimization</div>
          </div>

          <InputSetting
            label="Target FIRE Amount"
            value={settings.fireTargetAmount}
            onChange={(val) => handleSettingChange('fireTargetAmount', val)}
            type="number"
            placeholder="e.g., 10000000"
            prefix="₹"
          />
          <div className="grid grid-cols-2 gap-4">
            <InputSetting
              label="Current Age"
              value={settings.currentAge}
              onChange={(val) => handleSettingChange('currentAge', val)}
              type="number"
              placeholder="30"
              suffix="yrs"
            />
            <InputSetting
              label="Target Retirement Age"
              value={settings.targetRetirementAge}
              onChange={(val) => handleSettingChange('targetRetirementAge', val)}
              type="number"
              placeholder="45"
              suffix="yrs"
            />
          </div>
          <InputSetting
            label="Annual Expenses"
            value={settings.annualExpenses}
            onChange={(val) => handleSettingChange('annualExpenses', val)}
            type="number"
            placeholder="e.g., 600000"
            prefix="₹"
          />
          <InputSetting
            label="Safe Withdrawal Rate"
            value={settings.safeWithdrawalRate}
            onChange={(val) => handleSettingChange('safeWithdrawalRate', val)}
            type="number"
            placeholder="4"
            suffix="%"
          />
          <SelectSetting
            label="FIRE Type"
            value={settings.fireType}
            onChange={(val) => handleSettingChange('fireType', val)}
            options={[
              { value: 'lean', label: 'Lean FIRE (Minimal spending)' },
              { value: 'regular', label: 'Regular FIRE (Moderate lifestyle)' },
              { value: 'fat', label: 'Fat FIRE (Comfortable lifestyle)' }
            ]}
          />
        </SettingSection>

        {/* Optimization Settings */}
        <SettingSection id="optimization" title="Optimization Settings" icon="⚡">
          <div className="bg-gradient-to-br from-blue-50 to-cyan-50 border border-blue-200 rounded-xl p-4 mb-4">
            <div className="text-sm font-medium text-blue-800 mb-1">Smart Money Management</div>
            <div className="text-xs text-blue-600">Configure automated optimization strategies</div>
          </div>

          <div className="border-b border-gray-200 pb-4 mb-4">
            <h4 className="font-semibold text-gray-900 mb-3">Salary Sweep</h4>
            <ToggleSetting
              label="Enable Auto-Sweep"
              description="Automatically move excess funds to high-yield accounts"
              value={settings.autoSweepEnabled}
              onChange={(val) => handleSettingChange('autoSweepEnabled', val)}
            />
            {settings.autoSweepEnabled && (
              <>
                <InputSetting
                  label="Sweep Threshold"
                  value={settings.sweepThreshold}
                  onChange={(val) => handleSettingChange('sweepThreshold', val)}
                  type="number"
                  placeholder="50000"
                  prefix="₹"
                />
                <InputSetting
                  label="Emergency Fund Buffer"
                  value={settings.emergencyFundMonths}
                  onChange={(val) => handleSettingChange('emergencyFundMonths', val)}
                  type="number"
                  placeholder="6"
                  suffix="months"
                />
              </>
            )}
          </div>

          <div className="border-b border-gray-200 pb-4 mb-4">
            <h4 className="font-semibold text-gray-900 mb-3">Loan Prepayment</h4>
            <SelectSetting
              label="Prepayment Strategy"
              value={settings.loanPrepaymentStrategy}
              onChange={(val) => handleSettingChange('loanPrepaymentStrategy', val)}
              options={[
                { value: 'avalanche', label: 'Avalanche (Highest interest first)' },
                { value: 'snowball', label: 'Snowball (Smallest balance first)' },
                { value: 'custom', label: 'Custom Priority' }
              ]}
            />
          </div>

          <InputSetting
            label="Savings Rate Goal"
            value={settings.savingsRateGoal}
            onChange={(val) => handleSettingChange('savingsRateGoal', val)}
            type="number"
            placeholder="50"
            suffix="%"
          />
        </SettingSection>

        {/* Notifications */}
        <SettingSection id="notifications" title="Notifications & Alerts" icon="🔔">
          <div className="border-b border-gray-200 pb-4 mb-4">
            <h4 className="font-semibold text-gray-900 mb-3">Transaction Alerts</h4>
            <ToggleSetting
              label="Large Transactions"
              description="Get notified of large spending"
              value={settings.largeTransactionAlert}
              onChange={(val) => handleSettingChange('largeTransactionAlert', val)}
            />
            {settings.largeTransactionAlert && (
              <InputSetting
                label="Threshold Amount"
                value={settings.largeTransactionThreshold}
                onChange={(val) => handleSettingChange('largeTransactionThreshold', val)}
                type="number"
                prefix="₹"
              />
            )}
            <ToggleSetting
              label="Salary Credits"
              description="Notify when salary is credited"
              value={settings.salaryCredits}
              onChange={(val) => handleSettingChange('salaryCredits', val)}
            />
            <ToggleSetting
              label="Unusual Spending"
              description="Alert on irregular spending patterns"
              value={settings.unusualSpending}
              onChange={(val) => handleSettingChange('unusualSpending', val)}
            />
          </div>

          <div className="border-b border-gray-200 pb-4 mb-4">
            <h4 className="font-semibold text-gray-900 mb-3">Bill Reminders</h4>
            <ToggleSetting
              label="EMI Payment Due"
              value={settings.emiReminders}
              onChange={(val) => handleSettingChange('emiReminders', val)}
            />
            <ToggleSetting
              label="Insurance Premium Due"
              value={settings.insuranceReminders}
              onChange={(val) => handleSettingChange('insuranceReminders', val)}
            />
            <ToggleSetting
              label="Subscription Renewals"
              value={settings.subscriptionReminders}
              onChange={(val) => handleSettingChange('subscriptionReminders', val)}
            />
          </div>

          <div className="border-b border-gray-200 pb-4 mb-4">
            <h4 className="font-semibold text-gray-900 mb-3">FIRE Progress</h4>
            <ToggleSetting
              label="Monthly Net Worth Update"
              value={settings.monthlyNetWorth}
              onChange={(val) => handleSettingChange('monthlyNetWorth', val)}
            />
            <ToggleSetting
              label="Milestone Achievements"
              value={settings.milestoneAchievements}
              onChange={(val) => handleSettingChange('milestoneAchievements', val)}
            />
            <ToggleSetting
              label="Weekly Savings Rate Summary"
              value={settings.weeklySavingsRate}
              onChange={(val) => handleSettingChange('weeklySavingsRate', val)}
            />
          </div>

          <div className="border-b border-gray-200 pb-4 mb-4">
            <h4 className="font-semibold text-gray-900 mb-3">Notification Timing</h4>
            <ToggleSetting
              label="Enable Quiet Hours"
              description="No notifications during specified times"
              value={settings.quietHoursEnabled}
              onChange={(val) => handleSettingChange('quietHoursEnabled', val)}
            />
            {settings.quietHoursEnabled && (
              <div className="grid grid-cols-2 gap-4">
                <InputSetting
                  label="Start Time"
                  value={settings.quietHoursStart}
                  onChange={(val) => handleSettingChange('quietHoursStart', val)}
                  type="time"
                />
                <InputSetting
                  label="End Time"
                  value={settings.quietHoursEnd}
                  onChange={(val) => handleSettingChange('quietHoursEnd', val)}
                  type="time"
                />
              </div>
            )}
          </div>

          <SelectSetting
            label="Notification Delivery"
            value={settings.notificationDelivery}
            onChange={(val) => handleSettingChange('notificationDelivery', val)}
            options={[
              { value: 'push', label: 'Push Notifications Only' },
              { value: 'email', label: 'Email Only' },
              { value: 'both', label: 'Push & Email' }
            ]}
          />
        </SettingSection>

        {/* Security & Privacy */}
        <SettingSection id="security" title="Security & Privacy" icon="🔒">
          <div className="border-b border-gray-200 pb-4 mb-4">
            <h4 className="font-semibold text-gray-900 mb-3">Authentication</h4>
            <ToggleSetting
              label="Biometric Login"
              description="Use fingerprint or Face ID"
              value={settings.biometricLogin}
              onChange={(val) => handleSettingChange('biometricLogin', val)}
            />
            <SelectSetting
              label="Session Timeout"
              value={settings.sessionTimeout}
              onChange={(val) => handleSettingChange('sessionTimeout', val)}
              options={[
                { value: 'immediate', label: 'Immediate' },
                { value: '5', label: '5 minutes' },
                { value: '15', label: '15 minutes' },
                { value: '30', label: '30 minutes' },
                { value: 'never', label: 'Never' }
              ]}
            />
          </div>

          <div>
            <h4 className="font-semibold text-gray-900 mb-3">Privacy Controls</h4>
            <ToggleSetting
              label="Hide Amounts on App Switch"
              description="Blur screen when switching apps"
              value={settings.hideAmountsOnSwitch}
              onChange={(val) => handleSettingChange('hideAmountsOnSwitch', val)}
            />
            <ToggleSetting
              label="Require Auth for Sensitive Actions"
              description="Extra security for important operations"
              value={settings.requireAuthSensitive}
              onChange={(val) => handleSettingChange('requireAuthSensitive', val)}
            />
            <ToggleSetting
              label="Hide Data in Notifications"
              description="Don't show amounts in notification previews"
              value={settings.hideDataInNotifications}
              onChange={(val) => handleSettingChange('hideDataInNotifications', val)}
            />
          </div>
        </SettingSection>

        {/* Data & Backup */}
        <SettingSection id="data" title="Data & Backup" icon="💾">
          <SelectSetting
            label="Auto Backup Frequency"
            value={settings.autoBackup}
            onChange={(val) => handleSettingChange('autoBackup', val)}
            options={[
              { value: 'daily', label: 'Daily' },
              { value: 'weekly', label: 'Weekly' },
              { value: 'monthly', label: 'Monthly' },
              { value: 'off', label: 'Off' }
            ]}
          />
          {settings.lastBackupDate && (
            <div className="text-sm text-gray-500 py-2">
              Last backup: {new Date(settings.lastBackupDate).toLocaleString()}
            </div>
          )}
          <button
            onClick={() => {
              // Simulate backup
              handleSettingChange('lastBackupDate', new Date().toISOString());
              alert('Backup created successfully!');
            }}
            className="w-full py-3 px-4 bg-blue-500 hover:bg-blue-600 text-white font-semibold rounded-xl transition-colors"
          >
            Create Backup Now
          </button>
          <button
            onClick={() => {
              const data = JSON.stringify(settings, null, 2);
              const blob = new Blob([data], { type: 'application/json' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = `runway-settings-${new Date().toISOString().split('T')[0]}.json`;
              document.body.appendChild(a);
              a.click();
              document.body.removeChild(a);
              URL.revokeObjectURL(url);
            }}
            className="w-full py-3 px-4 bg-green-500 hover:bg-green-600 text-white font-semibold rounded-xl transition-colors"
          >
            Export Settings (JSON)
          </button>
        </SettingSection>

        {/* Save/Reset Buttons */}
        <div className="fixed bottom-20 left-0 right-0 bg-white border-t border-gray-200 p-4 shadow-lg">
          <div className="max-w-lg mx-auto flex gap-3">
            <button
              onClick={handleReset}
              className="flex-1 py-3 px-4 border-2 border-gray-300 text-gray-700 font-semibold rounded-xl hover:bg-gray-50 transition-colors"
            >
              Reset to Defaults
            </button>
            <button
              onClick={handleSave}
              disabled={!hasChanges}
              className={`flex-1 py-3 px-4 font-semibold rounded-xl transition-all ${
                hasChanges
                  ? 'bg-gradient-to-r from-purple-500 to-indigo-600 text-white hover:shadow-lg'
                  : 'bg-gray-200 text-gray-400 cursor-not-allowed'
              }`}
            >
              {hasChanges ? 'Save Changes' : 'No Changes'}
            </button>
          </div>
        </div>

        {/* Success Toast */}
        {showSaveSuccess && (
          <div className="fixed top-4 left-1/2 -translate-x-1/2 bg-green-500 text-white px-6 py-3 rounded-full shadow-lg z-50 animate-bounce">
            ✓ Settings saved successfully!
          </div>
        )}
      </div>
    </div>
  );
}
