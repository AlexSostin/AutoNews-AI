'use client';

import { useState, useEffect } from 'react';
import {
    Bell,
    MessageSquare,
    UserPlus,
    FileText,
    Youtube,
    AlertTriangle,
    Info,
    Check,
    CheckCheck,
    X,
    Loader2,
    Trash2,
    ExternalLink
} from 'lucide-react';
import { getApiUrl } from '@/lib/api';
import { authenticatedFetch } from '@/lib/authenticatedFetch';

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

const notificationIcons: Record<string, React.ReactNode> = {
    comment: <MessageSquare size={20} className="text-blue-500" />,
    subscriber: <UserPlus size={20} className="text-green-500" />,
    article: <FileText size={20} className="text-purple-500" />,
    video_pending: <Youtube size={20} className="text-orange-500" />,
    video_error: <AlertTriangle size={20} className="text-red-500" />,
    ai_error: <AlertTriangle size={20} className="text-red-500" />,
    system: <AlertTriangle size={20} className="text-amber-500" />,
    info: <Info size={20} className="text-gray-500" />,
};

export default function NotificationsPage() {
    const [notifications, setNotifications] = useState<Notification[]>([]);
    const [loading, setLoading] = useState(true);
    const [markingAll, setMarkingAll] = useState(false);
    const [filter, setFilter] = useState<'all' | 'unread'>('all');
    const [selectedType, setSelectedType] = useState<string>('all');

    const fetchNotifications = async () => {
        try {
            setLoading(true);
            const response = await authenticatedFetch('/notifications/?limit=100');

            if (response.ok) {
                const data = await response.json();
                setNotifications(data.notifications || []);
            }
        } catch (error) {
            console.error('Failed to fetch notifications:', error);
        } finally {
            setLoading(false);
        }
    };

    const markAsRead = async (id: number) => {
        try {
            await authenticatedFetch(`/notifications/${id}/mark_read/`, {
                method: 'POST',
            });

            setNotifications(prev =>
                prev.map(n => n.id === id ? { ...n, is_read: true } : n)
            );
        } catch (error) {
            console.error('Failed to mark as read:', error);
        }
    };

    const markAllAsRead = async () => {
        try {
            setMarkingAll(true);
            await authenticatedFetch('/notifications/mark_all_read/', {
                method: 'POST',
            });

            setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
        } catch (error) {
            console.error('Failed to mark all as read:', error);
        } finally {
            setMarkingAll(false);
        }
    };

    const deleteNotification = async (id: number) => {
        try {
            const response = await authenticatedFetch(`/notifications/${id}/`, {
                method: 'DELETE',
            });

            if (response.ok) {
                setNotifications(prev => prev.filter(n => n.id !== id));
            }
        } catch (error) {
            console.error('Failed to delete notification:', error);
        }
    };

    useEffect(() => {
        fetchNotifications();
    }, []);

    // Get counts for each type
    const typeCounts = notifications.reduce((acc, n) => {
        acc[n.notification_type] = (acc[n.notification_type] || 0) + 1;
        return acc;
    }, {} as Record<string, number>);

    const filteredNotifications = notifications.filter(n => {
        const matchesFilter = filter === 'all' || !n.is_read;
        const matchesType = selectedType === 'all' || n.notification_type === selectedType;
        return matchesFilter && matchesType;
    });

    const unreadCount = notifications.filter(n => !n.is_read).length;

    if (loading && notifications.length === 0) {
        return (
            <div className="flex items-center justify-center min-h-[60vh]">
                <Loader2 className="animate-spin text-indigo-600" size={48} />
            </div>
        );
    }

    const availableTypes = Object.entries(notificationIcons).filter(([type]) => typeCounts[type] > 0);

    return (
        <div className="space-y-6 max-w-5xl mx-auto pb-12 px-4 sm:px-0">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                    <h1 className="text-2xl sm:text-3xl font-black text-gray-950">Notifications</h1>
                    <p className="text-gray-500 mt-1">Manage your system updates and alerts</p>
                </div>

                <div className="flex gap-2">
                    {unreadCount > 0 && (
                        <button
                            onClick={markAllAsRead}
                            disabled={markingAll}
                            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50 shadow-md shadow-indigo-200"
                        >
                            {markingAll ? <Loader2 className="animate-spin" size={18} /> : <CheckCheck size={18} />}
                            Mark all as read
                        </button>
                    )}
                    <button
                        onClick={fetchNotifications}
                        className="p-2 bg-white border border-gray-200 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                        title="Refresh"
                    >
                        <Bell size={20} />
                    </button>
                </div>
            </div>

            {/* Status Filters */}
            <div className="flex gap-2 border-b border-gray-200">
                <button
                    onClick={() => setFilter('all')}
                    className={`px-4 py-2 font-bold text-sm transition-all relative ${filter === 'all' ? 'text-indigo-600' : 'text-gray-500 hover:text-gray-700'}`}
                >
                    All Status
                    {filter === 'all' && <div className="absolute bottom-0 left-0 right-0 h-1 bg-indigo-600 rounded-t-full" />}
                </button>
                <button
                    onClick={() => setFilter('unread')}
                    className={`px-4 py-2 font-bold text-sm transition-all relative flex items-center gap-2 ${filter === 'unread' ? 'text-indigo-600' : 'text-gray-500 hover:text-gray-700'}`}
                >
                    Unread
                    {unreadCount > 0 && (
                        <span className="bg-indigo-100 text-indigo-600 px-1.5 py-0.5 rounded-full text-[10px]">
                            {unreadCount}
                        </span>
                    )}
                    {filter === 'unread' && <div className="absolute bottom-0 left-0 right-0 h-1 bg-indigo-600 rounded-t-full" />}
                </button>
            </div>

            {/* Type Filters */}
            <div className="flex gap-2 pb-2 overflow-x-auto no-scrollbar scroll-smooth">
                <button
                    onClick={() => setSelectedType('all')}
                    className={`flex-shrink-0 px-4 py-2 rounded-xl text-sm font-bold transition-all border ${selectedType === 'all'
                        ? 'bg-gray-900 text-white border-gray-900 shadow-md'
                        : 'bg-white text-gray-600 border-gray-200 hover:border-gray-300'
                        }`}
                >
                    All Types ({notifications.length})
                </button>

                {availableTypes.map(([type, icon]) => (
                    <button
                        key={type}
                        onClick={() => setSelectedType(type)}
                        className={`flex-shrink-0 flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold transition-all border ${selectedType === type
                            ? 'bg-indigo-600 text-white border-indigo-600 shadow-md'
                            : 'bg-white text-gray-600 border-gray-200 hover:border-gray-300'
                            }`}
                    >
                        {icon}
                        <span className="capitalize">{type.replace('_', ' ')}</span>
                        <span className={`px-1.5 py-0.5 rounded-md text-[10px] ${selectedType === type ? 'bg-white/20 text-white' : 'bg-gray-100 text-gray-500'
                            }`}>
                            {typeCounts[type]}
                        </span>
                    </button>
                ))}
            </div>

            {/* List */}
            <div className="space-y-4">
                {filteredNotifications.length === 0 ? (
                    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-12 text-center">
                        <div className="bg-gray-50 w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-4">
                            <Bell size={40} className="text-gray-300" />
                        </div>
                        <h3 className="text-xl font-bold text-gray-900">No notifications found</h3>
                        <p className="text-gray-500 mt-2 max-w-xs mx-auto">
                            {filter === 'unread'
                                ? "You've read all your notifications! Great job."
                                : "When important events happen, they'll show up here."}
                        </p>
                    </div>
                ) : (
                    filteredNotifications.map((notification) => (
                        <div
                            key={notification.id}
                            className={`group relative bg-white rounded-2xl border transition-all hover:shadow-lg ${!notification.is_read ? 'border-indigo-100 shadow-sm' : 'border-gray-100'
                                } p-4 sm:p-5`}
                        >
                            {!notification.is_read && (
                                <div className="absolute left-0 top-6 bottom-6 w-1 bg-indigo-500 rounded-r-full" />
                            )}

                            <div className="flex items-start gap-4">
                                <div className={`flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center ${!notification.is_read ? 'bg-indigo-50 text-indigo-600' : 'bg-gray-50 text-gray-400'
                                    }`}>
                                    {notificationIcons[notification.notification_type] || <Info size={20} />}
                                </div>

                                <div className="flex-1 min-w-0">
                                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 mb-1">
                                        <h2 className={`text-base font-bold truncate ${!notification.is_read ? 'text-gray-900' : 'text-gray-600'}`}>
                                            {notification.title}
                                        </h2>
                                        <span className="text-xs text-gray-400 whitespace-nowrap">
                                            {notification.time_ago}
                                        </span>
                                    </div>

                                    <p className={`text-sm leading-relaxed mb-3 ${!notification.is_read ? 'text-gray-700' : 'text-gray-500'}`}>
                                        {notification.message}
                                    </p>

                                    <div className="flex flex-wrap items-center gap-3">
                                        {notification.link && (
                                            <a
                                                href={notification.link}
                                                className="text-xs font-bold text-indigo-600 hover:text-indigo-800 flex items-center gap-1 transition-colors"
                                            >
                                                <ExternalLink size={14} />
                                                View Details
                                            </a>
                                        )}

                                        {!notification.is_read && (
                                            <button
                                                onClick={() => markAsRead(notification.id)}
                                                className="text-xs font-bold text-gray-500 hover:text-indigo-600 flex items-center gap-1 transition-colors"
                                            >
                                                <Check size={14} />
                                                Mark as read
                                            </button>
                                        )}

                                        <button
                                            onClick={() => deleteNotification(notification.id)}
                                            className="text-xs font-bold text-gray-400 hover:text-red-600 flex items-center gap-1 transition-colors ml-auto opacity-0 group-hover:opacity-100 sm:ml-0"
                                        >
                                            <Trash2 size={14} />
                                            Delete
                                        </button>
                                    </div>
                                </div>

                                <div className="hidden sm:block">
                                    <span className={`text-[10px] font-black uppercase tracking-wider px-2 py-1 rounded-full ${notification.priority === 'high' ? 'bg-red-100 text-red-600' :
                                        notification.priority === 'normal' ? 'bg-blue-100 text-blue-600' :
                                            'bg-gray-100 text-gray-600'
                                        }`}>
                                        {notification.priority}
                                    </span>
                                </div>
                            </div>
                        </div>
                    ))
                )}
            </div>

            {notifications.length >= 100 && (
                <div className="flex justify-center pt-4">
                    <p className="text-sm text-gray-500 italic">Showing your latest 100 notifications</p>
                </div>
            )}
        </div>
    );
}
