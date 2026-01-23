'use client';

import { useState, useEffect } from 'react';
import { 
  BarChart3, 
  TrendingUp, 
  Eye, 
  FileText, 
  MessageSquare,
  Clock,
  ArrowUp,
  ArrowDown,
  Loader2,
  Mail
} from 'lucide-react';
import { getApiUrl } from '@/lib/api';

interface Article {
  id: number;
  title: string;
  slug: string;
  views_count: number;
  created_at: string;
  category?: { name: string };
}

interface Stats {
  totalArticles: number;
  totalViews: number;
  totalComments: number;
  totalSubscribers: number;
  totalCategories: number;
  trendingArticles: Article[];
  popularArticles: Article[];
  recentArticles: Article[];
}

export default function AnalyticsPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | 'all'>('7d');

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const apiUrl = getApiUrl();
      const token = localStorage.getItem('access_token');
      const headers: HeadersInit = token ? { 'Authorization': `Bearer ${token}` } : {};

      // Fetch all data in parallel
      const [
        articlesRes,
        trendingRes,
        popularRes,
        categoriesRes,
        commentsRes,
        subscribersRes
      ] = await Promise.all([
        fetch(`${apiUrl}/articles/`),
        fetch(`${apiUrl}/articles/trending/`),
        fetch(`${apiUrl}/articles/popular/`),
        fetch(`${apiUrl}/categories/`),
        fetch(`${apiUrl}/comments/`, { headers }),
        fetch(`${apiUrl}/subscribers/`, { headers }).catch(() => null)
      ]);

      const articlesData = await articlesRes.json();
      const trendingData = await trendingRes.json();
      const popularData = await popularRes.json();
      const categoriesData = await categoriesRes.json();
      const commentsData = commentsRes.ok ? await commentsRes.json() : { results: [] };
      const subscribersData = subscribersRes?.ok ? await subscribersRes.json() : { results: [] };

      const articles = Array.isArray(articlesData) ? articlesData : articlesData.results || [];
      const trending = Array.isArray(trendingData) ? trendingData : trendingData.results || [];
      const popular = Array.isArray(popularData) ? popularData : popularData.results || [];
      const categories = Array.isArray(categoriesData) ? categoriesData : categoriesData.results || [];
      const comments = Array.isArray(commentsData) ? commentsData : commentsData.results || [];
      const subscribers = Array.isArray(subscribersData) ? subscribersData : subscribersData.results || [];

      // Calculate total views
      const totalViews = articles.reduce((sum: number, a: Article) => sum + (a.views_count || 0), 0);

      setStats({
        totalArticles: articlesData.count || articles.length,
        totalViews,
        totalComments: commentsData.count || comments.length,
        totalSubscribers: subscribersData.count || subscribers.length,
        totalCategories: categoriesData.count || categories.length,
        trendingArticles: trending.slice(0, 10),
        popularArticles: popular.slice(0, 10),
        recentArticles: articles.slice(0, 5)
      });
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="animate-spin text-purple-600" size={48} />
      </div>
    );
  }

  const statCards = [
    { 
      title: 'Total Views', 
      value: stats?.totalViews?.toLocaleString() || '0', 
      icon: Eye, 
      color: 'bg-blue-500',
      trend: '+12%',
      trendUp: true
    },
    { 
      title: 'Articles', 
      value: stats?.totalArticles?.toString() || '0', 
      icon: FileText, 
      color: 'bg-green-500',
      trend: '+3',
      trendUp: true
    },
    { 
      title: 'Comments', 
      value: stats?.totalComments?.toString() || '0', 
      icon: MessageSquare, 
      color: 'bg-orange-500',
      trend: '+8',
      trendUp: true
    },
    { 
      title: 'Subscribers', 
      value: stats?.totalSubscribers?.toString() || '0', 
      icon: Mail, 
      color: 'bg-purple-500',
      trend: '+5',
      trendUp: true
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <h1 className="text-2xl sm:text-3xl font-black text-gray-950">Analytics</h1>
        
        {/* Time Range Selector */}
        <div className="flex gap-2 bg-white rounded-lg p-1 shadow">
          {[
            { value: '7d', label: '7 Days' },
            { value: '30d', label: '30 Days' },
            { value: 'all', label: 'All Time' }
          ].map((option) => (
            <button
              key={option.value}
              onClick={() => setTimeRange(option.value as '7d' | '30d' | 'all')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                timeRange === option.value
                  ? 'bg-purple-600 text-white'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.title} className="bg-white rounded-xl shadow-md p-6">
              <div className="flex items-center justify-between mb-4">
                <div className={`${stat.color} p-3 rounded-lg text-white`}>
                  <Icon size={24} />
                </div>
                <div className={`flex items-center gap-1 text-sm font-medium ${
                  stat.trendUp ? 'text-green-600' : 'text-red-600'
                }`}>
                  {stat.trendUp ? <ArrowUp size={16} /> : <ArrowDown size={16} />}
                  {stat.trend}
                </div>
              </div>
              <p className="text-3xl font-black text-gray-900">{stat.value}</p>
              <p className="text-gray-500 text-sm mt-1">{stat.title}</p>
            </div>
          );
        })}
      </div>

      {/* Trending & Popular Articles */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Trending Articles */}
        <div className="bg-white rounded-xl shadow-md p-6">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="text-orange-500" size={24} />
            <h2 className="text-xl font-bold text-gray-900">Trending (7 Days)</h2>
          </div>
          <div className="space-y-3">
            {stats?.trendingArticles?.length ? (
              stats.trendingArticles.map((article, index) => (
                <div 
                  key={article.id} 
                  className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <span className={`w-8 h-8 rounded-full flex items-center justify-center text-white font-bold text-sm ${
                    index === 0 ? 'bg-yellow-500' : 
                    index === 1 ? 'bg-gray-400' : 
                    index === 2 ? 'bg-orange-600' : 'bg-gray-300'
                  }`}>
                    {index + 1}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900 truncate text-sm">
                      {article.title}
                    </p>
                    <p className="text-xs text-gray-500">
                      {article.category?.name || 'Uncategorized'}
                    </p>
                  </div>
                  <div className="flex items-center gap-1 text-gray-600">
                    <Eye size={14} />
                    <span className="text-sm font-medium">{article.views_count?.toLocaleString() || 0}</span>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-gray-500 text-center py-4">No trending articles yet</p>
            )}
          </div>
        </div>

        {/* Popular All Time */}
        <div className="bg-white rounded-xl shadow-md p-6">
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="text-purple-500" size={24} />
            <h2 className="text-xl font-bold text-gray-900">Popular (All Time)</h2>
          </div>
          <div className="space-y-3">
            {stats?.popularArticles?.length ? (
              stats.popularArticles.map((article, index) => (
                <div 
                  key={article.id} 
                  className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <span className={`w-8 h-8 rounded-full flex items-center justify-center text-white font-bold text-sm ${
                    index === 0 ? 'bg-purple-600' : 
                    index === 1 ? 'bg-purple-500' : 
                    index === 2 ? 'bg-purple-400' : 'bg-gray-300'
                  }`}>
                    {index + 1}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900 truncate text-sm">
                      {article.title}
                    </p>
                    <p className="text-xs text-gray-500">
                      {article.category?.name || 'Uncategorized'}
                    </p>
                  </div>
                  <div className="flex items-center gap-1 text-gray-600">
                    <Eye size={14} />
                    <span className="text-sm font-medium">{article.views_count?.toLocaleString() || 0}</span>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-gray-500 text-center py-4">No popular articles yet</p>
            )}
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-white rounded-xl shadow-md p-6">
        <div className="flex items-center gap-2 mb-4">
          <Clock className="text-blue-500" size={24} />
          <h2 className="text-xl font-bold text-gray-900">Recent Articles</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-3 px-4 text-sm font-semibold text-gray-600">Title</th>
                <th className="text-left py-3 px-4 text-sm font-semibold text-gray-600">Category</th>
                <th className="text-left py-3 px-4 text-sm font-semibold text-gray-600">Views</th>
                <th className="text-left py-3 px-4 text-sm font-semibold text-gray-600">Published</th>
              </tr>
            </thead>
            <tbody>
              {stats?.recentArticles?.map((article) => (
                <tr key={article.id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="py-3 px-4">
                    <p className="font-medium text-gray-900 truncate max-w-xs">{article.title}</p>
                  </td>
                  <td className="py-3 px-4">
                    <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded text-xs font-medium">
                      {article.category?.name || 'Uncategorized'}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <span className="text-gray-600">{article.views_count?.toLocaleString() || 0}</span>
                  </td>
                  <td className="py-3 px-4">
                    <span className="text-gray-500 text-sm">
                      {new Date(article.created_at).toLocaleDateString()}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
