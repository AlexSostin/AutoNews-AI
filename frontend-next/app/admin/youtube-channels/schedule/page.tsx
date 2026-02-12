'use client';

import { useState, useEffect } from 'react';
import {
  Clock,
  Save,
  Loader2,
  ArrowLeft,
  Play,
  Calendar,
  Zap,
  Check,
  AlertCircle
} from 'lucide-react';
import api, { getApiUrl } from '@/lib/api';
import Link from 'next/link';

interface Schedule {
  id: number;
  is_enabled: boolean;
  frequency: 'once' | 'twice' | 'four' | 'manual';
  scan_time_1: string;
  scan_time_2: string | null;
  scan_time_3: string | null;
  scan_time_4: string | null;
  last_scan: string | null;
  total_scans: number;
  total_articles_generated: number;
}

export default function SchedulePage() {
  const [schedule, setSchedule] = useState<Schedule | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    fetchSchedule();
  }, []);

  const fetchSchedule = async () => {
    try {
      const response = await api.get('/auto-publish-schedule/');

      if (response.status === 200) {
        const data = response.data;
        // Get first schedule or create default
        if (data.results && data.results.length > 0) {
          setSchedule(data.results[0]);
        } else if (Array.isArray(data) && data.length > 0) {
          setSchedule(data[0]);
        } else if (data && typeof data === 'object' && data.id) {
          // Handle single object response
          setSchedule(data);
        } else {
          // Create default schedule
          const createResponse = await api.post('/auto-publish-schedule/', {
            is_enabled: false,
            frequency: 'twice',
            scan_time_1: '08:00:00',
            scan_time_2: '18:00:00'
          });
          if (createResponse.status === 201 || createResponse.status === 200) {
            setSchedule(createResponse.data);
          }
        }
      }
    } catch (error) {
      console.error('Failed to fetch schedule:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!schedule) return;

    setSaving(true);
    setMessage(null);

    try {
      const response = await api.patch(`/auto-publish-schedule/${schedule.id}/`, {
        is_enabled: schedule.is_enabled,
        frequency: schedule.frequency,
        scan_time_1: schedule.scan_time_1,
        scan_time_2: schedule.scan_time_2,
        scan_time_3: schedule.scan_time_3,
        scan_time_4: schedule.scan_time_4
      });

      if (response.status === 200) {
        setMessage({ type: 'success', text: 'Schedule saved successfully!' });
      } else {
        setMessage({ type: 'error', text: 'Failed to save schedule' });
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'An error occurred' });
    } finally {
      setSaving(false);
    }
  };

  const handleTriggerScan = async () => {
    if (!schedule) return;

    setScanning(true);
    setMessage(null);

    try {
      const response = await api.post(`/auto-publish-schedule/${schedule.id}/trigger_scan/`);

      if (response.status === 200) {
        const data = response.data;
        setMessage({
          type: 'success',
          text: data.message || 'Scan triggered successfully! New articles will appear in the pending queue soon.'
        });
        fetchSchedule(); // Refresh stats
      } else {
        setMessage({ type: 'error', text: 'Failed to trigger scan' });
      }
    } catch (error: any) {
      setMessage({ type: 'error', text: error.response?.data?.error || 'An error occurred' });
    } finally {
      setScanning(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="animate-spin text-purple-600" size={48} />
      </div>
    );
  }

  const frequencyLabels = {
    manual: 'Manual only',
    once: 'Once per day',
    twice: 'Twice per day',
    four: 'Four times per day'
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex items-center gap-4">
        <Link
          href="/admin/youtube-channels"
          className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors font-medium"
        >
          <ArrowLeft size={20} />
          Back to Channels
        </Link>
        <div>
          <h1 className="text-2xl sm:text-3xl font-black text-gray-950">Scan Schedule</h1>
          <p className="text-gray-500 text-sm">Configure automatic YouTube channel scanning</p>
        </div>
      </div>

      {message && (
        <div className={`p-4 rounded-lg ${message.type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'
          }`}>
          {message.text}
        </div>
      )}

      {/* Stats */}
      {schedule && (
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-purple-50 rounded-xl p-4 border border-purple-200">
            <p className="text-3xl font-black text-purple-600">{schedule.total_scans}</p>
            <p className="text-purple-700 text-sm">Total Scans</p>
          </div>
          <div className="bg-green-50 rounded-xl p-4 border border-green-200">
            <p className="text-3xl font-black text-green-600">{schedule.total_articles_generated}</p>
            <p className="text-green-700 text-sm">Articles Generated</p>
          </div>
        </div>
      )}

      {/* Settings Card */}
      {schedule && (
        <div className="bg-white rounded-xl shadow-md p-6 space-y-6">
          {/* Enable Toggle */}
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-bold text-gray-900">Auto-Scan Enabled</h3>
              <p className="text-sm text-gray-500">Automatically scan channels on schedule</p>
            </div>
            <button
              onClick={() => setSchedule({ ...schedule, is_enabled: !schedule.is_enabled })}
              className={`relative w-14 h-8 rounded-full transition-colors ${schedule.is_enabled ? 'bg-purple-600' : 'bg-gray-300'
                }`}
            >
              <span className={`absolute top-1 left-1 w-6 h-6 bg-white rounded-full shadow transition-transform ${schedule.is_enabled ? 'translate-x-6' : ''
                }`} />
            </button>
          </div>

          {/* Frequency */}
          <div>
            <label className="block font-bold text-gray-900 mb-2">
              <Calendar size={16} className="inline mr-2" />
              Scan Frequency
            </label>
            <select
              value={schedule.frequency}
              onChange={(e) => setSchedule({ ...schedule, frequency: e.target.value as Schedule['frequency'] })}
              className="w-full border rounded-lg px-4 py-3 focus:ring-2 focus:ring-purple-500 focus:border-transparent text-gray-900"
            >
              <option value="manual">Manual only</option>
              <option value="once">Once per day (1 time)</option>
              <option value="twice">Twice per day (2 times)</option>
              <option value="four">Four times per day</option>
            </select>
          </div>

          {/* Time Inputs */}
          {schedule.frequency !== 'manual' && (
            <div className="space-y-4">
              <label className="block font-bold text-gray-900">
                <Clock size={16} className="inline mr-2" />
                Scan Times
              </label>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-gray-500 mb-1">Time 1</label>
                  <input
                    type="time"
                    value={schedule.scan_time_1?.slice(0, 5) || '08:00'}
                    onChange={(e) => setSchedule({ ...schedule, scan_time_1: e.target.value + ':00' })}
                    className="w-full border rounded-lg px-4 py-3 focus:ring-2 focus:ring-purple-500 focus:border-transparent text-gray-900"
                  />
                </div>

                {(schedule.frequency === 'twice' || schedule.frequency === 'four') && (
                  <div>
                    <label className="block text-sm text-gray-500 mb-1">Time 2</label>
                    <input
                      type="time"
                      value={schedule.scan_time_2?.slice(0, 5) || '18:00'}
                      onChange={(e) => setSchedule({ ...schedule, scan_time_2: e.target.value + ':00' })}
                      className="w-full border rounded-lg px-4 py-3 focus:ring-2 focus:ring-purple-500 focus:border-transparent text-gray-900"
                    />
                  </div>
                )}

                {schedule.frequency === 'four' && (
                  <>
                    <div>
                      <label className="block text-sm text-gray-500 mb-1">Time 3</label>
                      <input
                        type="time"
                        value={schedule.scan_time_3?.slice(0, 5) || '12:00'}
                        onChange={(e) => setSchedule({ ...schedule, scan_time_3: e.target.value + ':00' })}
                        className="w-full border rounded-lg px-4 py-3 focus:ring-2 focus:ring-purple-500 focus:border-transparent text-gray-900"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-gray-500 mb-1">Time 4</label>
                      <input
                        type="time"
                        value={schedule.scan_time_4?.slice(0, 5) || '22:00'}
                        onChange={(e) => setSchedule({ ...schedule, scan_time_4: e.target.value + ':00' })}
                        className="w-full border rounded-lg px-4 py-3 focus:ring-2 focus:ring-purple-500 focus:border-transparent text-gray-900"
                      />
                    </div>
                  </>
                )}
              </div>
            </div>
          )}

          {/* Last Scan Info */}
          {schedule.last_scan && (
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-sm text-gray-500">
                Last scan: {new Date(schedule.last_scan).toLocaleString()}
              </p>
            </div>
          )}

          {/* Actions */}
          <div className="flex flex-col sm:flex-row gap-3 pt-4 border-t">
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center justify-center gap-2 px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 font-bold"
            >
              {saving ? <Loader2 className="animate-spin" size={20} /> : <Save size={20} />}
              Save Schedule
            </button>

            <button
              onClick={handleTriggerScan}
              disabled={scanning}
              className="flex items-center justify-center gap-2 px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 font-bold"
            >
              {scanning ? <Loader2 className="animate-spin" size={20} /> : <Zap size={20} />}
              Scan Now
            </button>
          </div>
        </div>
      )}

      {/* Info */}
      <div className="bg-blue-50 rounded-xl p-6 border border-blue-200">
        <h3 className="font-bold text-blue-900 mb-2">How it works</h3>
        <ul className="space-y-2 text-sm text-blue-800">
          <li>• <strong>Manual only:</strong> You trigger scans manually from the YouTube Channels page</li>
          <li>• <strong>Once per day:</strong> System scans all enabled channels at the specified time</li>
          <li>• <strong>Twice per day:</strong> Morning and evening scans at your chosen times</li>
          <li>• <strong>Four times:</strong> Maximum coverage for breaking news channels</li>
          <li>• Articles from channels with <strong>Auto-Publish</strong> enabled are published immediately</li>
          <li>• Articles from other channels go to the <strong>Pending</strong> queue for your review</li>
        </ul>
      </div>
    </div>
  );
}
