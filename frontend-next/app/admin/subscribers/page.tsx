'use client';

import { useState, useEffect } from 'react';
import { 
  Mail, 
  Search, 
  Trash2, 
  Download, 
  Send, 
  Loader2, 
  Users,
  UserCheck,
  UserX,
  X
} from 'lucide-react';
import { getApiUrl } from '@/lib/api';

interface Subscriber {
  id: number;
  email: string;
  is_active: boolean;
  created_at: string;
  unsubscribed_at: string | null;
}

export default function SubscribersPage() {
  const [subscribers, setSubscribers] = useState<Subscriber[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filter, setFilter] = useState<'all' | 'active' | 'inactive'>('all');
  const [showNewsletter, setShowNewsletter] = useState(false);
  const [newsletterForm, setNewsletterForm] = useState({ subject: '', message: '' });
  const [sending, setSending] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    fetchSubscribers();
  }, []);

  const fetchSubscribers = async () => {
    try {
      const apiUrl = getApiUrl();
      const token = localStorage.getItem('access_token');

      const response = await fetch(`${apiUrl}/subscribers/`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        const data = await response.json();
        const subs = Array.isArray(data) ? data : data.results || [];
        setSubscribers(subs);
      }
    } catch (error) {
      console.error('Failed to fetch subscribers:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to remove this subscriber?')) return;

    try {
      const apiUrl = getApiUrl();
      const token = localStorage.getItem('access_token');

      await fetch(`${apiUrl}/subscribers/${id}/`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      setSubscribers(subscribers.filter(s => s.id !== id));
      setMessage({ type: 'success', text: 'Subscriber removed' });
    } catch {
      setMessage({ type: 'error', text: 'Failed to remove subscriber' });
    }
  };

  const handleSendNewsletter = async (e: React.FormEvent) => {
    e.preventDefault();
    setSending(true);
    setMessage(null);

    try {
      const apiUrl = getApiUrl();
      const token = localStorage.getItem('access_token');

      const response = await fetch(`${apiUrl}/subscribers/send_newsletter/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(newsletterForm)
      });

      const data = await response.json();

      if (response.ok) {
        setMessage({ type: 'success', text: data.message || 'Newsletter sent!' });
        setShowNewsletter(false);
        setNewsletterForm({ subject: '', message: '' });
      } else {
        setMessage({ type: 'error', text: data.error || 'Failed to send newsletter' });
      }
    } catch {
      setMessage({ type: 'error', text: 'An error occurred' });
    } finally {
      setSending(false);
    }
  };

  const exportSubscribers = () => {
    const activeEmails = subscribers
      .filter(s => s.is_active)
      .map(s => s.email)
      .join('\n');
    
    const blob = new Blob([activeEmails], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'subscribers.txt';
    a.click();
    URL.revokeObjectURL(url);
  };

  const filteredSubscribers = subscribers.filter(sub => {
    const matchesSearch = sub.email.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesFilter = filter === 'all' || 
      (filter === 'active' && sub.is_active) || 
      (filter === 'inactive' && !sub.is_active);
    return matchesSearch && matchesFilter;
  });

  const activeCount = subscribers.filter(s => s.is_active).length;
  const inactiveCount = subscribers.filter(s => !s.is_active).length;

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="animate-spin text-purple-600" size={48} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <h1 className="text-2xl sm:text-3xl font-black text-gray-950">Newsletter Subscribers</h1>
        
        <div className="flex gap-2">
          <button
            onClick={exportSubscribers}
            className="flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
          >
            <Download size={18} />
            <span className="hidden sm:inline">Export</span>
          </button>
          <button
            onClick={() => setShowNewsletter(true)}
            className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
          >
            <Send size={18} />
            Send Newsletter
          </button>
        </div>
      </div>

      {message && (
        <div className={`p-4 rounded-lg ${
          message.type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'
        }`}>
          {message.text}
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl shadow-md p-6">
          <div className="flex items-center gap-3">
            <div className="bg-purple-100 p-3 rounded-lg">
              <Users className="text-purple-600" size={24} />
            </div>
            <div>
              <p className="text-2xl font-black text-gray-900">{subscribers.length}</p>
              <p className="text-gray-500 text-sm">Total Subscribers</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl shadow-md p-6">
          <div className="flex items-center gap-3">
            <div className="bg-green-100 p-3 rounded-lg">
              <UserCheck className="text-green-600" size={24} />
            </div>
            <div>
              <p className="text-2xl font-black text-gray-900">{activeCount}</p>
              <p className="text-gray-500 text-sm">Active</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl shadow-md p-6">
          <div className="flex items-center gap-3">
            <div className="bg-red-100 p-3 rounded-lg">
              <UserX className="text-red-600" size={24} />
            </div>
            <div>
              <p className="text-2xl font-black text-gray-900">{inactiveCount}</p>
              <p className="text-gray-500 text-sm">Unsubscribed</p>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-md p-4">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
            <input
              type="text"
              placeholder="Search by email..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
            />
          </div>
          <div className="flex gap-2">
            {[
              { value: 'all', label: 'All' },
              { value: 'active', label: 'Active' },
              { value: 'inactive', label: 'Inactive' }
            ].map((option) => (
              <button
                key={option.value}
                onClick={() => setFilter(option.value as 'all' | 'active' | 'inactive')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  filter === option.value
                    ? 'bg-purple-600 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Subscribers Table */}
      <div className="bg-white rounded-xl shadow-md overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left py-4 px-6 text-sm font-semibold text-gray-600">Email</th>
                <th className="text-left py-4 px-6 text-sm font-semibold text-gray-600">Status</th>
                <th className="text-left py-4 px-6 text-sm font-semibold text-gray-600">Subscribed</th>
                <th className="text-right py-4 px-6 text-sm font-semibold text-gray-600">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredSubscribers.length > 0 ? (
                filteredSubscribers.map((subscriber) => (
                  <tr key={subscriber.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-4 px-6">
                      <div className="flex items-center gap-3">
                        <div className="bg-purple-100 p-2 rounded-full">
                          <Mail className="text-purple-600" size={16} />
                        </div>
                        <span className="font-medium text-gray-900">{subscriber.email}</span>
                      </div>
                    </td>
                    <td className="py-4 px-6">
                      <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                        subscriber.is_active
                          ? 'bg-green-100 text-green-700'
                          : 'bg-red-100 text-red-700'
                      }`}>
                        {subscriber.is_active ? 'Active' : 'Unsubscribed'}
                      </span>
                    </td>
                    <td className="py-4 px-6">
                      <span className="text-gray-500 text-sm">
                        {new Date(subscriber.created_at).toLocaleDateString()}
                      </span>
                    </td>
                    <td className="py-4 px-6 text-right">
                      <button
                        onClick={() => handleDelete(subscriber.id)}
                        className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        title="Delete subscriber"
                      >
                        <Trash2 size={18} />
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={4} className="py-12 text-center text-gray-500">
                    {searchQuery ? 'No subscribers found matching your search' : 'No subscribers yet'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Newsletter Modal */}
      {showNewsletter && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-gray-200 flex items-center justify-between">
              <h2 className="text-xl font-bold text-gray-900">Send Newsletter</h2>
              <button
                onClick={() => setShowNewsletter(false)}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                <X size={20} />
              </button>
            </div>
            
            <form onSubmit={handleSendNewsletter} className="p-6 space-y-4">
              <div className="bg-purple-50 p-4 rounded-lg">
                <p className="text-purple-800 text-sm">
                  This will send an email to <strong>{activeCount}</strong> active subscribers.
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Subject
                </label>
                <input
                  type="text"
                  value={newsletterForm.subject}
                  onChange={(e) => setNewsletterForm({ ...newsletterForm, subject: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
                  placeholder="Newsletter subject..."
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Message
                </label>
                <textarea
                  value={newsletterForm.message}
                  onChange={(e) => setNewsletterForm({ ...newsletterForm, message: e.target.value })}
                  rows={6}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
                  placeholder="Write your newsletter message..."
                  required
                />
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowNewsletter(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={sending}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
                >
                  {sending ? <Loader2 className="animate-spin" size={18} /> : <Send size={18} />}
                  Send to {activeCount} subscribers
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
