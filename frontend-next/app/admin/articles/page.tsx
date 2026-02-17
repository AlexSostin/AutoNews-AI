'use client';

import { useState, useEffect } from 'react';
import { Plus, Edit, Trash2, Eye, Search, Zap, Loader2, X } from 'lucide-react';
import Link from 'next/link';
import api from '@/lib/api';

interface Article {
  id: number;
  title: string;
  slug: string;
  category_names: string[];
  is_published: boolean;
  is_hero: boolean;
  created_at: string;
  average_rating: number;
  image?: string;
}

interface PaginationInfo {
  count: number;
  next: string | null;
  previous: string | null;
}

export default function ArticlesPage() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [filter, setFilter] = useState<'all' | 'published' | 'draft'>('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(20);
  const [pagination, setPagination] = useState<PaginationInfo>({ count: 0, next: null, previous: null });
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [bulkEnriching, setBulkEnriching] = useState(false);
  const [bulkResults, setBulkResults] = useState<any>(null);
  const [enrichProgress, setEnrichProgress] = useState<{ current: number; total: number } | null>(null);

  const handleBulkEnrich = async (mode: 'missing' | 'all') => {
    const label = mode === 'missing' ? 'articles missing enrichment' : 'ALL published articles';
    if (!confirm(`Run AI enrichment on ${label}?\n\nThis will:\n• Generate VehicleSpecs (Deep Specs)\n• Create A/B title variants\n• Run smart tag matching\n• Search web for latest specs\n\nThis may take several minutes for many articles.`)) return;

    setBulkEnriching(true);
    setBulkResults(null);
    setEnrichProgress(null);

    try {
      // Use native fetch for SSE streaming (axios doesn't support streams)
      const { getApiUrl } = await import('@/lib/api');
      const apiBase = getApiUrl();
      const token = document.cookie
        .split('; ')
        .find(row => row.startsWith('access_token='))
        ?.split('=')[1];

      const response = await fetch(`${apiBase}/articles/bulk-re-enrich/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ mode }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No response body');

      const decoder = new TextDecoder();
      let buffer = '';
      const streamedResults: any[] = [];
      let finalData: any = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Parse SSE events from buffer
        const events = buffer.split('\n\n');
        buffer = events.pop() || ''; // Keep incomplete event in buffer

        for (const event of events) {
          const dataLine = event.trim();
          if (!dataLine.startsWith('data: ')) continue;
          try {
            const data = JSON.parse(dataLine.slice(6));

            if (data.type === 'init') {
              setEnrichProgress({ current: 0, total: data.total });
            } else if (data.type === 'progress') {
              setEnrichProgress({ current: data.current, total: data.total });
              streamedResults.push(data.article);
              // Update results live
              setBulkResults({
                success: true,
                message: `Processing ${data.current}/${data.total}...`,
                processed: data.current,
                success_count: streamedResults.filter((r: any) => !r.errors?.length).length,
                error_count: streamedResults.filter((r: any) => r.errors?.length).length,
                elapsed_seconds: '...',
                results: [...streamedResults],
              });
            } else if (data.type === 'done') {
              finalData = data;
            }
          } catch {
            // Skip malformed events
          }
        }
      }

      // Set final results
      if (finalData) {
        setBulkResults({
          ...finalData,
          success: true,
          results: streamedResults,
        });
        setSuccessMessage(finalData.message);
        setTimeout(() => setSuccessMessage(null), 5000);
      }
    } catch (err: any) {
      setBulkResults({ success: false, message: err.message || 'Network Error' });
    } finally {
      setBulkEnriching(false);
      setEnrichProgress(null);
    }
  };

  useEffect(() => {
    fetchArticles();
  }, [filter, currentPage, itemsPerPage, searchTerm]);

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearchTerm(searchInput);
      setCurrentPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchInput]);

  const fetchArticles = async () => {
    try {
      setLoading(true);
      const params: any = {
        page: currentPage,
        page_size: itemsPerPage
      };
      if (filter !== 'all') {
        params.is_published = filter === 'published' ? 'true' : 'false';
      }
      if (searchTerm.trim()) {
        params.search = searchTerm.trim();
      }
      const response = await api.get('/articles/', { params });
      setArticles(response.data.results || response.data);
      if (response.data.count !== undefined) {
        setPagination({
          count: response.data.count,
          next: response.data.next,
          previous: response.data.previous
        });
      }
    } catch (error) {
      console.error('Failed to fetch articles:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this article?')) return;

    setDeletingId(id);
    try {
      await api.delete(`/articles/${id}/`);
      setArticles(prev => prev.filter(a => a.id !== id));
      setSuccessMessage('Article deleted successfully');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (error) {
      console.error('Failed to delete article:', error);
      alert('Failed to delete article');
    } finally {
      setDeletingId(null);
    }
  };

  const handleTogglePublish = async (id: number, currentStatus: boolean) => {
    try {
      console.log('🔄 Toggle publish status:', { id, currentStatus, newStatus: !currentStatus });

      // Optimistic update
      setArticles(articles.map(a =>
        a.id === id ? { ...a, is_published: !currentStatus } : a
      ));

      const response = await api.patch(`/articles/${id}/`, { is_published: !currentStatus });
      console.log('✅ Update successful:', response.data);
    } catch (error: any) {
      console.error('❌ Failed to update published status:', error);
      console.error('Error details:', error.response?.data || error.message);
      alert('Failed to update status: ' + (error.response?.data?.detail || error.message));
      // Revert on error
      setArticles(articles.map(a =>
        a.id === id ? { ...a, is_published: currentStatus } : a
      ));
    }
  };


  const handleToggleHero = async (id: number, currentStatus: boolean) => {
    try {
      // Optimistic update
      setArticles(articles.map(a =>
        a.id === id ? { ...a, is_hero: !currentStatus } : a
      ));

      await api.patch(`/articles/${id}/`, { is_hero: !currentStatus });
    } catch (error: any) {
      console.error('Failed to update hero status:', error);
      alert('Failed to update status: ' + (error.response?.data?.detail || error.message));
      // Revert on error
      setArticles(articles.map(a =>
        a.id === id ? { ...a, is_hero: currentStatus } : a
      ));
    }
  };

  // All filtering is done server-side now

  return (
    <div>
      {/* Success Toast */}
      {successMessage && (
        <div className="fixed top-4 right-4 z-50 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg font-semibold flex items-center gap-2 animate-pulse">
          ✓ {successMessage}
        </div>
      )}
      {/* Bulk Enrich Results Modal */}
      {bulkResults && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setBulkResults(null)}>
          <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between p-5 border-b border-gray-100">
              <div>
                <h3 className="text-lg font-black text-gray-900">⚡ Bulk Enrichment {enrichProgress ? 'Progress' : 'Results'}</h3>
                <p className="text-sm text-gray-500 font-medium mt-1">{bulkResults.message}</p>
              </div>
              {!enrichProgress && (
                <button onClick={() => setBulkResults(null)} className="p-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors" title="Close">
                  <X size={22} className="text-gray-600" />
                </button>
              )}
            </div>
            {enrichProgress && (
              <div className="px-5 pt-4">
                <div className="flex items-center justify-between text-sm font-bold text-gray-700 mb-2">
                  <span>Processing article {enrichProgress.current} of {enrichProgress.total}</span>
                  <span className="text-emerald-600">{enrichProgress.total > 0 ? Math.round((enrichProgress.current / enrichProgress.total) * 100) : 0}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                  <div
                    className="bg-gradient-to-r from-emerald-500 to-teal-500 h-3 rounded-full transition-all duration-300 ease-out"
                    style={{ width: `${enrichProgress.total > 0 ? (enrichProgress.current / enrichProgress.total) * 100 : 0}%` }}
                  />
                </div>
              </div>
            )}
            <div className="p-5 overflow-y-auto max-h-[60vh] space-y-3">
              {bulkResults.processed > 0 && (
                <div className="grid grid-cols-3 gap-3 mb-4">
                  <div className="bg-green-50 rounded-lg p-3 text-center">
                    <p className="text-2xl font-black text-green-700">{bulkResults.success_count}</p>
                    <p className="text-xs font-semibold text-green-600">Success</p>
                  </div>
                  <div className="bg-red-50 rounded-lg p-3 text-center">
                    <p className="text-2xl font-black text-red-700">{bulkResults.error_count}</p>
                    <p className="text-xs font-semibold text-red-600">Errors</p>
                  </div>
                  <div className="bg-blue-50 rounded-lg p-3 text-center">
                    <p className="text-2xl font-black text-blue-700">{bulkResults.elapsed_seconds}s</p>
                    <p className="text-xs font-semibold text-blue-600">Duration</p>
                  </div>
                </div>
              )}
              {bulkResults.results?.map((r: any) => (
                <div key={r.id} className={`border rounded-lg p-3 ${r.errors?.length ? 'border-red-200 bg-red-50/50' : 'border-green-200 bg-green-50/50'}`}>
                  <p className="font-bold text-gray-900 text-sm truncate">#{r.id} {r.title}</p>
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {Object.entries(r.steps || {}).map(([key, val]: [string, any]) => (
                      <span key={key} className={`px-2 py-0.5 rounded-full text-xs font-semibold ${val === true ? 'bg-green-100 text-green-700' :
                        val === 'skipped' ? 'bg-gray-100 text-gray-500' :
                          typeof val === 'number' ? 'bg-blue-100 text-blue-700' :
                            'bg-red-100 text-red-700'
                        }`}>
                        {key.replace('_', ' ')}: {val === true ? '✅' : val === 'skipped' ? '⏭️' : typeof val === 'number' ? `+${val}` : '❌'}
                      </span>
                    ))}
                  </div>
                  {r.errors?.length > 0 && (
                    <p className="text-xs text-red-600 mt-1.5 font-medium">{r.errors.join(', ')}</p>
                  )}
                </div>
              ))}
            </div>
            <div className="p-4 border-t border-gray-100 flex justify-end">
              <button
                onClick={() => setBulkResults(null)}
                className="px-6 py-2.5 bg-gray-900 text-white rounded-lg font-bold hover:bg-gray-800 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl sm:text-3xl font-black text-gray-950">Articles</h1>
        <div className="flex items-center gap-2">
          <div className="relative group">
            <button
              onClick={() => handleBulkEnrich('missing')}
              disabled={bulkEnriching}
              className="bg-gradient-to-r from-emerald-600 to-teal-600 text-white px-3 sm:px-4 py-3 rounded-lg font-bold hover:from-emerald-700 hover:to-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center gap-2 shadow-md"
            >
              {bulkEnriching ? <Loader2 size={18} className="animate-spin" /> : <Zap size={18} />}
              <span className="hidden sm:inline">{bulkEnriching ? 'Enriching...' : 'Bulk Enrich'}</span>
            </button>
            {!bulkEnriching && (
              <div className="absolute right-0 top-full pt-1 hidden group-hover:block z-20">
                <div className="bg-white rounded-lg shadow-xl border border-gray-200 py-1 min-w-[180px]">
                  <button
                    onClick={() => handleBulkEnrich('missing')}
                    className="w-full px-4 py-2 text-left text-sm font-semibold text-gray-700 hover:bg-emerald-50 hover:text-emerald-700 transition-colors"
                  >
                    🔍 Enrich Missing Only
                  </button>
                  <button
                    onClick={() => handleBulkEnrich('all')}
                    className="w-full px-4 py-2 text-left text-sm font-semibold text-gray-700 hover:bg-amber-50 hover:text-amber-700 transition-colors"
                  >
                    🌐 Re-Enrich All Articles
                  </button>
                </div>
              </div>
            )}
          </div>
          <Link
            href="/admin/articles/new"
            className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white px-4 sm:px-6 py-3 rounded-lg font-bold hover:from-indigo-700 hover:to-purple-700 transition-all flex items-center gap-2 shadow-md"
          >
            <Plus size={20} />
            <span className="hidden sm:inline">New Article</span>
          </Link>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow-md p-4 mb-6">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
              <input
                type="text"
                placeholder="Search articles..."
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-gray-900"
              />
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setFilter('all')}
              className={`px-3 sm:px-4 py-2 rounded-lg font-medium transition-all whitespace-nowrap ${filter === 'all'
                ? 'bg-indigo-600 text-white shadow-md'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
            >
              All
            </button>
            <button
              onClick={() => setFilter('published')}
              className={`px-3 sm:px-4 py-2 rounded-lg font-medium transition-all whitespace-nowrap ${filter === 'published'
                ? 'bg-green-600 text-white shadow-md'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
            >
              Published
            </button>
            <button
              onClick={() => setFilter('draft')}
              className={`px-3 sm:px-4 py-2 rounded-lg font-medium transition-all whitespace-nowrap ${filter === 'draft'
                ? 'bg-amber-600 text-white shadow-md'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
            >
              Drafts
            </button>
          </div>
        </div>
      </div>

      {/* Articles Table */}
      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        {loading ? (
          <div className="p-12 text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
            <p className="text-gray-600 mt-4 font-medium">Loading articles...</p>
          </div>
        ) : articles.length === 0 ? (
          <div className="p-12 text-center">
            <div className="text-6xl mb-4">📝</div>
            <p className="text-gray-700 font-semibold text-lg mb-2">No articles found</p>
            <p className="text-gray-600">
              {searchTerm ? 'Try adjusting your search' : 'Create your first article to get started'}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full table-fixed">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="w-16 px-2 py-3 text-left text-xs font-bold text-gray-900 uppercase tracking-wider">
                    Image
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-bold text-gray-900 uppercase tracking-wider">
                    Title
                  </th>
                  <th className="w-28 px-3 py-3 text-left text-xs font-bold text-gray-900 uppercase tracking-wider">
                    Category
                  </th>
                  <th className="w-32 px-3 py-3 text-left text-xs font-bold text-gray-900 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="w-24 px-3 py-3 text-left text-xs font-bold text-gray-900 uppercase tracking-wider hidden xl:table-cell">
                    Hero
                  </th>
                  <th className="w-20 px-3 py-3 text-left text-xs font-bold text-gray-900 uppercase tracking-wider hidden xl:table-cell">
                    Rating
                  </th>
                  <th className="w-24 px-3 py-3 text-left text-xs font-bold text-gray-900 uppercase tracking-wider">
                    Date
                  </th>
                  <th className="w-28 px-2 py-3 text-right text-xs font-bold text-gray-900 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {articles.map((article) => (
                  <tr key={article.id} className={`hover:bg-gray-50 transition-colors ${deletingId === article.id ? 'opacity-50' : ''}`}>
                    <td className="px-2 py-3">
                      <div className="w-14 h-14 rounded-lg overflow-hidden bg-gray-100 flex items-center justify-center">
                        {article.image ? (
                          <img
                            src={article.image}
                            alt={article.title}
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <span className="text-gray-400 text-xs">—</span>
                        )}
                      </div>
                    </td>
                    <td className="px-3 py-3">
                      <div className="font-bold text-gray-900 truncate text-sm" title={article.title}>{article.title}</div>
                      <div className="text-xs text-gray-600 font-medium truncate">{article.slug}</div>
                    </td>
                    <td className="px-3 py-3">
                      <span className="px-2 py-1 bg-indigo-100 text-indigo-700 rounded-full text-xs font-semibold truncate block">
                        {article.category_names?.join(', ') || 'None'}
                      </span>
                    </td>
                    <td className="px-3 py-3">
                      <label className="flex items-center gap-1.5 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={article.is_published}
                          onChange={() => handleTogglePublish(article.id, article.is_published)}
                          className="w-4 h-4 text-indigo-600 rounded focus:ring-indigo-500 border-gray-300"
                        />
                        {/* Show real visibility status: published + has category */}
                        {article.is_published && article.category_names && article.category_names.length > 0 ? (
                          <span className="px-1.5 py-0.5 rounded-full text-xs font-semibold bg-green-100 text-green-700">
                            Live
                          </span>
                        ) : article.is_published ? (
                          <span className="px-1.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-700">
                            No Cat
                          </span>
                        ) : (
                          <span className="px-1.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-700">
                            Draft
                          </span>
                        )}
                      </label>
                    </td>
                    <td className="px-3 py-3 hidden xl:table-cell">
                      <label className="flex items-center gap-1.5 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={article.is_hero || false}
                          onChange={() => handleToggleHero(article.id, article.is_hero)}
                          className="w-4 h-4 text-purple-600 rounded focus:ring-purple-500 border-gray-300"
                        />
                        <span className={`px-1.5 py-0.5 rounded-full text-xs font-semibold ${article.is_hero
                          ? 'bg-purple-100 text-purple-700'
                          : 'bg-gray-100 text-gray-400'
                          }`}>
                          {article.is_hero ? 'Yes' : 'No'}
                        </span>
                      </label>
                    </td>
                    <td className="px-3 py-3 hidden xl:table-cell">
                      <div className="flex items-center gap-1">
                        <span className="text-amber-500 text-sm">★</span>
                        <span className="font-bold text-gray-900 text-sm">{article.average_rating.toFixed(1)}</span>
                      </div>
                    </td>
                    <td className="px-3 py-3 text-sm text-gray-700 font-medium whitespace-nowrap">
                      {new Date(article.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-2 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Link
                          href={`/articles/${article.slug}`}
                          target="_blank"
                          className="p-1.5 text-gray-600 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                          title="View"
                        >
                          <Eye size={16} />
                        </Link>
                        <Link
                          href={`/admin/articles/${article.id}/edit`}
                          className="p-1.5 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                          title="Edit"
                        >
                          <Edit size={16} />
                        </Link>
                        <button
                          onClick={() => handleDelete(article.id)}
                          disabled={deletingId === article.id}
                          className="p-1.5 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
                          title="Delete"
                        >
                          {deletingId === article.id ? (
                            <div className="w-4 h-4 border-2 border-red-400 border-t-transparent rounded-full animate-spin" />
                          ) : (
                            <Trash2 size={16} />
                          )}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination Controls */}
      <div className="mt-6 flex flex-col sm:flex-row items-center justify-between gap-4 bg-white rounded-lg shadow-md p-4">
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-600 font-medium">Items per page:</span>
          <select
            value={itemsPerPage}
            onChange={(e) => {
              setItemsPerPage(Number(e.target.value));
              setCurrentPage(1);
            }}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-gray-900 font-medium"
          >
            <option value={20}>20</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
        </div>

        <div className="text-sm text-gray-600 font-medium">
          Showing {((currentPage - 1) * itemsPerPage) + 1} - {Math.min(currentPage * itemsPerPage, pagination.count)} of {pagination.count} articles
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
            disabled={!pagination.previous}
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg font-medium hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            Previous
          </button>

          <div className="flex items-center gap-1">
            {Array.from({ length: Math.min(5, Math.ceil(pagination.count / itemsPerPage)) }, (_, i) => {
              const totalPages = Math.ceil(pagination.count / itemsPerPage);
              let pageNum;

              if (totalPages <= 5) {
                pageNum = i + 1;
              } else if (currentPage <= 3) {
                pageNum = i + 1;
              } else if (currentPage >= totalPages - 2) {
                pageNum = totalPages - 4 + i;
              } else {
                pageNum = currentPage - 2 + i;
              }

              return (
                <button
                  key={pageNum}
                  onClick={() => setCurrentPage(pageNum)}
                  className={`w-10 h-10 rounded-lg font-bold transition-all ${currentPage === pageNum
                    ? 'bg-indigo-600 text-white shadow-md'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                >
                  {pageNum}
                </button>
              );
            })}
          </div>

          <button
            onClick={() => setCurrentPage(prev => prev + 1)}
            disabled={!pagination.next}
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg font-medium hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
