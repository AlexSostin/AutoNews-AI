'use client';

import { Bell, User, Menu } from 'lucide-react';

interface AdminHeaderProps {
  onMenuClick: () => void;
}

export default function AdminHeader({ onMenuClick }: AdminHeaderProps) {
  return (
    <header className="bg-white shadow-sm border-b border-gray-200 px-3 sm:px-4 md:px-6 py-3 sm:py-4">
      <div className="flex items-center justify-between">
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
          <button className="p-2 hover:bg-gray-100 rounded-full transition-colors relative">
            <Bell size={18} className="sm:w-5 sm:h-5" />
            <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
          </button>
          
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
