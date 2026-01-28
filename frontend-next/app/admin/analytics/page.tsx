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
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Line, Pie } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

interface Article {
  id: number;
  title: string;
  slug: string;
  views_count: number;
  views: number;
  created_at: string;
  category?: { name: string };
}

interface Stats {
  totalArticles: number;
  totalViews: number;
  totalComments: number;
  totalSubscribers: number;
  articlesGrowth: number;
  popularArticles: Article[];
}

interface TimelineData {
  labels: string[];
  data: number[];
}

interface CategoriesData {
  labels: string[];
  data: number[];
}

export default function AnalyticsPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [timeline, setTimeline] = useState<TimelineData | null>(null);
  const [categories, setCategories] = useState<CategoriesData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const apiUrl = getApiUrl();
      const token = localStorage.getItem('access_token');
      const headers: HeadersInit = token ? { 'Authorization': `Bearer ${token}` } : {};

      // Fetch new analytics endpoints
      const [
        overviewRes,
        topArticlesRes,
        timelineRes,
        categoriesRes
      ] = await Promise.all([
        fetch(`${apiUrl}/analytics/overview/`, { headers }),
        fetch(`${apiUrl}/analytics/articles/top/?limit=10`, { headers }),
        fetch(`${apiUrl}/analytics/views/timeline/?days=30`, { headers }),
        fetch(`${apiUrl}/analytics/categories/`, { headers })
      ]);

      const overviewData = await overviewRes.json();
      const topArticlesData = await topArticlesRes.json();
      const timelineData = await timelineRes.json();
      const categoriesData = await categoriesRes.json();

      setStats({
        totalArticles: overviewData.total_articles,
        totalViews: overviewData.total_views,
        totalComments: overviewData.total_comments,
        totalSubscribers: overviewData.total_subscribers,
        articlesGrowth: overviewData.articles_growth_percent,
        popularArticles: topArticlesData.articles
      });

      setTimeline(timelineData);
      setCategories(categoriesData);
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
      trend: `${(stats?.articlesGrowth ?? 0) > 0 ? '+' : ''}${stats?.articlesGrowth ?? 0}%`,
      trendUp: (stats?.articlesGrowth ?? 0) > 0
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
        <h1 className="text-2xl sm:text-3xl font-black text-gray-950">📊 Analytics Dashboard</h1>
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
                <div className={`flex items-center gap-1 text-sm font-medium ${stat.trendUp ? 'text-green-600' : 'text-red-600'
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

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Timeline Chart */}
        {timeline && (
          <div className="bg-white rounded-xl shadow-md p-6">
            <h3 className="text-lg font-bold text-gray-900 mb-4">📈 Articles Published (Last 30 Days)</h3>
            <Line
              data={{
                labels: timeline.labels,
                datasets: [
                  {
                    label: 'Articles',
                    data: timeline.data,
                    borderColor: 'rgb(59, 130, 246)',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.4,
                  },
                ],
              }}
              options={{
                responsive: true,
                plugins: {
                  legend: { display: false },
                },
                scales: {
                  y: {
                    beginAtZero: true,
                    ticks: { precision: 0 }
                  }
                }
              }}
            />
          </div>
        )}

        {/* Categories Pie Chart */}
        {categories && (
          <div className="bg-white rounded-xl shadow-md p-6">
            <h3 className="text-lg font-bold text-gray-900 mb-4">🥧 Articles by Category</h3>
            <Pie
              data={{
                labels: categories.labels,
                datasets: [
                  {
                    data: categories.data,
                    backgroundColor: [
                      'rgba(59, 130, 246, 0.8)',
                      'rgba(16, 185, 129, 0.8)',
                      'rgba(139, 92, 246, 0.8)',
                      'rgba(249, 115, 22, 0.8)',
                      'rgba(236, 72, 153, 0.8)',
                      'rgba(234, 179, 8, 0.8)',
                    ],
                    borderWidth: 2,
                  },
                ],
              }}
              options={{
                responsive: true,
                plugins: {
                  legend: { position: 'right' },
                },
              }}
            />
          </div>
        )}
      </div>

      {/* Top Articles Table */}
      <div className="bg-white rounded-xl shadow-md p-6">
        <div className="flex items-center gap-2 mb-4">
          <BarChart3 className="text-purple-500" size={24} />
          <h2 className="text-xl font-bold text-gray-900">🔥 Top 10 Articles by Views</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-3 px-4 text-sm font-semibold text-gray-600">Rank</th>
                <th className="text-left py-3 px-4 text-sm font-semibold text-gray-600">Title</th>
                <th className="text-left py-3 px-4 text-sm font-semibold text-gray-600">Views</th>
                <th className="text-left py-3 px-4 text-sm font-semibold text-gray-600">Published</th>
              </tr>
            </thead>
            <tbody>
              {stats?.popularArticles?.map((article, index) => (
                <tr key={article.id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="py-3 px-4">
                    <span className="text-xl">
                      {index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : `${index + 1}.`}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <a href={`/article/${article.slug}`} target="_blank" className="text-blue-600 hover:underline font-medium">
                      {article.title}
                    </a>
                  </td>
                  <td className="py-3 px-4">
                    <span className="font-semibold">{article.views?.toLocaleString() || 0}</span>
                  </td>
                  <td className="py-3 px-4 text-sm text-gray-500">
                    {new Date(article.created_at).toLocaleDateString()}
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
