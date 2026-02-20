'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState, useEffect } from 'react';
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
  Bell,
  Languages,
  Car,
  Wrench,
  ArrowRightLeft,
  Globe,
  MessageSquareWarning,
  FlaskConical,
  Megaphone,
  Bot,
  Users,
  LucideIcon
} from 'lucide-react';
import { logout, isSuperuser } from '@/lib/auth';

interface MenuItem {
  href: string;
  icon: LucideIcon;
  label: string;
  superuserOnly?: boolean;
}

interface MenuSection {
  title: string;
  items: MenuItem[];
}

const menuSections: MenuSection[] = [
  {
    title: 'Overview',
    items: [
      { href: '/admin', icon: LayoutDashboard, label: 'Dashboard' },
      { href: '/admin/analytics', icon: BarChart3, label: 'Analytics' },
      { href: '/admin/notifications', icon: Bell, label: 'Notifications' },
    ],
  },
  {
    title: 'Content',
    items: [
      { href: '/admin/articles', icon: FileText, label: 'Articles' },
      { href: '/admin/categories', icon: Folder, label: 'Categories' },
      { href: '/admin/tags', icon: Tag, label: 'Tags' },
      { href: '/admin/pages', icon: FileStack, label: 'Pages' },
      { href: '/admin/translate', icon: Languages, label: 'Translate & Enhance' },
    ],
  },
  {
    title: 'Automotive',
    items: [
      { href: '/admin/brands', icon: Globe, label: 'Brands' },
      { href: '/admin/brand-aliases', icon: ArrowRightLeft, label: 'Brand Aliases' },
      { href: '/admin/car-specs', icon: Car, label: 'Car Specs' },
      { href: '/admin/vehicle-specs', icon: Wrench, label: 'Vehicle Specs' },
    ],
  },
  {
    title: 'Sources',
    items: [
      { href: '/admin/rss-feeds', icon: Rss, label: 'RSS Feeds' },
      { href: '/admin/rss-pending', icon: FileStack, label: 'RSS News' },
      { href: '/admin/youtube-channels', icon: Youtube, label: 'YouTube Channels' },
    ],
  },
  {
    title: 'Audience',
    items: [
      { href: '/admin/comments', icon: MessageSquare, label: 'Comments' },
      { href: '/admin/feedback', icon: MessageSquareWarning, label: 'Feedback' },
      { href: '/admin/subscribers', icon: Mail, label: 'Subscribers' },
    ],
  },
  {
    title: 'Tools',
    items: [
      { href: '/admin/automation', icon: Bot, label: 'Automation' },
      { href: '/admin/ab-testing', icon: FlaskConical, label: 'A/B Testing' },
      { href: '/admin/ads', icon: Megaphone, label: 'Ads / Sponsors' },
    ],
  },
  {
    title: 'Settings',
    items: [
      { href: '/admin/settings', icon: Settings, label: 'Site Settings' },
      { href: '/admin/account', icon: UserCog, label: 'Account Settings' },
      { href: '/admin/users', icon: Users, label: 'Users', superuserOnly: true },
    ],
  },
];

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  isCollapsed: boolean;
  onToggle: () => void;
}

export default function Sidebar({ isOpen, onClose, isCollapsed, onToggle }: SidebarProps) {
  const pathname = usePathname();
  const [isSuperuserState, setIsSuperuserState] = useState(false);

  useEffect(() => {
    setIsSuperuserState(isSuperuser());
  }, []);

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
        {/* Header */}
        <div className={`p-4 sm:p-6 flex items-center ${isCollapsed ? 'justify-center' : 'justify-between'} border-b border-gray-800/50`}>
          {!isCollapsed && (
            <h2 className="text-xl sm:text-2xl font-black bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent truncate">
              FM Admin
            </h2>
          )}

          <div className="flex items-center gap-1">
            <button
              onClick={onToggle}
              className="hidden lg:flex p-2 hover:bg-gray-800 rounded-lg transition-colors text-gray-400 hover:text-white"
              title={isCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
            >
              {isCollapsed ? <ChevronRight size={20} /> : <ChevronLeft size={20} />}
            </button>
            <button
              onClick={onClose}
              className="lg:hidden p-2 hover:bg-gray-800 rounded-lg transition-colors text-gray-400 hover:text-white"
            >
              <X size={24} />
            </button>
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto overflow-x-hidden pt-4">
          {/* View Public Site */}
          <Link
            href="/"
            onClick={onClose}
            className={`flex items-center gap-3 px-4 sm:px-6 py-3 hover:bg-gray-800 transition-colors text-sm sm:text-base ${isCollapsed ? 'justify-center px-0' : ''}`}
            title={isCollapsed ? "View Public Site" : ""}
          >
            <Home size={20} className="flex-shrink-0" />
            {!isCollapsed && <span>View Public Site</span>}
          </Link>

          {/* Menu Sections */}
          {menuSections.map((section) => {
            const visibleItems = section.items.filter(item => {
              if (item.superuserOnly) return isSuperuserState;
              return true;
            });

            if (visibleItems.length === 0) return null;

            return (
              <div key={section.title}>
                {/* Section Divider */}
                <div className={`my-2 border-t border-gray-800/50 mx-4`} />

                {/* Section Label */}
                {!isCollapsed && (
                  <div className="px-6 pt-2 pb-1">
                    <span className="text-[10px] font-bold uppercase tracking-widest text-gray-500">
                      {section.title}
                    </span>
                  </div>
                )}

                {/* Section Items */}
                {visibleItems.map((item) => {
                  const Icon = item.icon;
                  const isActive = pathname === item.href;

                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      onClick={onClose}
                      className={`flex items-center gap-3 px-4 sm:px-6 py-2.5 transition-colors font-medium text-sm ${isActive
                        ? 'bg-indigo-600 text-white font-bold'
                        : 'hover:bg-gray-800 text-gray-400 hover:text-white'
                        } ${isCollapsed ? 'justify-center px-0' : ''}`}
                      title={isCollapsed ? item.label : ""}
                    >
                      <Icon size={18} className="flex-shrink-0" />
                      {!isCollapsed && <span className="truncate">{item.label}</span>}
                    </Link>
                  );
                })}
              </div>
            );
          })}
        </nav>

        {/* Logout */}
        <div className="border-t border-gray-800/50 mx-4 mt-2" />
        <button
          onClick={handleLogout}
          className={`flex items-center gap-3 px-4 sm:px-6 py-4 hover:bg-red-600 transition-colors mt-2 mb-2 text-sm sm:text-base text-gray-400 hover:text-white ${isCollapsed ? 'justify-center px-0' : ''}`}
          title={isCollapsed ? "Logout" : ""}
        >
          <LogOut size={20} className="flex-shrink-0" />
          {!isCollapsed && <span>Logout</span>}
        </button>
      </aside>
    </>
  );
}
