'use client';

import { useState, useEffect } from 'react';
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

  if (loading) {
    return (
      <main className="flex-1 bg-gray-50 flex items-center justify-center min-h-[60vh]">
        <Loader2 className="animate-spin text-purple-600" size={48} />
      </main>
    );
  }

  // Safely extract settings after loading is complete
  const contactEmail = settings?.contact_email || 'info@freshmotors.net';
  const hasPhone = !!(settings?.contact_phone && settings?.contact_phone_enabled);
  const hasAddress = !!(settings?.contact_address && settings?.contact_address_enabled);
  const hasSupportEmail = settings?.support_email;
  const hasBusinessEmail = settings?.business_email;

  return (
    <>
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

        <div className="container mx-auto px-4 py-12 max-w-6xl">
          <div className="bg-white rounded-3xl shadow-xl overflow-hidden flex flex-col lg:flex-row border border-gray-100">

            {/* Contact Information Sidebar */}
            <div className="lg:w-1/3 bg-gradient-to-br from-indigo-900 via-purple-900 to-slate-900 p-8 sm:p-12 text-white flex flex-col justify-between">
              <div>
                <h2 className="text-3xl font-black mb-6">Get in Touch</h2>
                <p className="text-purple-100/80 mb-10 leading-relaxed font-medium">
                  We're here to help! Whether you have questions about a vehicle, feedback on our content, or business inquiries, reach out using any method below.
                </p>

                <div className="space-y-8">
                  {/* Email */}
                  <div className="flex items-start gap-4 group">
                    <div className="bg-white/10 p-3 rounded-2xl group-hover:bg-white/20 transition-colors">
                      <Mail className="text-purple-300" size={24} />
                    </div>
                    <div>
                      <p className="text-xs font-black uppercase tracking-widest text-purple-300/80 mb-1">Email Us</p>
                      <a href={`mailto:${contactEmail}`} className="text-lg font-bold hover:text-purple-300 transition-colors">
                        {contactEmail}
                      </a>
                      {hasSupportEmail && (
                        <p className="text-sm text-purple-200/60 mt-0.5">Support: {settings?.support_email}</p>
                      )}
                    </div>
                  </div>

                  {/* Phone */}
                  {hasPhone && settings?.contact_phone && (
                    <div className="flex items-start gap-4 group">
                      <div className="bg-white/10 p-3 rounded-2xl group-hover:bg-white/20 transition-colors">
                        <Phone className="text-purple-300" size={24} />
                      </div>
                      <div>
                        <p className="text-xs font-black uppercase tracking-widest text-purple-300/80 mb-1">Call Us</p>
                        <a href={`tel:${settings.contact_phone.replace(/\s/g, '')}`} className="text-lg font-bold hover:text-purple-300 transition-colors">
                          {settings.contact_phone}
                        </a>
                      </div>
                    </div>
                  )}

                  {/* Address */}
                  {hasAddress && settings?.contact_address && (
                    <div className="flex items-start gap-4 group">
                      <div className="bg-white/10 p-3 rounded-2xl group-hover:bg-white/20 transition-colors">
                        <MapPin className="text-purple-300" size={24} />
                      </div>
                      <div>
                        <p className="text-xs font-black uppercase tracking-widest text-purple-300/80 mb-1">Visit Us</p>
                        <div className="text-base font-medium text-purple-50 line-clamp-3">
                          {settings.contact_address.split('\n').map((line, idx) => (
                            <span key={idx} className="block">{line}</span>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Business Inquiries Box */}
              {hasBusinessEmail && settings?.business_email && (
                <div className="mt-12 p-6 bg-white/5 border border-white/10 rounded-2xl">
                  <p className="text-xs font-black uppercase tracking-widest text-indigo-300 mb-2">Business Inquiries</p>
                  <p className="text-sm text-indigo-100/70 mb-3">For partnerships or press, please email us directly:</p>
                  <a href={`mailto:${settings.business_email}`} className="text-sm font-black text-white hover:text-indigo-300 transition-colors border-b border-indigo-500/30 pb-0.5">
                    {settings.business_email}
                  </a>
                </div>
              )}
            </div>

            {/* Contact Form Area */}
            <div className="lg:w-2/3 p-8 sm:p-12 bg-white">
              <h3 className="text-2xl font-black text-gray-900 mb-1">Send a Message</h3>
              <p className="text-gray-500 mb-8 font-medium">Use the form below and we'll reply within 24 hours.</p>

              <form onSubmit={handleSubmit} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <label htmlFor="name" className="text-sm font-black text-gray-700 uppercase tracking-tight ml-1">
                      Full Name
                    </label>
                    <input
                      type="text"
                      id="name"
                      name="name"
                      value={formData.name}
                      onChange={handleChange}
                      required
                      className="w-full px-5 py-3 border-2 border-gray-100 rounded-2xl focus:ring-0 focus:border-indigo-600 transition-all text-gray-900 font-medium placeholder-gray-300"
                      placeholder="e.g. Michael Knight"
                    />
                  </div>

                  <div className="space-y-2">
                    <label htmlFor="email" className="text-sm font-black text-gray-700 uppercase tracking-tight ml-1">
                      Your Email
                    </label>
                    <input
                      type="email"
                      id="email"
                      name="email"
                      value={formData.email}
                      onChange={handleChange}
                      required
                      className="w-full px-5 py-3 border-2 border-gray-100 rounded-2xl focus:ring-0 focus:border-indigo-600 transition-all text-gray-900 font-medium placeholder-gray-300"
                      placeholder="e.g. michael@knightrider.com"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <label htmlFor="subject" className="text-sm font-black text-gray-700 uppercase tracking-tight ml-1">
                    Subject
                  </label>
                  <input
                    type="text"
                    id="subject"
                    name="subject"
                    value={formData.subject}
                    onChange={handleChange}
                    required
                    className="w-full px-5 py-3 border-2 border-gray-100 rounded-2xl focus:ring-0 focus:border-indigo-600 transition-all text-gray-900 font-medium placeholder-gray-300"
                    placeholder="How can we help you?"
                  />
                </div>

                <div className="space-y-2">
                  <label htmlFor="message" className="text-sm font-black text-gray-700 uppercase tracking-tight ml-1">
                    Message Details
                  </label>
                  <textarea
                    id="message"
                    name="message"
                    value={formData.message}
                    onChange={handleChange}
                    required
                    rows={6}
                    className="w-full px-5 py-3 border-2 border-gray-100 rounded-2xl focus:ring-0 focus:border-indigo-600 transition-all text-gray-900 font-medium placeholder-gray-300 resize-none"
                    placeholder="Provide as much detail as possible..."
                  />
                </div>

                {status === 'success' && (
                  <div className="bg-emerald-50 border-2 border-emerald-100 text-emerald-800 px-6 py-4 rounded-2xl font-bold flex items-center gap-3 animate-in fade-in slide-in-from-top-4 duration-500">
                    <span className="text-xl">✓</span>
                    Message sent successfully! We'll be in touch soon.
                  </div>
                )}

                <div className="pt-2">
                  <button
                    type="submit"
                    disabled={status === 'loading'}
                    className="w-full sm:w-auto px-10 py-4 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-2xl font-black text-lg hover:from-indigo-700 hover:to-purple-700 hover:scale-[1.02] active:scale-[0.98] transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-indigo-200 flex items-center justify-center gap-3 group"
                  >
                    {status === 'loading' ? (
                      <Loader2 className="animate-spin" size={24} />
                    ) : (
                      <>
                        <Send size={24} className="group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform" />
                        Send Message
                      </>
                    )}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
