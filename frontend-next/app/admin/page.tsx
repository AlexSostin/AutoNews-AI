'use client';

import { FileText, Folder, Tag, MessageSquare } from 'lucide-react';
import Link from 'next/link';

export default function AdminDashboard() {
  const stats = [
    { title: 'Total Articles', value: '0', icon: FileText, href: '/admin/articles', color: 'bg-blue-500' },
    { title: 'Categories', value: '0', icon: Folder, href: '/admin/categories', color: 'bg-green-500' },
    { title: 'Tags', value: '0', icon: Tag, href: '/admin/tags', color: 'bg-purple-500' },
    { title: 'Comments', value: '0', icon: MessageSquare, href: '/admin/comments', color: 'bg-orange-500' },
  ];

  return (
    <div>
      <h1 className="text-2xl sm:text-3xl font-black text-gray-950 mb-4 sm:mb-8">Dashboard</h1>
      
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 md:gap-6 mb-4 sm:mb-8">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <Link
              key={stat.title}
              href={stat.href}
              className="bg-white rounded-lg shadow p-4 sm:p-6 hover:shadow-lg transition-shadow"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-700 text-xs sm:text-sm font-semibold">{stat.title}</p>
                  <p className="text-2xl sm:text-3xl font-black text-gray-950 mt-1 sm:mt-2">{stat.value}</p>
                </div>
                <div className={`${stat.color} p-3 sm:p-4 rounded-full text-white`}>
                  <Icon size={20} className="sm:w-6 sm:h-6" />
                </div>
              </div>
            </Link>
          );
        })}
      </div>

      <div className="bg-white rounded-lg shadow p-4 sm:p-6">
        <h2 className="text-lg sm:text-xl font-black text-gray-950 mb-3 sm:mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
          <Link
            href="/admin/articles"
            className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white p-3 sm:p-4 rounded-lg text-center text-sm sm:text-base font-bold hover:from-indigo-700 hover:to-purple-700 transition-all shadow-md"
          >
            Create New Article
          </Link>
          <Link
            href="/admin/categories"
            className="bg-gradient-to-r from-green-500 to-teal-500 text-white p-3 sm:p-4 rounded-lg text-center text-sm sm:text-base font-bold hover:from-green-600 hover:to-teal-600 transition-all shadow-md"
          >
            Manage Categories
          </Link>
          <Link
            href="/admin/comments"
            className="bg-gradient-to-r from-orange-500 to-red-500 text-white p-3 sm:p-4 rounded-lg text-center text-sm sm:text-base font-bold hover:from-orange-600 hover:to-red-600 transition-all shadow-md"
          >
            Moderate Comments
          </Link>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-4 sm:p-6 mt-4 sm:mt-6">
        <h2 className="text-lg sm:text-xl font-black text-gray-950 mb-3 sm:mb-4">Welcome to AutoNews Admin!</h2>
        <p className="text-sm sm:text-base text-gray-800 mb-3 sm:mb-4 font-medium">
          This is your admin dashboard. From here you can manage all aspects of your automotive news site.
        </p>
        <ul className="list-disc list-inside text-sm sm:text-base text-gray-800 space-y-1 sm:space-y-2 font-medium">
          <li>Create and publish articles with rich content</li>
          <li>Organize content with categories and tags</li>
          <li>Moderate user comments</li>
          <li>View analytics and statistics</li>
        </ul>
        <div className="mt-4 sm:mt-6">
          <Link href="/" className="text-sm sm:text-base text-indigo-600 hover:underline font-bold">
            → View Public Site
          </Link>
        </div>
      </div>
    </div>
  );
}
