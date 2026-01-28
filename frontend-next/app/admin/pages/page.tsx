'use client';

import { useState, useEffect } from 'react';
import { Save, Info, Phone, MapPin, Mail, FileText } from 'lucide-react';
import api from '@/lib/api';

interface PageSettings {
  // Contact Info
  contact_email: string;
  contact_phone: string;
  contact_phone_enabled: boolean;
  contact_address: string;
  contact_address_enabled: boolean;
  support_email: string;
  business_email: string;
  
  // About Page
  about_page_title: string;
  about_page_content: string;
  about_page_enabled: boolean;
  
  // Privacy Page
  privacy_page_title: string;
  privacy_page_content: string;
  privacy_page_enabled: boolean;
  
  // Terms Page
  terms_page_title: string;
  terms_page_content: string;
  terms_page_enabled: boolean;
  
  // Contact Page
  contact_page_title: string;
  contact_page_subtitle: string;
  contact_page_enabled: boolean;
}

const defaultSettings: PageSettings = {
  contact_email: '',
  contact_phone: '',
  contact_phone_enabled: false,
  contact_address: '',
  contact_address_enabled: false,
  support_email: '',
  business_email: '',
  about_page_title: 'About Fresh Motors',
  about_page_content: '',
  about_page_enabled: true,
  privacy_page_title: 'Privacy Policy',
  privacy_page_content: '',
  privacy_page_enabled: true,
  terms_page_title: 'Terms of Service',
  terms_page_content: '',
  terms_page_enabled: true,
  contact_page_title: 'Contact Us',
  contact_page_subtitle: '',
  contact_page_enabled: true,
};

export default function PagesPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState<'contact' | 'about' | 'privacy' | 'terms'>('contact');
  const [formData, setFormData] = useState<PageSettings>(defaultSettings);
  const [successMessage, setSuccessMessage] = useState('');

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const response = await api.get('/settings/');
      setFormData({
        ...defaultSettings,
        ...response.data,
      });
    } catch (error) {
      console.error('Failed to fetch settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSuccessMessage('');

    try {
      await api.put('/settings/1/', formData);
      setSuccessMessage('Settings saved successfully!');
      setTimeout(() => setSuccessMessage(''), 3000);
    } catch (error: unknown) {
      console.error('Failed to save settings:', error);
      const err = error as { response?: { data?: { detail?: string } }; message?: string };
      alert('Failed to save settings: ' + (err.response?.data?.detail || err.message));
    } finally {
      setSaving(false);
    }
  };

  const handleChange = (field: keyof PageSettings, value: string | boolean) => {
    setFormData(prev => ({
      ...prev,
      [field]: value,
    }));
  };

  const tabs = [
    { id: 'contact', label: 'Contact Info', icon: Phone },
    { id: 'about', label: 'About Page', icon: Info },
    { id: 'privacy', label: 'Privacy Policy', icon: FileText },
    { id: 'terms', label: 'Terms of Service', icon: FileText },
  ] as const;

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500"></div>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 max-w-6xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl sm:text-3xl font-black text-gray-900 mb-2">Pages & Contact</h1>
        <p className="text-gray-600 text-sm sm:text-base">
          Manage your site pages and contact information. Toggle visibility with the switches.
        </p>
      </div>

      {successMessage && (
        <div className="mb-6 bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded-lg">
          {successMessage}
        </div>
      )}

      {/* Warning about fake data */}
      <div className="mb-6 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <Info className="text-yellow-600 flex-shrink-0 mt-0.5" size={20} />
          <div>
            <p className="text-yellow-800 font-medium">Important!</p>
            <p className="text-yellow-700 text-sm mt-1">
              Make sure to update all contact information with your real data. 
              Displaying fake contact information can damage trust and may cause legal issues.
              If you don&apos;t have a phone or address, disable those fields using the toggle.
            </p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-xl shadow-lg overflow-hidden">
        <div className="flex border-b border-gray-200 overflow-x-auto">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 sm:px-6 py-3 sm:py-4 text-sm font-medium whitespace-nowrap transition-colors ${
                activeTab === tab.id
                  ? 'text-indigo-600 border-b-2 border-indigo-600 bg-indigo-50'
                  : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
              }`}
            >
              <tab.icon size={18} />
              <span>{tab.label}</span>
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="p-4 sm:p-6">
          {/* Contact Info Tab */}
          {activeTab === 'contact' && (
            <div className="space-y-6">
              <h2 className="text-lg font-bold text-gray-900 border-b pb-2">Contact Page Settings</h2>
              
              {/* Contact Page Visibility */}
              <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                <div>
                  <label className="font-medium text-gray-900">Show Contact Page</label>
                  <p className="text-sm text-gray-500">Display contact page link in footer</p>
                </div>
                <button
                  type="button"
                  onClick={() => handleChange('contact_page_enabled', !formData.contact_page_enabled)}
                  className={`relative w-14 h-7 rounded-full transition-colors ${
                    formData.contact_page_enabled ? 'bg-green-500' : 'bg-gray-300'
                  }`}
                >
                  <span className={`absolute top-1 w-5 h-5 bg-white rounded-full shadow transition-transform ${
                    formData.contact_page_enabled ? 'left-8' : 'left-1'
                  }`} />
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Page Title</label>
                  <input
                    type="text"
                    value={formData.contact_page_title}
                    onChange={(e) => handleChange('contact_page_title', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 text-gray-900"
                    placeholder="Contact Us"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Subtitle</label>
                  <input
                    type="text"
                    value={formData.contact_page_subtitle}
                    onChange={(e) => handleChange('contact_page_subtitle', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 text-gray-900"
                    placeholder="Have a question? We'd love to hear from you!"
                  />
                </div>
              </div>

              <h3 className="text-md font-bold text-gray-900 border-b pb-2 mt-6">Email Addresses</h3>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    <Mail size={14} className="inline mr-1" />
                    Main Contact Email *
                  </label>
                  <input
                    type="email"
                    value={formData.contact_email}
                    onChange={(e) => handleChange('contact_email', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 text-gray-900"
                    placeholder="your-real-email@domain.com"
                    required
                  />
                  <p className="text-xs text-gray-500 mt-1">Your primary contact email</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Support Email</label>
                  <input
                    type="email"
                    value={formData.support_email}
                    onChange={(e) => handleChange('support_email', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 text-gray-900"
                    placeholder="support@domain.com (optional)"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Business Email</label>
                  <input
                    type="email"
                    value={formData.business_email}
                    onChange={(e) => handleChange('business_email', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 text-gray-900"
                    placeholder="business@domain.com (optional)"
                  />
                </div>
              </div>

              <h3 className="text-md font-bold text-gray-900 border-b pb-2 mt-6">Phone Number</h3>
              
              <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-3">
                  <Phone className="text-gray-500" size={20} />
                  <div>
                    <label className="font-medium text-gray-900">Show Phone Number</label>
                    <p className="text-sm text-gray-500">Display phone on contact page</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => handleChange('contact_phone_enabled', !formData.contact_phone_enabled)}
                  className={`relative w-14 h-7 rounded-full transition-colors ${
                    formData.contact_phone_enabled ? 'bg-green-500' : 'bg-gray-300'
                  }`}
                >
                  <span className={`absolute top-1 w-5 h-5 bg-white rounded-full shadow transition-transform ${
                    formData.contact_phone_enabled ? 'left-8' : 'left-1'
                  }`} />
                </button>
              </div>

              {formData.contact_phone_enabled && (
                <div>
                  <input
                    type="tel"
                    value={formData.contact_phone}
                    onChange={(e) => handleChange('contact_phone', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 text-gray-900"
                    placeholder="+1 (XXX) XXX-XXXX"
                  />
                  <p className="text-xs text-red-500 mt-1">⚠️ Enter your REAL phone number or disable this field</p>
                </div>
              )}

              <h3 className="text-md font-bold text-gray-900 border-b pb-2 mt-6">Physical Address</h3>
              
              <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-3">
                  <MapPin className="text-gray-500" size={20} />
                  <div>
                    <label className="font-medium text-gray-900">Show Address</label>
                    <p className="text-sm text-gray-500">Display office address on contact page</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => handleChange('contact_address_enabled', !formData.contact_address_enabled)}
                  className={`relative w-14 h-7 rounded-full transition-colors ${
                    formData.contact_address_enabled ? 'bg-green-500' : 'bg-gray-300'
                  }`}
                >
                  <span className={`absolute top-1 w-5 h-5 bg-white rounded-full shadow transition-transform ${
                    formData.contact_address_enabled ? 'left-8' : 'left-1'
                  }`} />
                </button>
              </div>

              {formData.contact_address_enabled && (
                <div>
                  <textarea
                    value={formData.contact_address}
                    onChange={(e) => handleChange('contact_address', e.target.value)}
                    rows={3}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 text-gray-900"
                    placeholder="123 Real Street&#10;City, State 12345&#10;Country"
                  />
                  <p className="text-xs text-red-500 mt-1">⚠️ Enter your REAL address or disable this field</p>
                </div>
              )}
            </div>
          )}

          {/* About Page Tab */}
          {activeTab === 'about' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                <div>
                  <label className="font-medium text-gray-900">Show About Page</label>
                  <p className="text-sm text-gray-500">Display About link in footer</p>
                </div>
                <button
                  type="button"
                  onClick={() => handleChange('about_page_enabled', !formData.about_page_enabled)}
                  className={`relative w-14 h-7 rounded-full transition-colors ${
                    formData.about_page_enabled ? 'bg-green-500' : 'bg-gray-300'
                  }`}
                >
                  <span className={`absolute top-1 w-5 h-5 bg-white rounded-full shadow transition-transform ${
                    formData.about_page_enabled ? 'left-8' : 'left-1'
                  }`} />
                </button>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Page Title</label>
                <input
                  type="text"
                  value={formData.about_page_title}
                  onChange={(e) => handleChange('about_page_title', e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 text-gray-900"
                  placeholder="About Us"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Page Content (HTML)</label>
                <textarea
                  value={formData.about_page_content}
                  onChange={(e) => handleChange('about_page_content', e.target.value)}
                  rows={15}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 text-gray-900 font-mono text-sm"
                  placeholder="<h2>Our Story</h2>&#10;<p>Write your about page content here...</p>"
                />
                <p className="text-xs text-gray-500 mt-1">You can use HTML tags for formatting. Leave empty to use default content.</p>
              </div>
            </div>
          )}

          {/* Privacy Page Tab */}
          {activeTab === 'privacy' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                <div>
                  <label className="font-medium text-gray-900">Show Privacy Policy</label>
                  <p className="text-sm text-gray-500">Display Privacy Policy link in footer</p>
                </div>
                <button
                  type="button"
                  onClick={() => handleChange('privacy_page_enabled', !formData.privacy_page_enabled)}
                  className={`relative w-14 h-7 rounded-full transition-colors ${
                    formData.privacy_page_enabled ? 'bg-green-500' : 'bg-gray-300'
                  }`}
                >
                  <span className={`absolute top-1 w-5 h-5 bg-white rounded-full shadow transition-transform ${
                    formData.privacy_page_enabled ? 'left-8' : 'left-1'
                  }`} />
                </button>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Page Title</label>
                <input
                  type="text"
                  value={formData.privacy_page_title}
                  onChange={(e) => handleChange('privacy_page_title', e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 text-gray-900"
                  placeholder="Privacy Policy"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Privacy Policy Content (HTML)</label>
                <textarea
                  value={formData.privacy_page_content}
                  onChange={(e) => handleChange('privacy_page_content', e.target.value)}
                  rows={15}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 text-gray-900 font-mono text-sm"
                  placeholder="<h2>Privacy Policy</h2>&#10;<p>Your privacy policy content here...</p>"
                />
                <p className="text-xs text-gray-500 mt-1">Leave empty to use default content. Consider consulting a lawyer for proper privacy policy.</p>
              </div>
            </div>
          )}

          {/* Terms Page Tab */}
          {activeTab === 'terms' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                <div>
                  <label className="font-medium text-gray-900">Show Terms of Service</label>
                  <p className="text-sm text-gray-500">Display Terms link in footer</p>
                </div>
                <button
                  type="button"
                  onClick={() => handleChange('terms_page_enabled', !formData.terms_page_enabled)}
                  className={`relative w-14 h-7 rounded-full transition-colors ${
                    formData.terms_page_enabled ? 'bg-green-500' : 'bg-gray-300'
                  }`}
                >
                  <span className={`absolute top-1 w-5 h-5 bg-white rounded-full shadow transition-transform ${
                    formData.terms_page_enabled ? 'left-8' : 'left-1'
                  }`} />
                </button>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Page Title</label>
                <input
                  type="text"
                  value={formData.terms_page_title}
                  onChange={(e) => handleChange('terms_page_title', e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 text-gray-900"
                  placeholder="Terms of Service"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Terms of Service Content (HTML)</label>
                <textarea
                  value={formData.terms_page_content}
                  onChange={(e) => handleChange('terms_page_content', e.target.value)}
                  rows={15}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 text-gray-900 font-mono text-sm"
                  placeholder="<h2>Terms of Service</h2>&#10;<p>Your terms content here...</p>"
                />
                <p className="text-xs text-gray-500 mt-1">Leave empty to use default content. Consider consulting a lawyer for proper terms.</p>
              </div>
            </div>
          )}

          {/* Submit Button */}
          <div className="mt-8 flex justify-end">
            <button
              type="submit"
              disabled={saving}
              className="flex items-center gap-2 px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 font-medium"
            >
              {saving ? (
                <>
                  <div className="animate-spin rounded-full h-5 w-5 border-t-2 border-white"></div>
                  <span>Saving...</span>
                </>
              ) : (
                <>
                  <Save size={20} />
                  <span>Save Changes</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
