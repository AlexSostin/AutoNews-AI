'use client';

import { useState } from 'react';
import { Send, Loader2 } from 'lucide-react';

export default function ContactForm() {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    subject: '',
    message: '',
  });
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');

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

  return (
    <div className="lg:w-2/3 p-8 sm:p-12 bg-white">
      <h3 className="text-2xl font-black text-gray-900 mb-1">Send a Message</h3>
      <p className="text-gray-500 mb-8 font-medium">Use the form below and we&apos;ll reply within 24 hours.</p>

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
            Message sent successfully! We&apos;ll be in touch soon.
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
  );
}
