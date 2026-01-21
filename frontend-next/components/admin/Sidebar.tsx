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
  FileStack
} from 'lucide-react';
import { logout } from '@/lib/auth';

const menuItems = [
  { href: '/admin', icon: LayoutDashboard, label: 'Dashboard' },
  { href: '/admin/articles', icon: FileText, label: 'Articles' },
  { href: '/admin/categories', icon: Folder, label: 'Categories' },
  { href: '/admin/tags', icon: Tag, label: 'Tags' },
  { href: '/admin/comments', icon: MessageSquare, label: 'Comments' },
  { href: '/admin/pages', icon: FileStack, label: 'Pages' },
  { href: '/admin/settings', icon: Settings, label: 'Settings' },
];

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function Sidebar({ isOpen, onClose }: SidebarProps) {
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
        w-64 bg-gray-900 text-white min-h-screen flex flex-col
        transform transition-transform duration-300 ease-in-out
        ${isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        {/* Header with Close Button (Mobile) */}
        <div className="p-4 sm:p-6 flex items-center justify-between">
          <h2 className="text-xl sm:text-2xl font-black bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
            AutoNews Admin
          </h2>
          <button
            onClick={onClose}
            className="lg:hidden p-2 hover:bg-gray-800 rounded-lg transition-colors"
          >
            <X size={24} />
          </button>
        </div>
        
        <nav className="flex-1 overflow-y-auto">
          <Link
            href="/"
            onClick={onClose}
            className="flex items-center gap-3 px-4 sm:px-6 py-3 hover:bg-gray-800 transition-colors text-sm sm:text-base"
          >
            <Home size={20} />
            <span>View Public Site</span>
          </Link>
          
          <div className="my-4 border-t border-gray-700"></div>
          
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={onClose}
                className={`flex items-center gap-3 px-4 sm:px-6 py-3 transition-colors font-medium text-sm sm:text-base ${
                  isActive 
                    ? 'bg-indigo-600 text-white font-bold' 
                    : 'hover:bg-gray-800'
                }`}
              >
                <Icon size={20} className="flex-shrink-0" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <button
          onClick={handleLogout}
          className="flex items-center gap-3 px-4 sm:px-6 py-3 hover:bg-red-600 transition-colors mt-auto mb-4 text-sm sm:text-base"
        >
          <LogOut size={20} className="flex-shrink-0" />
          <span>Logout</span>
        </button>
      </aside>
    </>
  );
}
