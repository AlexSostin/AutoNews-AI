'use client';

import { useState, useEffect, useRef } from 'react';
import { Bell, User, Menu, MessageSquare, UserPlus, FileText, Youtube, AlertTriangle, Info, Check, CheckCheck, X, Loader2 } from 'lucide-react';
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
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Fetch notifications
  const fetchNotifications = async () => {
    try {
      const response = await api.get('/notifications/?limit=10');
      setNotifications(response.data.notifications || []);
      setUnreadCount(response.data.unread_count || 0);
    } catch (error) {
      // Silently fail - don't spam console with auth errors
      // console.error('Failed to fetch notifications:', error);
    }
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
    const interval = setInterval(fetchNotifications, 30000);
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
          {/* Notifications */}
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => {
                setIsOpen(!isOpen);
                if (!isOpen) fetchNotifications();
              }}
              className="p-2 hover:bg-gray-100 rounded-full transition-colors relative"
              title="Notifications"
            >
              <Bell size={18} className="sm:w-5 sm:h-5 text-gray-700" />
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs font-bold rounded-full min-w-[18px] h-[18px] flex items-center justify-center px-1">
                  {unreadCount > 99 ? '99+' : unreadCount}
                </span>
              )}
            </button>

            {/* Notifications Dropdown */}
            {isOpen && (
              <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-white rounded-xl shadow-2xl border border-gray-200 z-50 max-h-[80vh] overflow-hidden">
                {/* Header */}
                <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between bg-gray-50">
                  <h3 className="font-bold text-gray-900">Notifications</h3>
                  <div className="flex items-center gap-2">
                    {unreadCount > 0 && (
                      <button
                        onClick={markAllAsRead}
                        disabled={loading}
                        className="text-xs text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1"
                      >
                        {loading ? <Loader2 size={12} className="animate-spin" /> : <CheckCheck size={14} />}
                        Mark all read
                      </button>
                    )}
                    <button
                      onClick={() => setIsOpen(false)}
                      className="p-1 hover:bg-gray-200 rounded"
                    >
                      <X size={16} className="text-gray-500" />
                    </button>
                  </div>
                </div>

                {/* Notifications List */}
                <div className="overflow-y-auto max-h-[60vh]">
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
                </div>

                {/* Footer */}
                {notifications.length > 0 && (
                  <div className="px-4 py-2 border-t border-gray-100 bg-gray-50">
                    <a
                      href="/admin/notifications"
                      className="text-sm text-blue-600 hover:text-blue-800 font-medium block text-center"
                    >
                      View all notifications
                    </a>
                  </div>
                )}
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
