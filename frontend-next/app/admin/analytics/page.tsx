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
  Mail,
  Tag,
  Cpu,
  Sparkles,
  CheckCircle2,
  Youtube,
  Rss,
  Languages
} from 'lucide-react';
import api from '@/lib/api';
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
import { Line, Pie, Bar, Doughnut } from 'react-chartjs-2';

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
  name: string;
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

interface AIStats {
  enrichment: {
    total_articles: number;
    vehicle_specs: number;
    ab_titles: number;
    tags: number;
    car_specs: number;
    images: number;
  };
  top_tags: {
    name: string;
    slug: string;
    article_count: number;
    total_views: number;
  }[];
  sources: {
    youtube: number;
    rss: number;
    translated: number;
  };
}

export default function AnalyticsPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [timeline, setTimeline] = useState<TimelineData | null>(null);
  const [categories, setCategories] = useState<CategoriesData | null>(null);
  const [gscStats, setGscStats] = useState<GSCStats | null>(null);
  const [aiStats, setAiStats] = useState<AIStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const [
        overviewRes,
        topArticlesRes,
        timelineRes,
        categoriesRes,
        gscRes,
        aiRes
      ] = await Promise.all([
        api.get('/analytics/overview/'),
        api.get('/analytics/articles/top/?limit=10'),
        api.get('/analytics/views/timeline/?days=30'),
        api.get('/analytics/categories/'),
        api.get('/analytics/gsc/?days=30').catch(() => ({ data: null })),
        api.get('/analytics/ai-stats/').catch(() => ({ data: null }))
      ]);

      setStats({
        totalArticles: overviewRes.data.total_articles,
        totalViews: overviewRes.data.total_views,
        totalComments: overviewRes.data.total_comments,
        totalSubscribers: overviewRes.data.total_subscribers,
        articlesGrowth: overviewRes.data.articles_growth,
        viewsGrowth: overviewRes.data.views_growth,
        commentsGrowth: overviewRes.data.comments_growth,
        subscribersGrowth: overviewRes.data.subscribers_growth,
        popularArticles: topArticlesRes.data.articles
      });

      setTimeline(timelineRes.data);
      setCategories(categoriesRes.data);
      setGscStats(gscRes.data);
      setAiStats(aiRes.data);
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

  // Enrichment progress bar helper
  const getEnrichmentPercent = (count: number) => {
    if (!aiStats?.enrichment.total_articles) return 0;
    return Math.round((count / aiStats.enrichment.total_articles) * 100);
  };

  const enrichmentItems = aiStats ? [
    { label: 'Deep Specs (VehicleSpecs)', count: aiStats.enrichment.vehicle_specs, icon: Sparkles, color: 'bg-violet-500' },
    { label: 'A/B Title Variants', count: aiStats.enrichment.ab_titles, icon: FileText, color: 'bg-blue-500' },
    { label: 'Tags Assigned', count: aiStats.enrichment.tags, icon: Tag, color: 'bg-emerald-500' },
    { label: 'Car Specifications', count: aiStats.enrichment.car_specs, icon: Cpu, color: 'bg-orange-500' },
    { label: 'Featured Images', count: aiStats.enrichment.images, icon: Eye, color: 'bg-pink-500' },
  ] : [];

  return (
    <div className="space-y-8 pb-12">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black text-gray-950">📊 Analytics Dashboard</h1>
          <p className="text-gray-500 text-sm">Real-time stats, AI insights, and Google Search performance</p>
        </div>
        {gscStats && (
          <div className="bg-green-50 px-4 py-2 rounded-lg border border-green-100 hidden sm:block">
            <p className="text-xs text-green-700 font-medium">Last GSC Sync:</p>
            <p className="text-sm text-green-800 font-bold">
              {gscStats.last_sync
                ? new Date(gscStats.last_sync).toLocaleString()
                : 'Never synced yet'}
            </p>
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

      {/* AI & Enrichment Section */}
      {aiStats && (
        <div className="space-y-6">
          <h2 className="text-xl font-bold text-gray-900 border-l-4 border-violet-600 pl-4 mt-12">🤖 AI & Enrichment Stats</h2>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Enrichment Coverage */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
              <h3 className="text-lg font-bold text-gray-900 mb-2 flex items-center gap-2">
                <CheckCircle2 className="text-violet-600" size={20} />
                Enrichment Coverage
              </h3>
              <p className="text-xs text-gray-400 mb-6">
                Out of {aiStats.enrichment.total_articles} published articles
              </p>
              <div className="space-y-4">
                {enrichmentItems.map((item) => {
                  const Icon = item.icon;
                  const percent = getEnrichmentPercent(item.count);
                  return (
                    <div key={item.label}>
                      <div className="flex items-center justify-between mb-1.5">
                        <div className="flex items-center gap-2">
                          <Icon size={16} className="text-gray-500" />
                          <span className="text-sm font-semibold text-gray-700">{item.label}</span>
                        </div>
                        <span className="text-sm font-black text-gray-900">
                          {item.count} <span className="text-gray-400 font-medium">({percent}%)</span>
                        </span>
                      </div>
                      <div className="w-full bg-gray-100 rounded-full h-2.5">
                        <div
                          className={`${item.color} h-2.5 rounded-full transition-all duration-500`}
                          style={{ width: `${Math.max(percent, 2)}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* AI Source Breakdown */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
              <h3 className="text-lg font-bold text-gray-900 mb-6 flex items-center gap-2">
                <Cpu className="text-violet-600" size={20} />
                Article Sources
              </h3>
              <div className="flex flex-col items-center gap-6">
                <div className="w-full max-w-[250px]">
                  <Doughnut
                    data={{
                      labels: ['YouTube', 'RSS Feeds', 'Translated/Manual'],
                      datasets: [{
                        data: [
                          aiStats.sources.youtube,
                          aiStats.sources.rss,
                          aiStats.sources.translated,
                        ],
                        backgroundColor: [
                          'rgba(239, 68, 68, 0.85)',
                          'rgba(249, 115, 22, 0.85)',
                          'rgba(139, 92, 246, 0.85)',
                        ],
                        borderWidth: 3,
                        borderColor: '#fff',
                      }],
                    }}
                    options={{
                      responsive: true,
                      cutout: '60%',
                      plugins: {
                        legend: { display: false },
                      },
                    }}
                  />
                </div>
                <div className="grid grid-cols-3 gap-3 w-full">
                  {[
                    { label: 'YouTube', count: aiStats.sources.youtube, icon: Youtube, color: 'text-red-500', bg: 'bg-red-50' },
                    { label: 'RSS', count: aiStats.sources.rss, icon: Rss, color: 'text-orange-500', bg: 'bg-orange-50' },
                    { label: 'Translated', count: aiStats.sources.translated, icon: Languages, color: 'text-violet-500', bg: 'bg-violet-50' },
                  ].map((src) => {
                    const SrcIcon = src.icon;
                    return (
                      <div key={src.label} className={`${src.bg} rounded-lg p-3 text-center`}>
                        <SrcIcon size={18} className={`${src.color} mx-auto mb-1`} />
                        <p className="text-xl font-black text-gray-900">{src.count}</p>
                        <p className="text-xs font-semibold text-gray-500">{src.label}</p>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>

          {/* Top Tags */}
          {aiStats.top_tags.length > 0 && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
              <h3 className="text-lg font-bold text-gray-900 mb-6 flex items-center gap-2">
                <Tag className="text-emerald-600" size={20} />
                🏷️ Top Tags by Views
              </h3>
              <div className="h-[300px]">
                <Bar
                  data={{
                    labels: aiStats.top_tags.map(t => t.name),
                    datasets: [
                      {
                        label: 'Total Views',
                        data: aiStats.top_tags.map(t => t.total_views),
                        backgroundColor: 'rgba(16, 185, 129, 0.7)',
                        borderColor: 'rgba(16, 185, 129, 1)',
                        borderWidth: 1,
                        borderRadius: 6,
                      },
                      {
                        label: 'Articles',
                        data: aiStats.top_tags.map(t => t.article_count),
                        backgroundColor: 'rgba(139, 92, 246, 0.7)',
                        borderColor: 'rgba(139, 92, 246, 1)',
                        borderWidth: 1,
                        borderRadius: 6,
                        yAxisID: 'y1',
                      },
                    ],
                  }}
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                      mode: 'index' as const,
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
                        title: { display: true, text: 'Views' },
                        beginAtZero: true,
                      },
                      y1: {
                        type: 'linear' as const,
                        display: true,
                        position: 'right' as const,
                        title: { display: true, text: 'Articles' },
                        grid: { drawOnChartArea: false },
                        beginAtZero: true,
                        ticks: { precision: 0 },
                      },
                      x: {
                        ticks: {
                          maxRotation: 45,
                          minRotation: 45,
                          font: { size: 11 },
                        },
                      },
                    },
                  }}
                />
              </div>
            </div>
          )}
        </div>
      )}

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
