'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  FileText,
  Folder,
  Tag,
  MessageSquare,
  LogOut,
  Home,
  Settings,
  X,
  FileStack,
  BarChart3,
  UserCog,
  Mail,
  Youtube,
  Rss,
  ChevronLeft,
  ChevronRight,
  Menu,
  Bell
} from 'lucide-react';
import { logout } from '@/lib/auth';

const menuItems = [
  { href: '/admin', icon: LayoutDashboard, label: 'Dashboard' },
  { href: '/admin/notifications', icon: Bell, label: 'Notifications' },
  { href: '/admin/analytics', icon: BarChart3, label: 'Analytics' },
  { href: '/admin/articles', icon: FileText, label: 'Articles' },
  { href: '/admin/categories', icon: Folder, label: 'Categories' },
  { href: '/admin/tags', icon: Tag, label: 'Tags' },
  { href: '/admin/comments', icon: MessageSquare, label: 'Comments' },
  { href: '/admin/subscribers', icon: Mail, label: 'Subscribers' },
  { href: '/admin/youtube-channels', icon: Youtube, label: 'YouTube Channels' },
  { href: '/admin/rss-feeds', icon: Rss, label: 'RSS Feeds' },
  { href: '/admin/rss-pending', icon: FileStack, label: 'RSS Pending' },
  { href: '/admin/pages', icon: FileStack, label: 'Pages' },
  { href: '/admin/settings', icon: Settings, label: 'Site Settings' },
  { href: '/admin/account', icon: UserCog, label: 'Account Settings' },
];

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  isCollapsed: boolean;
  onToggle: () => void;
}

export default function Sidebar({ isOpen, onClose, isCollapsed, onToggle }: SidebarProps) {
  const pathname = usePathname();

  const handleLogout = () => {
    logout();
  };

  return (
    <>
      {/* Mobile Overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside className={`
        fixed lg:static inset-y-0 left-0 z-50
        ${isCollapsed ? 'w-20' : 'w-64'} bg-gray-900 text-white min-h-screen flex flex-col
        transform transition-all duration-300 ease-in-out
        ${isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        {/* Header with Close Button (Mobile) & Toggle (Desktop) */}
        <div className={`p-4 sm:p-6 flex items-center ${isCollapsed ? 'justify-center' : 'justify-between'} border-b border-gray-800/50`}>
          {!isCollapsed && (
            <h2 className="text-xl sm:text-2xl font-black bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent truncate">
              FM Admin
            </h2>
          )}

          <div className="flex items-center gap-1">
            {/* Desktop Toggle Button */}
            <button
              onClick={onToggle}
              className="hidden lg:flex p-2 hover:bg-gray-800 rounded-lg transition-colors text-gray-400 hover:text-white"
              title={isCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
            >
              {isCollapsed ? <ChevronRight size={20} /> : <ChevronLeft size={20} />}
            </button>

            {/* Mobile Close Button */}
            <button
              onClick={onClose}
              className="lg:hidden p-2 hover:bg-gray-800 rounded-lg transition-colors text-gray-400 hover:text-white"
            >
              <X size={24} />
            </button>
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto overflow-x-hidden pt-4">
          <Link
            href="/"
            onClick={onClose}
            className={`flex items-center gap-3 px-4 sm:px-6 py-3 hover:bg-gray-800 transition-colors text-sm sm:text-base ${isCollapsed ? 'justify-center px-0' : ''}`}
            title={isCollapsed ? "View Public Site" : ""}
          >
            <Home size={20} className="flex-shrink-0" />
            {!isCollapsed && <span>View Public Site</span>}
          </Link>

          <div className={`my-4 border-t border-gray-800 mx-4 ${isCollapsed ? 'mx-6' : ''}`}></div>

          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;

            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={onClose}
                className={`flex items-center gap-3 px-4 sm:px-6 py-3 transition-colors font-medium text-sm sm:text-base ${isActive
                  ? 'bg-indigo-600 text-white font-bold'
                  : 'hover:bg-gray-800 text-gray-400 hover:text-white'
                  } ${isCollapsed ? 'justify-center px-0' : ''}`}
                title={isCollapsed ? item.label : ""}
              >
                <Icon size={20} className="flex-shrink-0" />
                {!isCollapsed && <span className="truncate">{item.label}</span>}
              </Link>
            );
          })}
        </nav>

        <button
          onClick={handleLogout}
          className={`flex items-center gap-3 px-4 sm:px-6 py-4 hover:bg-red-600 transition-colors mt-auto mb-2 text-sm sm:text-base text-gray-400 hover:text-white ${isCollapsed ? 'justify-center px-0' : ''}`}
          title={isCollapsed ? "Logout" : ""}
        >
          <LogOut size={20} className="flex-shrink-0" />
          {!isCollapsed && <span>Logout</span>}
        </button>
      </aside>
    </>
  );
}
