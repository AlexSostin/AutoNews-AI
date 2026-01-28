'use client';

import { useState, useEffect } from 'react';
import {
  FileText,
  Check,
  X,
  Eye,
  Loader2,
  Clock,
  Youtube,
  ArrowLeft,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { getApiUrl } from '@/lib/api';
import Link from 'next/link';

interface PendingArticle {
  id: number;
  youtube_channel: number;
  channel_name: string;
  video_url: string;
  video_id: string;
  video_title: string;
  title: string;
  content: string;
  excerpt: string;
  suggested_category: number;
  category_name: string;
  images: string[];
  featured_image: string;
  status: string;
  created_at: string;
}

interface Stats {
  pending: number;
  approved: number;
  rejected: number;
  published: number;
  total: number;
}

export default function PendingArticlesPage() {
  const [articles, setArticles] = useState<PendingArticle[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'pending' | 'all'>('pending');
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [processing, setProcessing] = useState<number | null>(null);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    fetchData();
  }, [filter]);

  const fetchData = async () => {
    try {
      const apiUrl = getApiUrl();
      const token = localStorage.getItem('access_token');
      const headers = { 'Authorization': `Bearer ${token}` };

      const [articlesRes, statsRes] = await Promise.all([
        fetch(`${apiUrl}/pending-articles/?status=${filter === 'pending' ? 'pending' : ''}`, { headers }),
        fetch(`${apiUrl}/pending-articles/stats/`, { headers })
      ]);

      if (articlesRes.ok) {
        const data = await articlesRes.json();
        setArticles(Array.isArray(data) ? data : data.results || []);
      }

      if (statsRes.ok) {
        setStats(await statsRes.json());
      }
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (id: number) => {
    setProcessing(id);
    try {
      const apiUrl = getApiUrl();
      const token = localStorage.getItem('access_token');

      const response = await fetch(`${apiUrl}/pending-articles/${id}/approve/`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        const data = await response.json();
        setMessage({ type: 'success', text: `Article published! Slug: ${data.article_slug}` });
        setArticles(articles.filter(a => a.id !== id));
        if (stats) setStats({ ...stats, pending: stats.pending - 1, published: stats.published + 1 });
      } else {
        const data = await response.json();
        setMessage({ type: 'error', text: data.error || 'Failed to approve' });
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'An error occurred' });
    } finally {
      setProcessing(null);
    }
  };

  const handleReject = async (id: number) => {
    const reason = prompt('Reason for rejection (optional):');

    setProcessing(id);
    try {
      const apiUrl = getApiUrl();
      const token = localStorage.getItem('access_token');

      const response = await fetch(`${apiUrl}/pending-articles/${id}/reject/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ reason: reason || '' })
      });

      if (response.ok) {
        setMessage({ type: 'success', text: 'Article rejected' });
        setArticles(articles.filter(a => a.id !== id));
        if (stats) setStats({ ...stats, pending: stats.pending - 1, rejected: stats.rejected + 1 });
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'An error occurred' });
    } finally {
      setProcessing(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="animate-spin text-purple-600" size={48} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link
          href="/admin/youtube-channels"
          className="flex items-center gap-2 p-2 px-3 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <ArrowLeft size={20} />
          <span className="font-medium">Back to Channels</span>
        </Link>
        <div>
          <h1 className="text-2xl sm:text-3xl font-black text-gray-950">Pending Articles</h1>
          <p className="text-gray-500 text-sm">Статьи ожидающие проверки и публикации</p>
        </div>
      </div>

      {message && (
        <div className={`p-4 rounded-lg ${message.type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'
          }`}>
          {message.text}
        </div>
      )}

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="bg-orange-50 rounded-xl p-4 border border-orange-200">
            <p className="text-3xl font-black text-orange-600">{stats.pending}</p>
            <p className="text-orange-700 text-sm">Pending</p>
          </div>
          <div className="bg-green-50 rounded-xl p-4 border border-green-200">
            <p className="text-3xl font-black text-green-600">{stats.published}</p>
            <p className="text-green-700 text-sm">Published</p>
          </div>
          <div className="bg-red-50 rounded-xl p-4 border border-red-200">
            <p className="text-3xl font-black text-red-600">{stats.rejected}</p>
            <p className="text-red-700 text-sm">Rejected</p>
          </div>
          <div className="bg-gray-50 rounded-xl p-4 border border-gray-200">
            <p className="text-3xl font-black text-gray-600">{stats.total}</p>
            <p className="text-gray-700 text-sm">Total</p>
          </div>
        </div>
      )}

      {/* Filter */}
      <div className="flex gap-2">
        <button
          onClick={() => setFilter('pending')}
          className={`px-4 py-2 rounded-lg text-sm font-medium ${filter === 'pending'
            ? 'bg-orange-600 text-white'
            : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
        >
          Pending Only
        </button>
        <button
          onClick={() => setFilter('all')}
          className={`px-4 py-2 rounded-lg text-sm font-medium ${filter === 'all'
            ? 'bg-purple-600 text-white'
            : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
        >
          All Articles
        </button>
      </div>

      {/* Articles List */}
      <div className="space-y-4">
        {articles.length > 0 ? (
          articles.map((article) => (
            <div key={article.id} className="bg-white rounded-xl shadow-md overflow-hidden">
              {/* Header */}
              <div className="p-4 sm:p-6 border-b border-gray-100">
                <div className="flex flex-col sm:flex-row sm:items-start gap-4">
                  {/* Thumbnail */}
                  {article.featured_image && (
                    <img
                      src={(() => {
                        const url = article.featured_image;
                        if (!url) return '';
                        if (url.startsWith('http')) return url;
                        // Determine API URL for media
                        const apiUrl = getApiUrl().replace('/api/v1', '');
                        return `${apiUrl}${url.startsWith('/') ? '' : '/'}${url}`;
                      })()}
                      alt=""
                      className="w-full sm:w-40 h-24 object-cover rounded-lg"
                    />
                  )}

                  <div className="flex-1">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <h3 className="font-bold text-gray-900 text-lg">{article.title}</h3>
                        <div className="flex flex-wrap items-center gap-2 mt-2 text-sm">
                          <span className="flex items-center gap-1 text-gray-500">
                            <Youtube size={14} className="text-red-600" />
                            {article.channel_name}
                          </span>
                          {article.category_name && (
                            <span className="px-2 py-0.5 bg-purple-100 text-purple-700 rounded text-xs">
                              {article.category_name}
                            </span>
                          )}
                          <span className="flex items-center gap-1 text-gray-400">
                            <Clock size={14} />
                            {new Date(article.created_at).toLocaleDateString()}
                          </span>
                        </div>
                      </div>

                      {/* Status Badge */}
                      <span className={`px-3 py-1 rounded-full text-xs font-bold ${article.status === 'pending' ? 'bg-orange-100 text-orange-700' :
                        article.status === 'published' ? 'bg-green-100 text-green-700' :
                          article.status === 'rejected' ? 'bg-red-100 text-red-700' :
                            'bg-gray-100 text-gray-700'
                        }`}>
                        {article.status}
                      </span>
                    </div>

                    {/* Actions */}
                    {article.status === 'pending' && (
                      <div className="flex flex-wrap gap-2 mt-4">
                        <button
                          onClick={() => handleApprove(article.id)}
                          disabled={processing === article.id}
                          className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 text-sm font-medium"
                        >
                          {processing === article.id ? (
                            <Loader2 className="animate-spin" size={16} />
                          ) : (
                            <Check size={16} />
                          )}
                          Approve & Publish
                        </button>
                        <button
                          onClick={() => handleReject(article.id)}
                          disabled={processing === article.id}
                          className="flex items-center gap-2 px-4 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 disabled:opacity-50 text-sm font-medium"
                        >
                          <X size={16} />
                          Reject
                        </button>
                        <button
                          onClick={() => setExpandedId(expandedId === article.id ? null : article.id)}
                          className="flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 text-sm font-medium"
                        >
                          <Eye size={16} />
                          Preview
                          {expandedId === article.id ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                        </button>
                        <a
                          href={article.video_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-2 px-4 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 text-sm font-medium"
                        >
                          <Youtube size={16} />
                          Watch Video
                        </a>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Expanded Content Preview */}
              {expandedId === article.id && (
                <div className="p-4 sm:p-6 bg-gray-50 border-t border-gray-100">
                  <h4 className="font-bold text-gray-700 mb-2">Article Preview:</h4>
                  <div className="prose prose-sm max-w-none">
                    {article.excerpt && (
                      <p className="text-gray-600 italic mb-4">{article.excerpt}</p>
                    )}
                    <div
                      className="text-gray-800 max-h-96 overflow-y-auto"
                      dangerouslySetInnerHTML={{ __html: article.content.slice(0, 2000) + (article.content.length > 2000 ? '...' : '') }}
                    />
                  </div>

                  {/* Images */}
                  {article.images && article.images.length > 0 && (
                    <div className="mt-4">
                      <h4 className="font-bold text-gray-700 mb-2">Images ({article.images.length}):</h4>
                      <div className="flex flex-wrap gap-2">
                        {article.images.slice(0, 4).map((img, idx) => (
                          <img
                            key={idx}
                            src={(() => {
                              if (!img) return '';
                              if (img.startsWith('http')) return img;
                              const apiUrl = getApiUrl().replace('/api/v1', '');
                              return `${apiUrl}${img.startsWith('/') ? '' : '/'}${img}`;
                            })()}
                            alt=""
                            className="w-24 h-16 object-cover rounded"
                          />
                        ))}
                        {article.images.length > 4 && (
                          <div className="w-24 h-16 bg-gray-200 rounded flex items-center justify-center text-gray-500 text-sm">
                            +{article.images.length - 4} more
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))
        ) : (
          <div className="bg-white rounded-xl shadow-md p-12 text-center">
            <FileText className="mx-auto mb-4 text-gray-300" size={48} />
            <p className="text-gray-500">
              {filter === 'pending' ? 'No pending articles' : 'No articles found'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
