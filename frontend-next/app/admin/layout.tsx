'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Sidebar from '@/components/admin/Sidebar';
import AdminHeader from '@/components/admin/AdminHeader';
import { IdleWarningModal } from '@/components/admin/IdleWarningModal';
import { useIdleTimeout } from '@/lib/useIdleTimeout';
import { useProactiveTokenRefresh } from '@/lib/useProactiveTokenRefresh';
import { isAdmin, isAuthenticated, verifyAndRefreshSession } from '@/lib/auth';
import toast from 'react-hot-toast';
import api from '@/lib/api';

// Block search engine indexing on all admin pages
const NOINDEX_META = typeof document !== 'undefined' ? (() => {
  const existing = document.querySelector('meta[name="robots"]');
  if (!existing) {
    const meta = document.createElement('meta');
    meta.name = 'robots';
    meta.content = 'noindex, nofollow';
    document.head.appendChild(meta);
  }
  return true;
})() : false;

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const router = useRouter();
  const [authorized, setAuthorized] = useState(false);
  const [showIdleWarning, setShowIdleWarning] = useState(false);

  useEffect(() => {
    // Load sidebar state from localStorage
    const savedState = localStorage.getItem('adminSidebarCollapsed');
    if (savedState === 'true') {
      setIsCollapsed(true);
    }

    // Check authentication + verify token liveness
    const checkAuth = async () => {
      if (!isAuthenticated()) {
        router.push('/login');
        return;
      }

      if (!isAdmin()) {
        toast.error('Access Denied: Admin privileges required');
        router.push('/');
        return;
      }

      // Verify token is live; refresh if expired; handle network errors gracefully
      const sessionOk = await verifyAndRefreshSession();
      if (!sessionOk) {
        toast.error('Session expired. Please log in again.');
        router.push('/login');
        return;
      }

      setAuthorized(true);
    };

    checkAuth();
  }, [router]);

  // ── Idle logout logic ─────────────────────────────────────────────
  const handleLogout = useCallback(async () => {
    setShowIdleWarning(false);
    try {
      const refreshToken = document.cookie
        .split('; ')
        .find(row => row.startsWith('refresh_token='))
        ?.split('=')[1];
      if (refreshToken) {
        await api.post('/token/blacklist/', { refresh: refreshToken });
      }
    } catch { /* ignore — still clear state */ }

    document.cookie = 'access_token=; path=/; max-age=0';
    document.cookie = 'refresh_token=; path=/; max-age=0';
    localStorage.removeItem('user');
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');  // ← was missing before
    localStorage.removeItem('admin_last_active');

    toast('🔒 Session expired due to inactivity', { icon: '⏰' });
    router.push('/login');
  }, [router]);

  const handleWarn = useCallback(() => {
    setShowIdleWarning(true);
  }, []);

  const { extendSession } = useIdleTimeout({
    enabled: authorized,
    onWarn: handleWarn,
    onLogout: handleLogout,
  });

  // Proactive token refresh: silently renew when < 10 min left
  useProactiveTokenRefresh(authorized);

  const handleStayLoggedIn = useCallback(() => {
    setShowIdleWarning(false);
    extendSession();
  }, [extendSession]);
  // ─────────────────────────────────────────────────────────────────

  const toggleSidebar = () => {
    const newState = !isCollapsed;
    setIsCollapsed(newState);
    localStorage.setItem('adminSidebarCollapsed', String(newState));
  };

  if (!authorized) {
    return (
      <div className="flex min-h-screen bg-gray-100 items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-gray-100">
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        isCollapsed={isCollapsed}
        onToggle={toggleSidebar}
      />
      <div className="flex-1 flex flex-col min-w-0">
        <AdminHeader onMenuClick={() => setSidebarOpen(true)} />
        <main className="flex-1 p-3 sm:p-4 md:p-6 transition-all duration-300">
          {children}
        </main>
      </div>

      {/* Idle session warning modal */}
      <IdleWarningModal
        visible={showIdleWarning}
        onStay={handleStayLoggedIn}
        onLogout={handleLogout}
        countdownSeconds={120}
      />
    </div>
  );
}
