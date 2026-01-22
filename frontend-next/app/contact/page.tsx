'use client';

import { useState, useEffect } from 'react';
import Header from '@/components/public/Header';
import Footer from '@/components/public/Footer';
import { Mail, MapPin, Phone, Send, Loader2 } from 'lucide-react';
import { getApiUrl } from '@/lib/api';

interface SiteSettings {
  contact_email: string;
  contact_phone: string;
  contact_phone_enabled: boolean;
  contact_address: string;
  contact_address_enabled: boolean;
  support_email: string;
  business_email: string;
  contact_page_title: string;
  contact_page_subtitle: string;
  contact_page_enabled: boolean;
}

export default function ContactPage() {
  const [settings, setSettings] = useState<SiteSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    subject: '',
    message: '',
  });
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const apiUrl = getApiUrl();
      const response = await fetch(`${apiUrl}/settings/`);
      if (response.ok) {
        const data = await response.json();
        setSettings(data);
      }
    } catch (error) {
      console.error('Failed to fetch settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus('loading');

    // Simulate API call (implement real contact form API later)
    setTimeout(() => {
      setStatus('success');
      setFormData({ name: '', email: '', subject: '', message: '' });
      setTimeout(() => setStatus('idle'), 3000);
    }, 1000);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  // Check if we have any contact info to show
  const contactEmail = settings?.contact_email || 'info@freshmotors.net';
  const hasEmail = true; // Always show email
  const hasPhone = settings?.contact_phone && settings?.contact_phone_enabled;
  const hasAddress = settings?.contact_address && settings?.contact_address_enabled;
  const hasSupportEmail = settings?.support_email;
  const hasBusinessEmail = settings?.business_email;

  if (loading) {
    return (
      <>
        <Header />
        <main className="flex-1 bg-gray-50 flex items-center justify-center min-h-[60vh]">
          <Loader2 className="animate-spin text-purple-600" size={48} />
        </main>
        <Footer />
      </>
    );
  }

  return (
    <>
      <Header />
      
      <main className="flex-1 bg-gray-50">
        {/* Hero Section */}
        <div className="bg-gradient-to-r from-slate-900 via-purple-900 to-gray-900 text-white py-20">
          <div className="container mx-auto px-4 text-center">
            <h1 className="text-4xl md:text-5xl font-black mb-4">
              {settings?.contact_page_title || 'Contact Us'}
            </h1>
            <p className="text-xl text-gray-300 max-w-3xl mx-auto">
              {settings?.contact_page_subtitle || "Have a question, suggestion, or just want to say hello? We'd love to hear from you!"}
            </p>
          </div>
        </div>

        <div className="container mx-auto px-4 py-12">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Contact Information */}
            <div className="lg:col-span-1 space-y-6">
              {/* Email - always shown */}
              {hasEmail && (
                <div className="bg-white rounded-xl shadow-md p-6">
                  <div className="flex items-start gap-4 mb-4">
                    <div className="bg-purple-100 p-3 rounded-lg">
                      <Mail className="text-purple-600" size={24} />
                    </div>
                    <div>
                      <h3 className="font-bold text-gray-900 mb-1">Email Us</h3>
                      <a 
                        href={`mailto:${contactEmail}`}
                        className="text-purple-600 hover:text-purple-800 text-sm block"
                      >
                        {contactEmail}
                      </a>
                      {hasSupportEmail && (
                        <a 
                          href={`mailto:${settings.support_email}`}
                          className="text-gray-600 hover:text-gray-800 text-sm block mt-1"
                        >
                          {settings.support_email}
                        </a>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Phone - only shown if enabled */}
              {hasPhone && (
                <div className="bg-white rounded-xl shadow-md p-6">
                  <div className="flex items-start gap-4 mb-4">
                    <div className="bg-indigo-100 p-3 rounded-lg">
                      <Phone className="text-indigo-600" size={24} />
                    </div>
                    <div>
                      <h3 className="font-bold text-gray-900 mb-1">Call Us</h3>
                      <a 
                        href={`tel:${settings.contact_phone.replace(/\s/g, '')}`}
                        className="text-gray-600 hover:text-gray-800 text-sm"
                      >
                        {settings.contact_phone}
                      </a>
                    </div>
                  </div>
                </div>
              )}

              {/* Address - only shown if enabled */}
              {hasAddress && (
                <div className="bg-white rounded-xl shadow-md p-6">
                  <div className="flex items-start gap-4 mb-4">
                    <div className="bg-blue-100 p-3 rounded-lg">
                      <MapPin className="text-blue-600" size={24} />
                    </div>
                    <div>
                      <h3 className="font-bold text-gray-900 mb-1">Visit Us</h3>
                      {settings.contact_address.split('\n').map((line, idx) => (
                        <p key={idx} className="text-gray-600 text-sm">{line}</p>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Business Email */}
              {hasBusinessEmail && (
                <div className="bg-gradient-to-br from-purple-600 to-indigo-600 rounded-xl shadow-md p-6 text-white">
                  <h3 className="font-bold mb-2">Business Inquiries</h3>
                  <p className="text-sm text-purple-100 mb-3">
                    For advertising, partnerships, or press inquiries, please contact:
                  </p>
                  <a 
                    href={`mailto:${settings.business_email}`}
                    className="text-sm font-medium hover:underline"
                  >
                    {settings.business_email}
                  </a>
                </div>
              )}

              {/* No contact info message */}
              {!hasEmail && !hasPhone && !hasAddress && (
                <div className="bg-gray-100 rounded-xl p-6 text-center">
                  <p className="text-gray-600">
                    Please use the contact form to get in touch with us.
                  </p>
                </div>
              )}
            </div>

            {/* Contact Form */}
            <div className="lg:col-span-2">
              <div className="bg-white rounded-2xl shadow-lg p-8">
                <h2 className="text-2xl font-black text-gray-900 mb-6">Send Us a Message</h2>
                
                <form onSubmit={handleSubmit} className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                      <label htmlFor="name" className="block text-sm font-bold text-gray-900 mb-2">
                        Your Name *
                      </label>
                      <input
                        type="text"
                        id="name"
                        name="name"
                        value={formData.name}
                        onChange={handleChange}
                        required
                        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent text-gray-900 bg-white"
                        placeholder="John Doe"
                      />
                    </div>

                    <div>
                      <label htmlFor="email" className="block text-sm font-bold text-gray-900 mb-2">
                        Your Email *
                      </label>
                      <input
                        type="email"
                        id="email"
                        name="email"
                        value={formData.email}
                        onChange={handleChange}
                        required
                        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent text-gray-900 bg-white"
                        placeholder="john@example.com"
                      />
                    </div>
                  </div>

                  <div>
                    <label htmlFor="subject" className="block text-sm font-bold text-gray-900 mb-2">
                      Subject *
                    </label>
                    <input
                      type="text"
                      id="subject"
                      name="subject"
                      value={formData.subject}
                      onChange={handleChange}
                      required
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent text-gray-900 bg-white"
                      placeholder="How can we help?"
                    />
                  </div>

                  <div>
                    <label htmlFor="message" className="block text-sm font-bold text-gray-900 mb-2">
                      Message *
                    </label>
                    <textarea
                      id="message"
                      name="message"
                      value={formData.message}
                      onChange={handleChange}
                      required
                      rows={6}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent text-gray-900 bg-white"
                      placeholder="Tell us more about your inquiry..."
                    />
                  </div>

                  {status === 'success' && (
                    <div className="bg-green-50 border border-green-200 text-green-800 px-4 py-3 rounded-lg">
                      ✓ Thank you! Your message has been sent successfully. We'll get back to you soon.
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={status === 'loading'}
                    className="w-full md:w-auto px-8 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-lg font-bold hover:from-purple-700 hover:to-indigo-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                  >
                    {status === 'loading' ? (
                      'Sending...'
                    ) : (
                      <>
                        <Send size={20} />
                        Send Message
                      </>
                    )}
                  </button>
                </form>
              </div>
            </div>
          </div>
        </div>
      </main>
      
      <Footer />
    </>
  );
}
