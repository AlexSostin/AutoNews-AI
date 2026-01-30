'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Sidebar from '@/components/admin/Sidebar';
import AdminHeader from '@/components/admin/AdminHeader';
import { isAdmin, isAuthenticated } from '@/lib/auth'; // Ensure these are exported from lib/auth
import toast from 'react-hot-toast';

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const router = useRouter();
  const [authorized, setAuthorized] = useState(false);

  useEffect(() => {
    // Load sidebar state from localStorage
    const savedState = localStorage.getItem('adminSidebarCollapsed');
    if (savedState === 'true') {
      setIsCollapsed(true);
    }

    // Check if user is authenticated and is staff
    const checkAuth = () => {
      if (!isAuthenticated()) {
        router.push('/login');
        return;
      }

      if (!isAdmin()) {
        toast.error('Access Denied: Admin privileges required');
        router.push('/');
        return;
      }

      setAuthorized(true);
    };

    checkAuth();
  }, [router]);

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
    </div>
  );
}
