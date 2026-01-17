'use client';

import { Bell, User } from 'lucide-react';

export default function AdminHeader() {
  return (
    <header className="bg-white shadow-sm border-b border-gray-200 px-6 py-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-black text-gray-950">Admin Dashboard</h1>
        
        <div className="flex items-center gap-4">
          <button className="p-2 hover:bg-gray-100 rounded-full transition-colors relative">
            <Bell size={20} />
            <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
          </button>
          
          <div className="flex items-center gap-2 px-3 py-2 bg-gray-100 rounded-full">
            <User size={20} className="text-gray-800" />
            <span className="font-bold text-gray-900">Admin</span>
          </div>
        </div>
      </div>
    </header>
  );
}
