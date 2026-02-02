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
  Filler,
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
  Legend,
  Filler
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
  viewsGrowth: number;
  commentsGrowth: number;
  subscribersGrowth: number;
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

interface GSCStats {
  timeline: {
    labels: string[];
    clicks: number[];
    impressions: number[];
  };
  summary: {
    clicks: number;
    impressions: number;
    ctr: number;
    position: number;
  };
  previous_summary: {
    clicks: number;
    impressions: number;
    ctr: number;
    position: number;
  };
  last_sync: string | null;
}

export default function AnalyticsPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [timeline, setTimeline] = useState<TimelineData | null>(null);
  const [categories, setCategories] = useState<CategoriesData | null>(null);
  const [gscStats, setGscStats] = useState<GSCStats | null>(null);
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
        categoriesRes,
        gscRes
      ] = await Promise.all([
        fetch(`${apiUrl}/analytics/overview/`, { headers }),
        fetch(`${apiUrl}/analytics/articles/top/?limit=10`, { headers }),
        fetch(`${apiUrl}/analytics/views/timeline/?days=30`, { headers }),
        fetch(`${apiUrl}/analytics/categories/`, { headers }),
        fetch(`${apiUrl}/analytics/gsc/?days=30`, { headers })
      ]);

      const overviewData = await overviewRes.json();
      const topArticlesData = await topArticlesRes.json();
      const timelineData = await timelineRes.json();
      const categoriesData = await categoriesRes.json();
      const gscData = gscRes.ok ? await gscRes.json() : null;

      setStats({
        totalArticles: overviewData.total_articles,
        totalViews: overviewData.total_views,
        totalComments: overviewData.total_comments,
        totalSubscribers: overviewData.total_subscribers,
        articlesGrowth: overviewData.articles_growth,
        viewsGrowth: overviewData.views_growth,
        commentsGrowth: overviewData.comments_growth,
        subscribersGrowth: overviewData.subscribers_growth,
        popularArticles: topArticlesData.articles
      });

      setTimeline(timelineData);
      setCategories(categoriesData);
      setGscStats(gscData);
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
      trend: `${(stats?.viewsGrowth ?? 0) > 0 ? '+' : ''}${stats?.viewsGrowth ?? 0}%`,
      trendUp: (stats?.viewsGrowth ?? 0) >= 0
    },
    {
      title: 'Articles',
      value: stats?.totalArticles?.toString() || '0',
      icon: FileText,
      color: 'bg-green-500',
      trend: `${(stats?.articlesGrowth ?? 0) > 0 ? '+' : ''}${stats?.articlesGrowth ?? 0}%`,
      trendUp: (stats?.articlesGrowth ?? 0) >= 0
    },
    {
      title: 'Comments',
      value: stats?.totalComments?.toString() || '0',
      icon: MessageSquare,
      color: 'bg-orange-500',
      trend: `${(stats?.commentsGrowth ?? 0) > 0 ? '+' : ''}${stats?.commentsGrowth ?? 0}%`,
      trendUp: (stats?.commentsGrowth ?? 0) >= 0
    },
    {
      title: 'Subscribers',
      value: stats?.totalSubscribers?.toString() || '0',
      icon: Mail,
      color: 'bg-purple-500',
      trend: `${(stats?.subscribersGrowth ?? 0) > 0 ? '+' : ''}${stats?.subscribersGrowth ?? 0}%`,
      trendUp: (stats?.subscribersGrowth ?? 0) >= 0
    },
  ];

  const getTrend = (current: number, previous: number) => {
    if (previous === 0) return { percent: '0%', up: true };
    const diff = ((current - previous) / previous) * 100;
    return {
      percent: `${Math.abs(Math.round(diff))}%`,
      up: diff >= 0
    };
  };

  const gscSummaries = gscStats ? [
    {
      title: 'Search Clicks',
      value: gscStats.summary.clicks.toLocaleString(),
      icon: TrendingUp,
      color: 'bg-indigo-600',
      ...getTrend(gscStats.summary.clicks, gscStats.previous_summary.clicks)
    },
    {
      title: 'Search Impressions',
      value: gscStats.summary.impressions.toLocaleString(),
      icon: Eye,
      color: 'bg-cyan-600',
      ...getTrend(gscStats.summary.impressions, gscStats.previous_summary.impressions)
    },
    {
      title: 'Avg. CTR',
      value: `${gscStats.summary.ctr}%`,
      icon: BarChart3,
      color: 'bg-pink-600',
      ...getTrend(gscStats.summary.ctr, gscStats.previous_summary.ctr)
    },
    {
      title: 'Avg. Position',
      value: gscStats.summary.position.toString(),
      icon: Clock,
      color: 'bg-amber-600',
      percent: (gscStats.summary.position < gscStats.previous_summary.position) ? 'Better' : 'Worse',
      up: gscStats.summary.position <= gscStats.previous_summary.position
    }
  ] : [];

  return (
    <div className="space-y-8 pb-12">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black text-gray-950">📊 Analytics Dashboard</h1>
          <p className="text-gray-500 text-sm">Real-time stats and Google Search performance</p>
        </div>
        {gscStats && (
          <div className="bg-green-50 px-4 py-2 rounded-lg border border-green-100 hidden sm:block">
            <p className="text-xs text-green-700 font-medium">Last GSC Sync:</p>
            <p className="text-sm text-green-800 font-bold">{new Date(gscStats.last_sync || '').toLocaleString()}</p>
          </div>
        )}
      </div>

      {/* Internal Stats Header */}
      <h2 className="text-xl font-bold text-gray-900 border-l-4 border-purple-600 pl-4">Site Usage</h2>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.title} className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 hover:shadow-md transition-shadow">
              <div className="flex items-center justify-between mb-4">
                <div className={`${stat.color} p-3 rounded-lg text-white shadow-sm`}>
                  <Icon size={24} />
                </div>
                <div className={`flex items-center gap-1 text-sm font-semibold ${stat.trendUp ? 'text-green-600' : 'text-red-600'}`}>
                  {stat.trendUp ? <ArrowUp size={16} /> : <ArrowDown size={16} />}
                  {stat.trend}
                </div>
              </div>
              <p className="text-3xl font-black text-gray-900">{stat.value}</p>
              <p className="text-gray-500 text-sm font-medium mt-1 uppercase tracking-wider">{stat.title}</p>
            </div>
          );
        })}
      </div>

      {/* GSC Section */}
      {gscStats && (
        <div className="space-y-6">
          <h2 className="text-xl font-bold text-gray-900 border-l-4 border-indigo-600 pl-4 mt-12">Google Search Console Performance</h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {gscSummaries.map((stat) => {
              const Icon = stat.icon;
              return (
                <div key={stat.title} className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 hover:shadow-md transition-shadow">
                  <div className="flex items-center justify-between mb-4">
                    <div className={`${stat.color} p-3 rounded-lg text-white shadow-sm`}>
                      <Icon size={24} />
                    </div>
                    {stat.percent && (
                      <div className={`flex items-center gap-1 text-sm font-semibold ${stat.up ? 'text-green-600' : 'text-red-600'}`}>
                        {stat.up ? <ArrowUp size={16} /> : <ArrowDown size={16} />}
                        {stat.percent}
                      </div>
                    )}
                  </div>
                  <p className="text-3xl font-black text-gray-900">{stat.value}</p>
                  <p className="text-gray-500 text-sm font-medium mt-1 uppercase tracking-wider">{stat.title}</p>
                </div>
              );
            })}
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <h3 className="text-lg font-bold text-gray-900 mb-6 flex items-center gap-2">
              <TrendingUp className="text-indigo-600" />
              Daily Search Clicks & Impressions
            </h3>
            <div className="h-[300px]">
              <Line
                data={{
                  labels: gscStats.timeline.labels,
                  datasets: [
                    {
                      label: 'Clicks',
                      data: gscStats.timeline.clicks,
                      borderColor: 'rgb(79, 70, 229)',
                      backgroundColor: 'rgba(79, 70, 229, 0.1)',
                      yAxisID: 'y',
                      tension: 0.3,
                      fill: true,
                    },
                    {
                      label: 'Impressions',
                      data: gscStats.timeline.impressions,
                      borderColor: 'rgb(8, 145, 178)',
                      backgroundColor: 'transparent',
                      yAxisID: 'y1',
                      tension: 0.3,
                      borderDash: [5, 5],
                    },
                  ],
                }}
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  interaction: {
                    mode: 'index',
                    intersect: false,
                  },
                  plugins: {
                    legend: { position: 'top' as const },
                  },
                  scales: {
                    y: {
                      type: 'linear' as const,
                      display: true,
                      position: 'left' as const,
                      title: { display: true, text: 'Clicks' },
                      beginAtZero: true
                    },
                    y1: {
                      type: 'linear' as const,
                      display: true,
                      position: 'right' as const,
                      title: { display: true, text: 'Impressions' },
                      grid: { drawOnChartArea: false },
                      beginAtZero: true
                    },
                  }
                }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Charts Row */}
      <h2 className="text-xl font-bold text-gray-900 border-l-4 border-green-600 pl-4 mt-12">Engagement & Distribution</h2>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Timeline Chart */}
        {timeline && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
              <FileText className="text-blue-600" />
              Articles Published (Last 30 Days)
            </h3>
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
                    fill: true,
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
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
              <BarChart3 className="text-green-600" />
              Articles by Category
            </h3>
            <div className="flex justify-center">
              <div className="w-full max-w-[300px]">
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
                      legend: { position: 'bottom' },
                    },
                  }}
                />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Top Articles Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <div className="flex items-center gap-2 mb-6">
          <BarChart3 className="text-purple-500" size={24} />
          <h2 className="text-xl font-bold text-gray-900">🔥 Top 10 Articles by Views</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100 text-left">
                <th className="pb-4 px-4 text-sm font-semibold text-gray-400 uppercase tracking-wider">Rank</th>
                <th className="pb-4 px-4 text-sm font-semibold text-gray-400 uppercase tracking-wider">Article</th>
                <th className="pb-4 px-4 text-sm font-semibold text-gray-400 uppercase tracking-wider text-right">Views</th>
                <th className="pb-4 px-4 text-sm font-semibold text-gray-400 uppercase tracking-wider text-right">Published</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50 text-gray-700">
              {stats?.popularArticles?.map((article, index) => (
                <tr key={article.id} className="hover:bg-gray-50/50 transition-colors">
                  <td className="py-4 px-4">
                    <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-gray-100 text-sm font-bold text-gray-600">
                      {index + 1}
                    </span>
                  </td>
                  <td className="py-4 px-4">
                    <a href={`/article/${article.slug}`} target="_blank" className="font-bold text-gray-900 hover:text-purple-600 transition-colors line-clamp-1">
                      {article.title}
                    </a>
                  </td>
                  <td className="py-4 px-4 text-right">
                    <span className="font-black text-gray-900">{article.views?.toLocaleString() || 0}</span>
                  </td>
                  <td className="py-4 px-4 text-right text-sm text-gray-500 font-medium">
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
