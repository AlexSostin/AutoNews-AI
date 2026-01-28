'use client';

import { useState, useEffect } from 'react';
import { Cookie, X, Settings, Check } from 'lucide-react';
import Link from 'next/link';

type ConsentSettings = {
  necessary: boolean; // Always true
  analytics: boolean;
  marketing: boolean;
};

const CONSENT_KEY = 'cookie_consent';
const CONSENT_SETTINGS_KEY = 'cookie_consent_settings';

export default function CookieConsent() {
  const [isVisible, setIsVisible] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [settings, setSettings] = useState<ConsentSettings>({
    necessary: true,
    analytics: false,
    marketing: false,
  });

  useEffect(() => {
    // Check if user has already consented
    const consent = localStorage.getItem(CONSENT_KEY);
    if (!consent) {
      // Small delay for better UX
      const timer = setTimeout(() => setIsVisible(true), 1000);
      return () => clearTimeout(timer);
    } else {
      // Load saved settings
      const savedSettings = localStorage.getItem(CONSENT_SETTINGS_KEY);
      if (savedSettings) {
        setSettings(JSON.parse(savedSettings));
      }
    }
  }, []);

  const saveConsent = (consentSettings: ConsentSettings) => {
    localStorage.setItem(CONSENT_KEY, 'true');
    localStorage.setItem(CONSENT_SETTINGS_KEY, JSON.stringify(consentSettings));
    setSettings(consentSettings);
    setIsVisible(false);
    
    // Trigger analytics if accepted
    if (consentSettings.analytics && typeof window !== 'undefined') {
      // Dispatch event for analytics scripts
      window.dispatchEvent(new CustomEvent('cookieConsentGranted', { 
        detail: consentSettings 
      }));
    }
  };

  const acceptAll = () => {
    saveConsent({
      necessary: true,
      analytics: true,
      marketing: true,
    });
  };

  const acceptNecessary = () => {
    saveConsent({
      necessary: true,
      analytics: false,
      marketing: false,
    });
  };

  const saveCustomSettings = () => {
    saveConsent(settings);
    setShowSettings(false);
  };

  if (!isVisible) return null;

  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black/30 backdrop-blur-sm z-[9998]"
        onClick={() => {}} // Prevent closing on backdrop click
      />
      
      {/* Main Banner */}
      <div className="fixed bottom-0 left-0 right-0 z-[9999] p-4 md:p-6">
        <div className="max-w-4xl mx-auto">
          <div className="bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 rounded-2xl shadow-2xl border border-purple-500/20 overflow-hidden">
            {/* Header */}
            <div className="bg-gradient-to-r from-purple-600/20 to-indigo-600/20 px-6 py-4 border-b border-purple-500/20">
              <div className="flex items-center gap-3">
                <div className="bg-purple-500/20 p-2 rounded-lg">
                  <Cookie className="text-purple-400" size={24} />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">Cookie Settings</h3>
                  <p className="text-sm text-gray-400">We value your privacy</p>
                </div>
              </div>
            </div>

            {/* Content */}
            <div className="p-6">
              {!showSettings ? (
                <>
                  <p className="text-gray-300 text-sm mb-6 leading-relaxed">
                    We use cookies to enhance your browsing experience, analyze site traffic, 
                    and personalize content. By clicking "Accept All", you consent to our use 
                    of cookies. You can customize your preferences or reject non-essential cookies.
                  </p>

                  {/* Quick Buttons */}
                  <div className="flex flex-col sm:flex-row gap-3">
                    <button
                      onClick={acceptAll}
                      className="flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white font-medium rounded-xl transition-all shadow-lg shadow-purple-500/25"
                    >
                      <Check size={18} />
                      Accept All
                    </button>
                    <button
                      onClick={acceptNecessary}
                      className="flex-1 px-6 py-3 bg-gray-700 hover:bg-gray-600 text-white font-medium rounded-xl transition-all"
                    >
                      Necessary Only
                    </button>
                    <button
                      onClick={() => setShowSettings(true)}
                      className="flex items-center justify-center gap-2 px-6 py-3 border border-gray-600 hover:border-purple-500 text-gray-300 hover:text-white font-medium rounded-xl transition-all"
                    >
                      <Settings size={18} />
                      Customize
                    </button>
                  </div>

                  {/* Privacy Link */}
                  <p className="mt-4 text-center text-xs text-gray-500">
                    Learn more in our{' '}
                    <Link href="/privacy-policy" className="text-purple-400 hover:text-purple-300 underline">
                      Privacy Policy
                    </Link>
                  </p>
                </>
              ) : (
                <>
                  {/* Settings Panel */}
                  <div className="space-y-4 mb-6">
                    {/* Necessary Cookies */}
                    <div className="flex items-center justify-between p-4 bg-gray-800/50 rounded-xl border border-gray-700">
                      <div className="flex-1">
                        <h4 className="text-white font-medium">Necessary Cookies</h4>
                        <p className="text-sm text-gray-400 mt-1">
                          Required for the website to function. Cannot be disabled.
                        </p>
                      </div>
                      <div className="ml-4">
                        <div className="w-12 h-7 bg-purple-600 rounded-full flex items-center justify-end px-1 cursor-not-allowed opacity-75">
                          <div className="w-5 h-5 bg-white rounded-full shadow" />
                        </div>
                      </div>
                    </div>

                    {/* Analytics Cookies */}
                    <div className="flex items-center justify-between p-4 bg-gray-800/50 rounded-xl border border-gray-700">
                      <div className="flex-1">
                        <h4 className="text-white font-medium">Analytics Cookies</h4>
                        <p className="text-sm text-gray-400 mt-1">
                          Help us understand how visitors interact with our website.
                        </p>
                      </div>
                      <div className="ml-4">
                        <button
                          onClick={() => setSettings({ ...settings, analytics: !settings.analytics })}
                          className={`w-12 h-7 rounded-full flex items-center px-1 transition-colors ${
                            settings.analytics ? 'bg-purple-600 justify-end' : 'bg-gray-600 justify-start'
                          }`}
                        >
                          <div className="w-5 h-5 bg-white rounded-full shadow" />
                        </button>
                      </div>
                    </div>

                    {/* Marketing Cookies */}
                    <div className="flex items-center justify-between p-4 bg-gray-800/50 rounded-xl border border-gray-700">
                      <div className="flex-1">
                        <h4 className="text-white font-medium">Marketing Cookies</h4>
                        <p className="text-sm text-gray-400 mt-1">
                          Used to deliver personalized advertisements.
                        </p>
                      </div>
                      <div className="ml-4">
                        <button
                          onClick={() => setSettings({ ...settings, marketing: !settings.marketing })}
                          className={`w-12 h-7 rounded-full flex items-center px-1 transition-colors ${
                            settings.marketing ? 'bg-purple-600 justify-end' : 'bg-gray-600 justify-start'
                          }`}
                        >
                          <div className="w-5 h-5 bg-white rounded-full shadow" />
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Settings Buttons */}
                  <div className="flex flex-col sm:flex-row gap-3">
                    <button
                      onClick={saveCustomSettings}
                      className="flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white font-medium rounded-xl transition-all shadow-lg shadow-purple-500/25"
                    >
                      <Check size={18} />
                      Save Preferences
                    </button>
                    <button
                      onClick={() => setShowSettings(false)}
                      className="px-6 py-3 border border-gray-600 hover:border-gray-500 text-gray-300 hover:text-white font-medium rounded-xl transition-all"
                    >
                      Back
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

// Helper hook to check consent
export function useCookieConsent() {
  const [consent, setConsent] = useState<ConsentSettings | null>(null);

  useEffect(() => {
    const savedSettings = localStorage.getItem(CONSENT_SETTINGS_KEY);
    if (savedSettings) {
      setConsent(JSON.parse(savedSettings));
    }
  }, []);

  return consent;
}

// Helper to check if analytics is allowed
export function isAnalyticsAllowed(): boolean {
  if (typeof window === 'undefined') return false;
  const savedSettings = localStorage.getItem(CONSENT_SETTINGS_KEY);
  if (!savedSettings) return false;
  const settings: ConsentSettings = JSON.parse(savedSettings);
  return settings.analytics;
}

// Helper to check if marketing is allowed
export function isMarketingAllowed(): boolean {
  if (typeof window === 'undefined') return false;
  const savedSettings = localStorage.getItem(CONSENT_SETTINGS_KEY);
  if (!savedSettings) return false;
  const settings: ConsentSettings = JSON.parse(savedSettings);
  return settings.marketing;
}
