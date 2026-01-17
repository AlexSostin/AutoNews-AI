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
  Settings
} from 'lucide-react';
import { logout } from '@/lib/auth';

const menuItems = [
  { href: '/admin', icon: LayoutDashboard, label: 'Dashboard' },
  { href: '/admin/articles', icon: FileText, label: 'Articles' },
  { href: '/admin/categories', icon: Folder, label: 'Categories' },
  { href: '/admin/tags', icon: Tag, label: 'Tags' },
  { href: '/admin/comments', icon: MessageSquare, label: 'Comments' },
  { href: '/admin/settings', icon: Settings, label: 'Settings' },
];

export default function Sidebar() {
  const pathname = usePathname();

  const handleLogout = () => {
    logout();
  };

  return (
    <aside className="w-64 bg-gray-900 text-white min-h-screen flex flex-col">
      <div className="p-6">
        <h2 className="text-2xl font-black bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
          AutoNews Admin
        </h2>
      </div>
      
      <nav className="flex-1">
        <Link
          href="/"
          className="flex items-center gap-3 px-6 py-3 hover:bg-gray-800 transition-colors"
        >
          <Home size={20} />
          View Public Site
        </Link>
        
        <div className="my-4 border-t border-gray-700"></div>
        
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-6 py-3 transition-colors font-medium ${
                isActive 
                  ? 'bg-indigo-600 text-white font-bold' 
                  : 'hover:bg-gray-800'
              }`}
            >
              <Icon size={20} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <button
        onClick={handleLogout}
        className="flex items-center gap-3 px-6 py-3 hover:bg-red-600 transition-colors mt-auto mb-4"
      >
        <LogOut size={20} />
        Logout
      </button>
    </aside>
  );
}
