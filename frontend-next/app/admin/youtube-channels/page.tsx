'use client';

import { useState, useEffect } from 'react';
import { 
  Youtube, 
  Plus, 
  Trash2, 
  Edit2, 
  Play, 
  Pause,
  RefreshCw,
  Loader2,
  X,
  Check,
  Clock,
  FileText
} from 'lucide-react';
import { getApiUrl } from '@/lib/api';
import Link from 'next/link';

interface Category {
  id: number;
  name: string;
  slug: string;
}

interface YouTubeChannel {
  id: number;
  name: string;
  channel_url: string;
  channel_id: string;
  is_enabled: boolean;
  auto_publish: boolean;
  default_category: number | null;
  category_name: string | null;
  last_checked: string | null;
  videos_processed: number;
  pending_count: number;
  created_at: string;
}

interface Schedule {
  id: number;
  is_enabled: boolean;
  frequency: string;
  scan_time_1: string;
  scan_time_2: string;
  scan_time_3: string | null;
  scan_time_4: string | null;
  last_scan: string | null;
  total_scans: number;
  total_articles_generated: number;
}

export default function YouTubeChannelsPage() {
  const [channels, setChannels] = useState<YouTubeChannel[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [schedule, setSchedule] = useState<Schedule | null>(null);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingChannel, setEditingChannel] = useState<YouTubeChannel | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    channel_url: '',
    is_enabled: true,
    auto_publish: false,
    default_category: ''
  });
  const [saving, setSaving] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const apiUrl = getApiUrl();
      const token = localStorage.getItem('access_token');
      const headers = { 'Authorization': `Bearer ${token}` };

      const [channelsRes, categoriesRes, scheduleRes] = await Promise.all([
        fetch(`${apiUrl}/youtube-channels/`, { headers }),
        fetch(`${apiUrl}/categories/`),
        fetch(`${apiUrl}/auto-publish-schedule/`, { headers })
      ]);

      if (channelsRes.ok) {
        const data = await channelsRes.json();
        setChannels(Array.isArray(data) ? data : data.results || []);
      }

      if (categoriesRes.ok) {
        const data = await categoriesRes.json();
        setCategories(Array.isArray(data) ? data : data.results || []);
      }

      if (scheduleRes.ok) {
        const data = await scheduleRes.json();
        setSchedule(data);
      }
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveChannel = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);

    try {
      const apiUrl = getApiUrl();
      const token = localStorage.getItem('access_token');
      
      const url = editingChannel 
        ? `${apiUrl}/youtube-channels/${editingChannel.id}/`
        : `${apiUrl}/youtube-channels/`;
      
      const response = await fetch(url, {
        method: editingChannel ? 'PUT' : 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          ...formData,
          default_category: formData.default_category || null
        })
      });

      if (response.ok) {
        setMessage({ type: 'success', text: editingChannel ? 'Channel updated!' : 'Channel added!' });
        setShowAddModal(false);
        setEditingChannel(null);
        setFormData({ name: '', channel_url: '', is_enabled: true, auto_publish: false, default_category: '' });
        fetchData();
      } else {
        const data = await response.json();
        setMessage({ type: 'error', text: data.detail || 'Failed to save channel' });
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'An error occurred' });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this channel?')) return;

    try {
      const apiUrl = getApiUrl();
      const token = localStorage.getItem('access_token');

const response = await fetch(`${apiUrl}/youtube-channels/${id}/`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      setChannels(channels.filter(c => c.id !== id));
      setMessage({ type: 'success', text: 'Channel deleted' });
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to delete channel' });
    }
  };

  const handleToggleEnabled = async (channel: YouTubeChannel) => {
    try {
      const apiUrl = getApiUrl();
      const token = localStorage.getItem('access_token');

      await fetch(`${apiUrl}/youtube-channels/${channel.id}/`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ is_enabled: !channel.is_enabled })
      });

      setChannels(channels.map(c => 
        c.id === channel.id ? { ...c, is_enabled: !c.is_enabled } : c
      ));
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to update channel' });
    }
  };

  const handleScanAll = async () => {
    setScanning(true);
    try {
      const apiUrl = getApiUrl();
      const token = localStorage.getItem('access_token');

      const response = await fetch(`${apiUrl}/youtube-channels/scan_all/`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        const data = await response.json();
        setMessage({ type: 'success', text: data.message });
        fetchData();
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to trigger scan' });
    } finally {
      setScanning(false);
    }
  };

  const handleScheduleToggle = async () => {
    if (!schedule) return;

    try {
      const apiUrl = getApiUrl();
      const token = localStorage.getItem('access_token');

      await fetch(`${apiUrl}/auto-publish-schedule/1/`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ is_enabled: !schedule.is_enabled })
      });

      setSchedule({ ...schedule, is_enabled: !schedule.is_enabled });
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to update schedule' });
    }
  };

  const openEditModal = (channel: YouTubeChannel) => {
    setEditingChannel(channel);
    setFormData({
      name: channel.name,
      channel_url: channel.channel_url,
      is_enabled: channel.is_enabled,
      auto_publish: channel.auto_publish,
      default_category: channel.default_category?.toString() || ''
    });
    setShowAddModal(true);
  };

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
        <div>
          <h1 className="text-2xl sm:text-3xl font-black text-gray-950">YouTube Channels</h1>
          <p className="text-gray-500 text-sm mt-1">Мониторинг каналов для автоматической генерации статей</p>
        </div>
        
        <div className="flex gap-2">
          <button
            onClick={handleScanAll}
            disabled={scanning}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
          >
            <RefreshCw size={18} className={scanning ? 'animate-spin' : ''} />
            Scan Now
          </button>
          <button
            onClick={() => {
              setEditingChannel(null);
              setFormData({ name: '', channel_url: '', is_enabled: true, auto_publish: false, default_category: '' });
              setShowAddModal(true);
            }}
            className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
          >
            <Plus size={18} />
            Add Channel
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

      {/* Schedule Settings */}
      <div className="bg-white rounded-xl shadow-md p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-3 rounded-lg ${schedule?.is_enabled ? 'bg-green-500' : 'bg-gray-400'} text-white`}>
              <Clock size={24} />
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-900">Auto-Scan Schedule</h2>
              <p className="text-sm text-gray-500">
                {schedule?.is_enabled 
                  ? `Scanning ${schedule.frequency === 'twice' ? 'twice daily' : schedule.frequency} at ${schedule.scan_time_1}${schedule.scan_time_2 ? ` & ${schedule.scan_time_2}` : ''}`
                  : 'Automatic scanning disabled'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <Link
              href="/admin/youtube-channels/schedule"
              className="text-purple-600 hover:text-purple-800 text-sm font-medium"
            >
              Configure
            </Link>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={schedule?.is_enabled || false}
                onChange={handleScheduleToggle}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-green-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-green-500"></div>
            </label>
          </div>
        </div>
        {schedule && (
          <div className="mt-4 pt-4 border-t border-gray-100 flex gap-6 text-sm">
            <div>
              <span className="text-gray-500">Total Scans:</span>
              <span className="ml-2 font-bold text-gray-900">{schedule.total_scans}</span>
            </div>
            <div>
              <span className="text-gray-500">Articles Generated:</span>
              <span className="ml-2 font-bold text-gray-900">{schedule.total_articles_generated}</span>
            </div>
            {schedule.last_scan && (
              <div>
                <span className="text-gray-500">Last Scan:</span>
                <span className="ml-2 font-bold text-gray-900">
                  {new Date(schedule.last_scan).toLocaleString()}
                </span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Pending Articles Link */}
      <Link
        href="/admin/youtube-channels/pending"
        className="block bg-gradient-to-r from-orange-500 to-red-500 rounded-xl shadow-md p-6 text-white hover:from-orange-600 hover:to-red-600 transition-all"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <FileText size={32} />
            <div>
              <h2 className="text-xl font-bold">Pending Articles</h2>
              <p className="text-orange-100">Articles waiting for your review</p>
            </div>
          </div>
          <div className="text-4xl font-black">
            {channels.reduce((sum, c) => sum + c.pending_count, 0)}
          </div>
        </div>
      </Link>

      {/* Channels List */}
      <div className="bg-white rounded-xl shadow-md overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left py-4 px-6 text-sm font-semibold text-gray-600">Channel</th>
                <th className="text-left py-4 px-6 text-sm font-semibold text-gray-600">Category</th>
                <th className="text-center py-4 px-6 text-sm font-semibold text-gray-600">Auto-Publish</th>
                <th className="text-center py-4 px-6 text-sm font-semibold text-gray-600">Pending</th>
                <th className="text-center py-4 px-6 text-sm font-semibold text-gray-600">Processed</th>
                <th className="text-center py-4 px-6 text-sm font-semibold text-gray-600">Status</th>
                <th className="text-right py-4 px-6 text-sm font-semibold text-gray-600">Actions</th>
              </tr>
            </thead>
            <tbody>
              {channels.length > 0 ? (
                channels.map((channel) => (
                  <tr key={channel.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-4 px-6">
                      <div className="flex items-center gap-3">
                        <div className="bg-red-100 p-2 rounded-full">
                          <Youtube className="text-red-600" size={20} />
                        </div>
                        <div>
                          <p className="font-medium text-gray-900">{channel.name}</p>
                          <a 
                            href={channel.channel_url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="text-xs text-gray-500 hover:text-purple-600 truncate block max-w-[200px]"
                          >
                            {channel.channel_url}
                          </a>
                        </div>
                      </div>
                    </td>
                    <td className="py-4 px-6">
                      <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded text-xs font-medium">
                        {channel.category_name || 'None'}
                      </span>
                    </td>
                    <td className="py-4 px-6 text-center">
                      {channel.auto_publish ? (
                        <span className="text-green-600"><Check size={20} /></span>
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </td>
                    <td className="py-4 px-6 text-center">
                      {channel.pending_count > 0 ? (
                        <span className="px-2 py-1 bg-orange-100 text-orange-700 rounded-full text-sm font-bold">
                          {channel.pending_count}
                        </span>
                      ) : (
                        <span className="text-gray-400">0</span>
                      )}
                    </td>
                    <td className="py-4 px-6 text-center text-gray-600">
                      {channel.videos_processed}
                    </td>
                    <td className="py-4 px-6 text-center">
                      <button
                        onClick={() => handleToggleEnabled(channel)}
                        className={`px-3 py-1 rounded-full text-xs font-medium ${
                          channel.is_enabled
                            ? 'bg-green-100 text-green-700'
                            : 'bg-gray-100 text-gray-500'
                        }`}
                      >
                        {channel.is_enabled ? 'Active' : 'Paused'}
                      </button>
                    </td>
                    <td className="py-4 px-6 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => openEditModal(channel)}
                          className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg"
                          title="Edit"
                        >
                          <Edit2 size={18} />
                        </button>
                        <button
                          onClick={() => handleDelete(channel.id)}
                          className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
                          title="Delete"
                        >
                          <Trash2 size={18} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-gray-500">
                    <Youtube className="mx-auto mb-4 text-gray-300" size={48} />
                    <p>No YouTube channels added yet</p>
                    <button
                      onClick={() => setShowAddModal(true)}
                      className="mt-4 text-purple-600 hover:text-purple-800 font-medium"
                    >
                      Add your first channel
                    </button>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add/Edit Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full">
            <div className="p-6 border-b border-gray-200 flex items-center justify-between">
              <h2 className="text-xl font-bold text-gray-900">
                {editingChannel ? 'Edit Channel' : 'Add YouTube Channel'}
              </h2>
              <button
                onClick={() => {
                  setShowAddModal(false);
                  setEditingChannel(null);
                }}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                <X size={20} />
              </button>
            </div>
            
            <form onSubmit={handleSaveChannel} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Channel Name
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 text-gray-900 placeholder-gray-500"
                  placeholder="e.g., Doug DeMuro"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  YouTube Channel URL
                </label>
                <input
                  type="url"
                  value={formData.channel_url}
                  onChange={(e) => setFormData({ ...formData, channel_url: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 text-gray-900 placeholder-gray-500"
                  placeholder="https://www.youtube.com/@ChannelName"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Default Category
                </label>
                <select
                  value={formData.default_category}
                  onChange={(e) => setFormData({ ...formData, default_category: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 text-gray-900 bg-white"
                >
                  <option value="">Select category...</option>
                  {categories.map((cat) => (
                    <option key={cat.id} value={cat.id}>{cat.name}</option>
                  ))}
                </select>
              </div>

              <div className="flex items-center gap-6 pt-2">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.is_enabled}
                    onChange={(e) => setFormData({ ...formData, is_enabled: e.target.checked })}
                    className="w-5 h-5 text-purple-600 rounded"
                  />
                  <span className="text-sm text-gray-700">Enable monitoring</span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.auto_publish}
                    onChange={(e) => setFormData({ ...formData, auto_publish: e.target.checked })}
                    className="w-5 h-5 text-green-600 rounded"
                  />
                  <span className="text-sm text-gray-700">Auto-publish (skip review)</span>
                </label>
              </div>

              {formData.auto_publish && (
                <div className="bg-yellow-50 p-3 rounded-lg text-yellow-800 text-sm">
                  ⚠️ Articles will be published automatically without review
                </div>
              )}

              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => {
                    setShowAddModal(false);
                    setEditingChannel(null);
                  }}
                  className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
                >
                  {saving ? <Loader2 className="animate-spin" size={18} /> : <Check size={18} />}
                  {editingChannel ? 'Update' : 'Add Channel'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
