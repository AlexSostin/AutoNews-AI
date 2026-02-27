'use client';

import { useState, useEffect, useRef } from 'react';
import {
  Bell, User, Menu, MessageSquare, UserPlus, FileText, Youtube,
  AlertTriangle, Info, Check, CheckCheck, X, Loader2, Activity,
  Server, Zap, Globe
} from 'lucide-react';
import api, { getApiUrl } from '@/lib/api';

interface Notification {
  id: number;
  notification_type: string;
  type_display: string;
  title: string;
  message: string;
  link: string;
  priority: string;
  is_read: boolean;
  created_at: string;
  time_ago: string;
}

interface HealthSummary {
  api_errors: { unresolved: number; last_24h: number };
  scheduler_errors: { unresolved: number; last_24h: number };
  frontend_errors: { unresolved: number; last_24h: number };
  total_unresolved: number;
  overall_status: string;
}

interface AdminHeaderProps {
  onMenuClick: () => void;
}

const notificationIcons: Record<string, React.ReactNode> = {
  comment: <MessageSquare size={16} className="text-blue-500" />,
  subscriber: <UserPlus size={16} className="text-green-500" />,
  article: <FileText size={16} className="text-purple-500" />,
  video_pending: <Youtube size={16} className="text-orange-500" />,
  video_error: <AlertTriangle size={16} className="text-red-500" />,
  ai_error: <AlertTriangle size={16} className="text-red-500" />,
  system: <AlertTriangle size={16} className="text-amber-500" />,
  info: <Info size={16} className="text-gray-500" />,
};

const priorityColors: Record<string, string> = {
  high: 'border-l-red-500',
  normal: 'border-l-blue-500',
  low: 'border-l-gray-300',
};

export default function AdminHeader({ onMenuClick }: AdminHeaderProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [healthData, setHealthData] = useState<HealthSummary | null>(null);
  const [activeTab, setActiveTab] = useState<'notifications' | 'health'>('notifications');
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Fetch notifications
  const fetchNotifications = async () => {
    try {
      const response = await api.get('/notifications/?limit=10');
      setNotifications(response.data.notifications || []);
      setUnreadCount(response.data.unread_count || 0);
    } catch (error) {
      // Silently fail
    }
  };

  // Fetch health errors
  const fetchHealth = async () => {
    try {
      const response = await api.get('/health/errors-summary/');
      setHealthData(response.data);
    } catch { /* silent */ }
  };

  // Mark single notification as read
  const markAsRead = async (id: number) => {
    try {
      await api.post(`/notifications/${id}/mark_read/`);
      setNotifications(prev =>
        prev.map(n => n.id === id ? { ...n, is_read: true } : n)
      );
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (error) {
      console.error('Failed to mark as read:', error);
    }
  };

  // Mark all as read
  const markAllAsRead = async () => {
    try {
      setLoading(true);
      await api.post('/notifications/mark_all_read/');
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch (error) {
      console.error('Failed to mark all as read:', error);
    } finally {
      setLoading(false);
    }
  };

  // Fetch on mount and poll every 30 seconds
  useEffect(() => {
    fetchNotifications();
    fetchHealth();
    const interval = setInterval(() => {
      fetchNotifications();
      fetchHealth();
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Handle notification click
  const handleNotificationClick = (notification: Notification) => {
    if (!notification.is_read) {
      markAsRead(notification.id);
    }
    if (notification.link) {
      window.location.href = notification.link;
    }
    setIsOpen(false);
  };

  // Total badge count: notifications + errors
  const totalBadge = unreadCount + (healthData?.total_unresolved || 0);

  // Health error items for the health tab
  const healthItems = [];
  if (healthData) {
    if (healthData.api_errors.unresolved > 0) {
      healthItems.push({
        icon: <Server size={16} className="text-blue-500" />,
        label: 'API Errors',
        count: healthData.api_errors.unresolved,
        last24h: healthData.api_errors.last_24h,
        color: 'border-l-red-500',
      });
    }
    if (healthData.scheduler_errors.unresolved > 0) {
      healthItems.push({
        icon: <Zap size={16} className="text-purple-500" />,
        label: 'Scheduler Errors',
        count: healthData.scheduler_errors.unresolved,
        last24h: healthData.scheduler_errors.last_24h,
        color: 'border-l-orange-500',
      });
    }
    if (healthData.frontend_errors.unresolved > 0) {
      healthItems.push({
        icon: <Globe size={16} className="text-cyan-500" />,
        label: 'Frontend Errors',
        count: healthData.frontend_errors.unresolved,
        last24h: healthData.frontend_errors.last_24h,
        color: 'border-l-amber-500',
      });
    }
  }

  return (
    <header className="bg-white shadow-sm border-b border-gray-200 py-3 sm:py-4">
      <div className="max-w-6xl mx-auto px-3 sm:px-4 md:px-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {/* Mobile Menu Button */}
          <button
            onClick={onMenuClick}
            className="lg:hidden p-2 hover:bg-gray-100 rounded-lg transition-colors text-gray-700"
          >
            <Menu size={24} />
          </button>

          <h1 className="text-lg sm:text-xl md:text-2xl font-black text-gray-950">
            Admin Dashboard
          </h1>
        </div>

        <div className="flex items-center gap-2 sm:gap-4">
          {/* Notifications + Health Bell */}
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => {
                setIsOpen(!isOpen);
                if (!isOpen) {
                  fetchNotifications();
                  fetchHealth();
                }
              }}
              className="p-2 hover:bg-gray-100 rounded-full transition-colors relative"
              title="Notifications & System Health"
            >
              <Bell size={18} className="sm:w-5 sm:h-5 text-gray-700" />
              {totalBadge > 0 && (
                <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs font-bold rounded-full min-w-[18px] h-[18px] flex items-center justify-center px-1">
                  {totalBadge > 99 ? '99+' : totalBadge}
                </span>
              )}
            </button>

            {/* Dropdown */}
            {isOpen && (
              <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-white rounded-xl shadow-2xl border border-gray-200 z-50 max-h-[80vh] overflow-hidden">
                {/* Tab Header */}
                <div className="flex border-b border-gray-100 bg-gray-50">
                  <button
                    onClick={() => setActiveTab('notifications')}
                    className={`flex-1 px-4 py-3 text-sm font-semibold transition-colors relative ${activeTab === 'notifications'
                      ? 'text-gray-900 bg-white'
                      : 'text-gray-500 hover:text-gray-700'
                      }`}
                  >
                    <Bell size={14} className="inline mr-1.5 -mt-0.5" />
                    Notifications
                    {unreadCount > 0 && (
                      <span className="ml-1.5 bg-blue-500 text-white text-[10px] font-bold rounded-full min-w-[16px] h-[16px] inline-flex items-center justify-center px-1">
                        {unreadCount}
                      </span>
                    )}
                    {activeTab === 'notifications' && (
                      <span className="absolute bottom-0 left-2 right-2 h-0.5 bg-indigo-600 rounded-full" />
                    )}
                  </button>
                  <button
                    onClick={() => setActiveTab('health')}
                    className={`flex-1 px-4 py-3 text-sm font-semibold transition-colors relative ${activeTab === 'health'
                      ? 'text-gray-900 bg-white'
                      : 'text-gray-500 hover:text-gray-700'
                      }`}
                  >
                    <Activity size={14} className="inline mr-1.5 -mt-0.5" />
                    System Health
                    {(healthData?.total_unresolved || 0) > 0 && (
                      <span className="ml-1.5 bg-red-500 text-white text-[10px] font-bold rounded-full min-w-[16px] h-[16px] inline-flex items-center justify-center px-1">
                        {healthData!.total_unresolved}
                      </span>
                    )}
                    {activeTab === 'health' && (
                      <span className="absolute bottom-0 left-2 right-2 h-0.5 bg-indigo-600 rounded-full" />
                    )}
                  </button>
                </div>

                {/* Tab Content */}
                <div className="overflow-y-auto max-h-[60vh]">
                  {/* ── Notifications Tab ──────────────────────── */}
                  {activeTab === 'notifications' && (
                    <>
                      {/* Mark all read */}
                      {unreadCount > 0 && (
                        <div className="px-4 py-2 border-b border-gray-50 flex justify-end">
                          <button
                            onClick={markAllAsRead}
                            disabled={loading}
                            className="text-xs text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1"
                          >
                            {loading ? <Loader2 size={12} className="animate-spin" /> : <CheckCheck size={14} />}
                            Mark all read
                          </button>
                        </div>
                      )}

                      {notifications.length === 0 ? (
                        <div className="px-4 py-8 text-center text-gray-500">
                          <Bell size={32} className="mx-auto mb-2 text-gray-300" />
                          <p className="font-medium">No notifications yet</p>
                          <p className="text-sm">We&apos;ll notify you about important updates</p>
                        </div>
                      ) : (
                        notifications.map((notification) => (
                          <div
                            key={notification.id}
                            onClick={() => handleNotificationClick(notification)}
                            className={`px-4 py-3 border-b border-gray-50 hover:bg-gray-50 cursor-pointer transition-colors border-l-4 ${priorityColors[notification.priority]} ${!notification.is_read ? 'bg-blue-50/50' : ''
                              }`}
                          >
                            <div className="flex items-start gap-3">
                              <div className="mt-0.5">
                                {notificationIcons[notification.notification_type] || notificationIcons.info}
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center justify-between gap-2">
                                  <p className={`text-sm font-medium truncate ${!notification.is_read ? 'text-gray-900' : 'text-gray-600'}`}>
                                    {notification.title}
                                  </p>
                                  {!notification.is_read && (
                                    <span className="w-2 h-2 bg-blue-500 rounded-full flex-shrink-0" />
                                  )}
                                </div>
                                <p className="text-xs text-gray-500 line-clamp-2 mt-0.5">
                                  {notification.message}
                                </p>
                                <p className="text-xs text-gray-400 mt-1">
                                  {notification.time_ago}
                                </p>
                              </div>
                            </div>
                          </div>
                        ))
                      )}
                    </>
                  )}

                  {/* ── System Health Tab ──────────────────────── */}
                  {activeTab === 'health' && (
                    <>
                      {/* Status Banner */}
                      {healthData && (
                        <div className={`px-4 py-3 border-b border-gray-50 flex items-center gap-2 ${healthData.overall_status === 'healthy' ? 'bg-emerald-50' :
                          healthData.overall_status === 'degraded' ? 'bg-amber-50' : 'bg-red-50'
                          }`}>
                          {healthData.overall_status === 'healthy' && <Check size={16} className="text-emerald-600" />}
                          {healthData.overall_status === 'degraded' && <AlertTriangle size={16} className="text-amber-600" />}
                          {healthData.overall_status === 'critical' && <AlertTriangle size={16} className="text-red-600" />}
                          <span className={`text-sm font-semibold capitalize ${healthData.overall_status === 'healthy' ? 'text-emerald-700' :
                            healthData.overall_status === 'degraded' ? 'text-amber-700' : 'text-red-700'
                            }`}>
                            System {healthData.overall_status}
                          </span>
                          <span className="text-xs text-gray-500 ml-auto">
                            {healthData.total_unresolved} unresolved
                          </span>
                        </div>
                      )}

                      {healthItems.length === 0 ? (
                        <div className="px-4 py-8 text-center text-gray-500">
                          <Check size={32} className="mx-auto mb-2 text-emerald-400" />
                          <p className="font-medium">All systems healthy</p>
                          <p className="text-sm">No unresolved errors detected</p>
                        </div>
                      ) : (
                        healthItems.map((item, i) => (
                          <a
                            key={i}
                            href="/admin/health"
                            className={`block px-4 py-3 border-b border-gray-50 hover:bg-gray-50 cursor-pointer transition-colors border-l-4 ${item.color}`}
                          >
                            <div className="flex items-center gap-3">
                              <div className="mt-0.5">{item.icon}</div>
                              <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium text-gray-900">{item.label}</p>
                                <p className="text-xs text-gray-500 mt-0.5">
                                  {item.last24h} in last 24h
                                </p>
                              </div>
                              <span className="bg-red-100 text-red-700 text-xs font-bold px-2 py-0.5 rounded-full">
                                {item.count}
                              </span>
                            </div>
                          </a>
                        ))
                      )}
                    </>
                  )}
                </div>

                {/* Footer */}
                <div className="px-4 py-2 border-t border-gray-100 bg-gray-50">
                  <a
                    href={activeTab === 'notifications' ? '/admin/notifications' : '/admin/health'}
                    className="text-sm text-blue-600 hover:text-blue-800 font-medium block text-center"
                  >
                    {activeTab === 'notifications' ? 'View all notifications' : 'Open System Health Monitor'}
                  </a>
                </div>
              </div>
            )}
          </div>

          <div className="hidden sm:flex items-center gap-2 px-3 py-2 bg-gray-100 rounded-full">
            <User size={20} className="text-gray-800" />
            <span className="font-bold text-gray-900">Admin</span>
          </div>

          {/* Mobile User Icon */}
          <div className="sm:hidden p-2 bg-gray-100 rounded-full">
            <User size={18} className="text-gray-800" />
          </div>
        </div>
      </div>
    </header>
  );
}
