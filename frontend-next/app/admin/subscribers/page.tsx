'use client';

import { useState, useEffect, useRef } from 'react';
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
  X,
  Plus,
  Upload,
  History,
  UserPlus
} from 'lucide-react';
import { getApiUrl } from '@/lib/api';
import { authenticatedFetch } from '@/lib/authenticatedFetch';

interface Subscriber {
  id: number;
  email: string;
  is_active: boolean;
  created_at: string;
  unsubscribed_at: string | null;
}

interface NewsletterHistoryItem {
  id: number;
  subject: string;
  message: string;
  sent_to_count: number;
  sent_at: string;
  sent_by_name: string;
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

  // New states
  const [showAddModal, setShowAddModal] = useState(false);
  const [newEmail, setNewEmail] = useState('');
  const [addingSubscriber, setAddingSubscriber] = useState(false);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [showImportModal, setShowImportModal] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importing, setImporting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [activeTab, setActiveTab] = useState<'subscribers' | 'history'>('subscribers');
  const [history, setHistory] = useState<NewsletterHistoryItem[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  useEffect(() => {
    fetchSubscribers();
  }, []);

  useEffect(() => {
    if (activeTab === 'history') {
      fetchHistory();
    }
  }, [activeTab]);

  const fetchSubscribers = async () => {
    try {
      const response = await authenticatedFetch('/subscribers/');

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

  const fetchHistory = async () => {
    setLoadingHistory(true);
    try {
      const response = await authenticatedFetch('/subscribers/newsletter_history/');

      if (response.ok) {
        const data = await response.json();
        setHistory(data);
      }
    } catch (error) {
      console.error('Failed to fetch history:', error);
    } finally {
      setLoadingHistory(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to remove this subscriber?')) return;

    try {
      await authenticatedFetch(`/subscribers/${id}/`, {
        method: 'DELETE',
      });

      setSubscribers(subscribers.filter(s => s.id !== id));
      setSelectedIds(selectedIds.filter(selectedId => selectedId !== id));
      setMessage({ type: 'success', text: 'Subscriber removed' });
    } catch {
      setMessage({ type: 'error', text: 'Failed to remove subscriber' });
    }
  };

  const handleBulkDelete = async () => {
    if (selectedIds.length === 0) return;
    if (!confirm(`Are you sure you want to delete ${selectedIds.length} subscriber(s)?`)) return;

    try {
      const response = await authenticatedFetch('/subscribers/bulk_delete/', {
        method: 'POST',
        body: JSON.stringify({ ids: selectedIds })
      });

      if (response.ok) {
        setSubscribers(subscribers.filter(s => !selectedIds.includes(s.id)));
        setSelectedIds([]);
        setMessage({ type: 'success', text: `Deleted ${selectedIds.length} subscribers` });
      }
    } catch {
      setMessage({ type: 'error', text: 'Failed to delete subscribers' });
    }
  };

  const handleAddSubscriber = async (e: React.FormEvent) => {
    e.preventDefault();
    setAddingSubscriber(true);

    try {
      const response = await authenticatedFetch('/subscribers/', {
        method: 'POST',
        body: JSON.stringify({ email: newEmail })
      });

      if (response.ok) {
        setMessage({ type: 'success', text: 'Subscriber added successfully' });
        setShowAddModal(false);
        setNewEmail('');
        fetchSubscribers();
      } else {
        const data = await response.json();
        setMessage({ type: 'error', text: data.error || 'Failed to add subscriber' });
      }
    } catch {
      setMessage({ type: 'error', text: 'An error occurred' });
    } finally {
      setAddingSubscriber(false);
    }
  };

  const handleSendNewsletter = async (e: React.FormEvent) => {
    e.preventDefault();
    setSending(true);
    setMessage(null);

    try {
      const response = await authenticatedFetch('/subscribers/send_newsletter/', {
        method: 'POST',
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

  const handleExportCSV = async () => {
    try {
      const response = await authenticatedFetch('/subscribers/export_csv/');

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'subscribers.csv';
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
        setMessage({ type: 'success', text: 'CSV exported successfully' });
      }
    } catch {
      setMessage({ type: 'error', text: 'Failed to export CSV' });
    }
  };

  const handleImportCSV = async () => {
    if (!importFile) return;

    setImporting(true);
    try {
      const formData = new FormData();
      formData.append('file', importFile);

      // Use authenticatedFetch but with FormData body — 
      // Content-Type header is auto-set by browser for FormData
      const response = await authenticatedFetch('/subscribers/import_csv/', {
        method: 'POST',
        body: formData,
        headers: {},  // Clear Content-Type to let browser set multipart boundary
      });

      const data = await response.json();

      if (response.ok) {
        setMessage({ type: 'success', text: `${data.added} added, ${data.skipped} skipped` });
        setShowImportModal(false);
        setImportFile(null);
        fetchSubscribers();
      } else {
        setMessage({ type: 'error', text: data.error || 'Import failed' });
      }
    } catch {
      setMessage({ type: 'error', text: 'An error occurred' });
    } finally {
      setImporting(false);
    }
  };

  const toggleSelectAll = () => {
    if (selectedIds.length === filteredSubscribers.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(filteredSubscribers.map(s => s.id));
    }
  };

  const toggleSelect = (id: number) => {
    if (selectedIds.includes(id)) {
      setSelectedIds(selectedIds.filter(selectedId => selectedId !== id));
    } else {
      setSelectedIds([...selectedIds, id]);
    }
  };

  const useAsTemplate = (item: NewsletterHistoryItem) => {
    setNewsletterForm({ subject: item.subject, message: item.message });
    setActiveTab('subscribers');
    setShowNewsletter(true);
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
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
          >
            <Plus size={18} />
            <span className="hidden sm:inline">Add</span>
          </button>
          <button
            onClick={() => setShowImportModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <Upload size={18} />
            <span className="hidden sm:inline">Import</span>
          </button>
          <button
            onClick={handleExportCSV}
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
        <div className={`p-4 rounded-lg ${message.type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'
          }`}>
          {message.text}
        </div>
      )}

      {/* Tabs */}
      <div className="bg-white rounded-xl shadow-md">
        <div className="flex border-b border-gray-200">
          <button
            onClick={() => setActiveTab('subscribers')}
            className={`flex-1 px-6 py-4 font-semibold transition-colors ${activeTab === 'subscribers'
              ? 'text-purple-600 border-b-2 border-purple-600'
              : 'text-gray-500 hover:text-gray-700'
              }`}
          >
            <div className="flex items-center justify-center gap-2">
              <Users size={20} />
              Subscribers
            </div>
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`flex-1 px-6 py-4 font-semibold transition-colors ${activeTab === 'history'
              ? 'text-purple-600 border-b-2 border-purple-600'
              : 'text-gray-500 hover:text-gray-700'
              }`}
          >
            <div className="flex items-center justify-center gap-2">
              <History size={20} />
              History
            </div>
          </button>
        </div>
      </div>

      {/* Subscribers Tab */}
      {activeTab === 'subscribers' && (
        <>
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
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${filter === option.value
                      ? 'bg-purple-600 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                      }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
              {selectedIds.length > 0 && (
                <button
                  onClick={handleBulkDelete}
                  className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                >
                  <Trash2 size={18} />
                  Delete {selectedIds.length}
                </button>
              )}
            </div>
          </div>

          {/* Subscribers Table */}
          <div className="bg-white rounded-xl shadow-md overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="px-6 py-4 text-left">
                      <input
                        type="checkbox"
                        checked={selectedIds.length === filteredSubscribers.length && filteredSubscribers.length > 0}
                        onChange={toggleSelectAll}
                        className="w-4 h-4 text-purple-600 rounded focus:ring-purple-500"
                      />
                    </th>
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
                        <td className="px-6 py-4">
                          <input
                            type="checkbox"
                            checked={selectedIds.includes(subscriber.id)}
                            onChange={() => toggleSelect(subscriber.id)}
                            className="w-4 h-4 text-purple-600 rounded focus:ring-purple-500"
                          />
                        </td>
                        <td className="py-4 px-6">
                          <div className="flex items-center gap-3">
                            <div className="bg-purple-100 p-2 rounded-full">
                              <Mail className="text-purple-600" size={16} />
                            </div>
                            <span className="font-medium text-gray-900">{subscriber.email}</span>
                          </div>
                        </td>
                        <td className="py-4 px-6">
                          <span className={`px-3 py-1 rounded-full text-xs font-medium ${subscriber.is_active
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
                      <td colSpan={5} className="py-12 text-center text-gray-500">
                        {searchQuery ? 'No subscribers found matching your search' : 'No subscribers yet'}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* History Tab */}
      {activeTab === 'history' && (
        <div className="bg-white rounded-xl shadow-md overflow-hidden">
          {loadingHistory ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="animate-spin text-purple-600" size={32} />
            </div>
          ) : history.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="text-left py-4 px-6 text-sm font-semibold text-gray-600">Subject</th>
                    <th className="text-left py-4 px-6 text-sm font-semibold text-gray-600">Sent To</th>
                    <th className="text-left py-4 px-6 text-sm font-semibold text-gray-600">Date</th>
                    <th className="text-left py-4 px-6 text-sm font-semibold text-gray-600">Sent By</th>
                    <th className="text-right py-4 px-6 text-sm font-semibold text-gray-600">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((item) => (
                    <tr key={item.id} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-4 px-6">
                        <div className="font-medium text-gray-900">{item.subject}</div>
                        <div className="text-sm text-gray-500 truncate max-w-md">{item.message}</div>
                      </td>
                      <td className="py-4 px-6">
                        <span className="px-3 py-1 bg-purple-100 text-purple-700 rounded-full text-sm font-medium">
                          {item.sent_to_count} subscribers
                        </span>
                      </td>
                      <td className="py-4 px-6">
                        <span className="text-gray-500 text-sm">
                          {new Date(item.sent_at).toLocaleString()}
                        </span>
                      </td>
                      <td className="py-4 px-6">
                        <span className="text-gray-700">{item.sent_by_name || 'Unknown'}</span>
                      </td>
                      <td className="py-4 px-6 text-right">
                        <button
                          onClick={() => useAsTemplate(item)}
                          className="px-3 py-1 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
                        >
                          Use as Template
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="py-12 text-center text-gray-500">
              No newsletters sent yet
            </div>
          )}
        </div>
      )}

      {/* Add Subscriber Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full">
            <div className="p-6 border-b border-gray-200 flex items-center justify-between">
              <h2 className="text-xl font-bold text-gray-900">Add Subscriber</h2>
              <button
                onClick={() => setShowAddModal(false)}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleAddSubscriber} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email Address
                </label>
                <input
                  type="email"
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 text-gray-900"
                  placeholder="subscriber@example.com"
                  required
                />
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={addingSubscriber}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
                >
                  {addingSubscriber ? <Loader2 className="animate-spin" size={18} /> : <UserPlus size={18} />}
                  Add Subscriber
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Import CSV Modal */}
      {showImportModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full">
            <div className="p-6 border-b border-gray-200 flex items-center justify-between">
              <h2 className="text-xl font-bold text-gray-900">Import Subscribers</h2>
              <button
                onClick={() => setShowImportModal(false)}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                <X size={20} />
              </button>
            </div>

            <div className="p-6 space-y-4">
              <div className="bg-blue-50 p-4 rounded-lg">
                <p className="text-blue-800 text-sm">
                  Upload a CSV file with an "email" column. Format:<br />
                  <code className="bg-blue-100 px-2 py-1 rounded mt-2 inline-block">email<br />user1@example.com<br />user2@example.com</code>
                </p>
              </div>

              <div>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv"
                  onChange={(e) => setImportFile(e.target.files?.[0] || null)}
                  className="hidden"
                />
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="w-full px-4 py-3 border-2 border-dashed border-gray-300 rounded-lg hover:border-purple-500 transition-colors text-gray-600 hover:text-purple-600"
                >
                  <Upload className="mx-auto mb-2" size={32} />
                  {importFile ? importFile.name : 'Click to select CSV file'}
                </button>
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowImportModal(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleImportCSV}
                  disabled={!importFile || importing}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {importing ? <Loader2 className="animate-spin" size={18} /> : <Upload size={18} />}
                  Import
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

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
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 text-gray-900"
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
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 text-gray-900"
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
