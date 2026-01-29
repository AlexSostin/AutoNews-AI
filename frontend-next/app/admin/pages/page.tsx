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

const defaultAboutContent = `
<h2>Our Story</h2>
<p>Founded with a passion for automobiles and a commitment to delivering accurate, timely information, Fresh Motors has grown into a comprehensive platform for car enthusiasts, industry professionals, and everyday drivers alike.</p>
<p>We believe that staying informed about the automotive world should be accessible, engaging, and reliable. From breaking news about the latest electric vehicles to detailed reviews of classic sports cars, we cover it all with expertise and enthusiasm.</p>
<p>Our team of automotive journalists and industry experts work tirelessly to bring you the most relevant and interesting content, helping you make informed decisions about your next vehicle purchase or simply stay connected with the ever-evolving world of automobiles.</p>

<h2>What We Stand For</h2>
<ul>
  <li><strong>Accuracy</strong>: We verify every fact and double-check our sources to ensure you get reliable information.</li>
  <li><strong>Innovation</strong>: We stay ahead of automotive trends and emerging technologies to keep you informed.</li>
  <li><strong>Excellence</strong>: We strive for excellence in every article, review, and piece of content we publish.</li>
  <li><strong>Community</strong>: We foster a community of car enthusiasts who share our passion for automobiles.</li>
</ul>

<h2>What We Cover</h2>
<p><strong>Latest News</strong>: Breaking stories from the automotive industry, including new model announcements, technological breakthroughs, and industry trends.</p>
<p><strong>In-Depth Reviews</strong>: Comprehensive reviews of the latest vehicles, covering performance, features, safety, and value for money.</p>
<p><strong>Electric Vehicles</strong>: Dedicated coverage of the EV revolution, including battery technology, charging infrastructure, and sustainability.</p>
<p><strong>Expert Analysis</strong>: Insights from industry experts, market analysis, and predictions about the future of transportation.</p>
`;

const defaultPrivacyContent = `
<p>At Fresh Motors, we take your privacy seriously. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you visit our website. Please read this privacy policy carefully. If you do not agree with the terms of this privacy policy, please do not access the site.</p>
<p>We reserve the right to make changes to this Privacy Policy at any time and for any reason. We will alert you about any changes by updating the "Last Updated" date of this Privacy Policy.</p>

<h2>Information We Collect</h2>
<h3>Personal Data</h3>
<p>We may collect personally identifiable information, such as your name and email address, that you voluntarily give to us when you subscribe to our newsletter, submit comments or contact forms, register for an account, or participate in surveys or contests.</p>
<h3>Derivative Data</h3>
<p>Our servers may automatically collect information when you access our website, such as your IP address, browser type, operating system, referral URLs, and pages viewed.</p>

<h2>How We Use Your Information</h2>
<p>We may use the information we collect to send you our newsletter, respond to your comments, improve our website, analyze website usage and trends, and address technical issues.</p>

<h2>Cookies and Tracking Technologies</h2>
<p>We may use cookies and other tracking technologies to help customize the website and improve your experience. Most browsers are set to accept cookies by default, but you can choose to remove or reject them.</p>

<h2>Disclosure of Your Information</h2>
<p>We may share information in certain situations, such as by law or to protect rights, with third-party service providers, or in connection with business transfers.</p>

<h2>Third-Party Websites</h2>
<p>Our website may contain links to third-party websites and applications. We are not responsible for the privacy practices of these third parties.</p>

<h2>Security of Your Information</h2>
<p>We use administrative, technical, and physical security measures to protect your personal information. However, no security system is impenetrable.</p>

<h2>Newsletter and Marketing</h2>
<p>If you subscribe to our newsletter, we will send you periodic emails about automotive news. You can unsubscribe at any time.</p>

<h2>Your Rights</h2>
<p>Depending on your location, you may have the right to access, correct, or delete your personal information, object to or restrict processing, and withdraw consent.</p>

<h2>GDPR and International Users</h2>
<p>For users in the EEA, UK, or other regions with data protection laws, you have specific rights under GDPR, including the right to access, rectification, erasure, and data portability.</p>

<h2>Children's Privacy</h2>
<p>Our website is not intended for children under 16. We do not knowingly collect personal information from children under 16.</p>

<h2>Contact Us</h2>
<p>If you have questions about this Privacy Policy, please contact us through our Contact Page.</p>
`;

const defaultTermsContent = `
<p>Welcome to Fresh Motors. These Terms of Service ("Terms") govern your access to and use of our website, services, and content. By accessing or using Fresh Motors, you agree to be bound by these Terms.</p>

<h2>Acceptance of Terms</h2>
<p>By accessing and using this website, you accept and agree to be bound by these Terms and our Privacy Policy. If you do not agree to these Terms, you are not authorized to use our website.</p>

<h2>Use of Website</h2>
<p>You may use our website for lawful purposes only. You agree not to violate any laws, infringe on intellectual property, or transmit harmful code.</p>

<h2>Intellectual Property Rights</h2>
<p>All content on this website, including text, images, and logos, is the property of Fresh Motors and is protected by copyright and other laws. We grant you a limited license for personal, non-commercial use.</p>

<h2>User-Generated Content</h2>
<p>By submitting content, you grant us a license to use it and represent that you own the rights to that content.</p>

<h2>Third-Party Links and Services</h2>
<p>Our website may contain links to third-party services. We are not responsible for their content or practices.</p>

<h2>Disclaimer of Warranties</h2>
<p>Our website is provided on an "AS IS" basis. Fresh Motors disclaims all warranties, express or implied.</p>

<h2>Limitation of Liability</h2>
<p>Fresh Motors shall not be liable for any indirect, incidental, or consequential damages resulting from your use of the website.</p>

<h2>Indemnification</h2>
<p>You agree to indemnify and hold harmless Fresh Motors from any claims arising out of your use of the website or violation of these Terms.</p>

<h2>Changes to Terms</h2>
<p>We reserve the right to modify these Terms at any time. Your continued use constitutes acceptance of the new Terms.</p>

<h2>Governing Law</h2>
<p>These Terms shall be governed by the laws of your jurisdiction. Any disputes will be resolved through good-faith negotiation or arbitration.</p>

<h2>Age Requirements</h2>
<p>You must be at least 16 years of age to use this website.</p>

<h2>International Users</h2>
<p>If you access the website from outside our primary region, you are responsible for compliance with local laws.</p>

<h2>Contact Us</h2>
<p>If you have questions about these Terms, please contact us through our Contact Page.</p>
`;

const defaultSettings: PageSettings = {
  contact_email: '',
  contact_phone: '',
  contact_phone_enabled: false,
  contact_address: '',
  contact_address_enabled: false,
  support_email: '',
  business_email: '',
  about_page_title: 'About Fresh Motors',
  about_page_content: defaultAboutContent,
  about_page_enabled: true,
  privacy_page_title: 'Privacy Policy',
  privacy_page_content: defaultPrivacyContent,
  privacy_page_enabled: true,
  terms_page_title: 'Terms of Service',
  terms_page_content: defaultTermsContent,
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
      const data = response.data;

      // Handle potential array response
      const settings = Array.isArray(data) ? data[0] : data;

      setFormData({
        ...defaultSettings,
        ...settings,
        // Sync defaults if DB is empty
        about_page_content: settings?.about_page_content?.trim() || defaultAboutContent,
        privacy_page_content: settings?.privacy_page_content?.trim() || defaultPrivacyContent,
        terms_page_content: settings?.terms_page_content?.trim() || defaultTermsContent,
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
              className={`flex items-center gap-2 px-4 sm:px-6 py-3 sm:py-4 text-sm font-medium whitespace-nowrap transition-colors ${activeTab === tab.id
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
                  className={`relative w-14 h-7 rounded-full transition-colors ${formData.contact_page_enabled ? 'bg-green-500' : 'bg-gray-300'
                    }`}
                >
                  <span className={`absolute top-1 w-5 h-5 bg-white rounded-full shadow transition-transform ${formData.contact_page_enabled ? 'left-8' : 'left-1'
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
                  className={`relative w-14 h-7 rounded-full transition-colors ${formData.contact_phone_enabled ? 'bg-green-500' : 'bg-gray-300'
                    }`}
                >
                  <span className={`absolute top-1 w-5 h-5 bg-white rounded-full shadow transition-transform ${formData.contact_phone_enabled ? 'left-8' : 'left-1'
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
                  className={`relative w-14 h-7 rounded-full transition-colors ${formData.contact_address_enabled ? 'bg-green-500' : 'bg-gray-300'
                    }`}
                >
                  <span className={`absolute top-1 w-5 h-5 bg-white rounded-full shadow transition-transform ${formData.contact_address_enabled ? 'left-8' : 'left-1'
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
                  className={`relative w-14 h-7 rounded-full transition-colors ${formData.about_page_enabled ? 'bg-green-500' : 'bg-gray-300'
                    }`}
                >
                  <span className={`absolute top-1 w-5 h-5 bg-white rounded-full shadow transition-transform ${formData.about_page_enabled ? 'left-8' : 'left-1'
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
                <div className="flex items-center justify-between mb-1">
                  <label className="block text-sm font-medium text-gray-700">Page Content (HTML)</label>
                  <button
                    type="button"
                    onClick={() => handleChange('about_page_content', defaultAboutContent)}
                    className="text-xs font-bold text-indigo-600 hover:text-indigo-800 bg-indigo-50 px-2 py-1 rounded-md border border-indigo-100 transition-colors"
                  >
                    Reset to Default (Full Text)
                  </button>
                </div>
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
                  className={`relative w-14 h-7 rounded-full transition-colors ${formData.privacy_page_enabled ? 'bg-green-500' : 'bg-gray-300'
                    }`}
                >
                  <span className={`absolute top-1 w-5 h-5 bg-white rounded-full shadow transition-transform ${formData.privacy_page_enabled ? 'left-8' : 'left-1'
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
                <div className="flex items-center justify-between mb-1">
                  <label className="block text-sm font-medium text-gray-700">Privacy Policy Content (HTML)</label>
                  <button
                    type="button"
                    onClick={() => handleChange('privacy_page_content', defaultPrivacyContent)}
                    className="text-xs font-bold text-indigo-600 hover:text-indigo-800 bg-indigo-50 px-2 py-1 rounded-md border border-indigo-100 transition-colors"
                  >
                    Reset to Default (Full Text)
                  </button>
                </div>
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
                  className={`relative w-14 h-7 rounded-full transition-colors ${formData.terms_page_enabled ? 'bg-green-500' : 'bg-gray-300'
                    }`}
                >
                  <span className={`absolute top-1 w-5 h-5 bg-white rounded-full shadow transition-transform ${formData.terms_page_enabled ? 'left-8' : 'left-1'
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
                <div className="flex items-center justify-between mb-1">
                  <label className="block text-sm font-medium text-gray-700">Terms of Service Content (HTML)</label>
                  <button
                    type="button"
                    onClick={() => handleChange('terms_page_content', defaultTermsContent)}
                    className="text-xs font-bold text-indigo-600 hover:text-indigo-800 bg-indigo-50 px-2 py-1 rounded-md border border-indigo-100 transition-colors"
                  >
                    Reset to Default (Full Text)
                  </button>
                </div>
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
