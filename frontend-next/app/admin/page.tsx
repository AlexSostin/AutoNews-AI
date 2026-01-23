'use client';

import { useState, useEffect } from 'react';
import { FileText, Folder, Tag, MessageSquare, Eye, Mail, Loader2, BarChart3 } from 'lucide-react';
import Link from 'next/link';
import { getApiUrl } from '@/lib/api';

interface Stats {
  articles: number;
  categories: number;
  tags: number;
  comments: number;
  views: number;
  subscribers: number;
}

export default function AdminDashboard() {
  const [stats, setStats] = useState<Stats>({
    articles: 0,
    categories: 0,
    tags: 0,
    comments: 0,
    views: 0,
    subscribers: 0
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const apiUrl = getApiUrl();
      const token = localStorage.getItem('access_token');
      const headers: HeadersInit = token ? { 'Authorization': `Bearer ${token}` } : {};

      const [articlesRes, categoriesRes, tagsRes, commentsRes, subscribersRes] = await Promise.all([
        fetch(`${apiUrl}/articles/`),
        fetch(`${apiUrl}/categories/`),
        fetch(`${apiUrl}/tags/`),
        fetch(`${apiUrl}/comments/`, { headers }),
        fetch(`${apiUrl}/subscribers/`, { headers }).catch(() => null)
      ]);

      const articlesData = await articlesRes.json();
      const categoriesData = await categoriesRes.json();
      const tagsData = await tagsRes.json();
      const commentsData = commentsRes.ok ? await commentsRes.json() : { results: [] };
      const subscribersData = subscribersRes?.ok ? await subscribersRes.json() : { results: [] };

      const articles = Array.isArray(articlesData) ? articlesData : articlesData.results || [];
      const totalViews = articles.reduce((sum: number, a: { views_count?: number }) => sum + (a.views_count || 0), 0);

      setStats({
        articles: articlesData.count || articles.length,
        categories: categoriesData.count || (Array.isArray(categoriesData) ? categoriesData : categoriesData.results || []).length,
        tags: tagsData.count || (Array.isArray(tagsData) ? tagsData : tagsData.results || []).length,
        comments: commentsData.count || (Array.isArray(commentsData) ? commentsData : commentsData.results || []).length,
        views: totalViews,
        subscribers: subscribersData.count || (Array.isArray(subscribersData) ? subscribersData : subscribersData.results || []).length
      });
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const statCards = [
    { title: 'Total Articles', value: stats.articles.toString(), icon: FileText, href: '/admin/articles', color: 'bg-blue-500' },
    { title: 'Total Views', value: stats.views.toLocaleString(), icon: Eye, href: '/admin/analytics', color: 'bg-purple-500' },
    { title: 'Categories', value: stats.categories.toString(), icon: Folder, href: '/admin/categories', color: 'bg-green-500' },
    { title: 'Comments', value: stats.comments.toString(), icon: MessageSquare, href: '/admin/comments', color: 'bg-orange-500' },
    { title: 'Subscribers', value: stats.subscribers.toString(), icon: Mail, href: '/admin/subscribers', color: 'bg-pink-500' },
    { title: 'Tags', value: stats.tags.toString(), icon: Tag, href: '/admin/tags', color: 'bg-indigo-500' },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="animate-spin text-purple-600" size={48} />
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl sm:text-3xl font-black text-gray-950 mb-4 sm:mb-8">Dashboard</h1>
      
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4 md:gap-6 mb-4 sm:mb-8">
        {statCards.map((stat) => {
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
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
          <Link
            href="/admin/articles/new"
            className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white p-3 sm:p-4 rounded-lg text-center text-sm sm:text-base font-bold hover:from-indigo-700 hover:to-purple-700 transition-all shadow-md"
          >
            Create New Article
          </Link>
          <Link
            href="/admin/analytics"
            className="bg-gradient-to-r from-purple-500 to-pink-500 text-white p-3 sm:p-4 rounded-lg text-center text-sm sm:text-base font-bold hover:from-purple-600 hover:to-pink-600 transition-all shadow-md"
          >
            View Analytics
          </Link>
          <Link
            href="/admin/subscribers"
            className="bg-gradient-to-r from-green-500 to-teal-500 text-white p-3 sm:p-4 rounded-lg text-center text-sm sm:text-base font-bold hover:from-green-600 hover:to-teal-600 transition-all shadow-md"
          >
            Send Newsletter
          </Link>
          <Link
            href="/admin/comments"
            className="bg-gradient-to-r from-orange-500 to-red-500 text-white p-3 sm:p-4 rounded-lg text-center text-sm sm:text-base font-bold hover:from-orange-600 hover:to-red-600 transition-all shadow-md"
          >
            Moderate Comments
          </Link>
        </div>
      </div>
    </div>
  );
}
