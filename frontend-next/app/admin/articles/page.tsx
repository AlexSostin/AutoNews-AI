'use client';

import { useState, useEffect } from 'react';
import { Plus, Edit, Trash2, Eye, Search } from 'lucide-react';
import Link from 'next/link';
import api from '@/lib/api';

interface Article {
  id: number;
  title: string;
  slug: string;
  category_name: string;
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
  const [filter, setFilter] = useState<'all' | 'published' | 'draft'>('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(20);
  const [pagination, setPagination] = useState<PaginationInfo>({ count: 0, next: null, previous: null });

  useEffect(() => {
    fetchArticles();
  }, [filter, currentPage, itemsPerPage]);

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

    try {
      await api.delete(`/articles/${id}/`);
      setArticles(articles.filter(a => a.id !== id));
    } catch (error) {
      console.error('Failed to delete article:', error);
      alert('Failed to delete article');
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

  const filteredArticles = articles.filter(article =>
    article.title.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl sm:text-3xl font-black text-gray-950">Articles</h1>
        <Link
          href="/admin/articles/new"
          className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white px-4 sm:px-6 py-3 rounded-lg font-bold hover:from-indigo-700 hover:to-purple-700 transition-all flex items-center gap-2 shadow-md"
        >
          <Plus size={20} />
          <span className="hidden sm:inline">New Article</span>
        </Link>
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
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
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
        ) : filteredArticles.length === 0 ? (
          <div className="p-12 text-center">
            <div className="text-6xl mb-4">📝</div>
            <p className="text-gray-700 font-semibold text-lg mb-2">No articles found</p>
            <p className="text-gray-600">
              {searchTerm ? 'Try adjusting your search' : 'Create your first article to get started'}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-4 text-left text-xs font-bold text-gray-900 uppercase tracking-wider">
                    Image
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-bold text-gray-900 uppercase tracking-wider">
                    Title
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-bold text-gray-900 uppercase tracking-wider">
                    Category
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-bold text-gray-900 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-bold text-gray-900 uppercase tracking-wider">
                    Hero
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-bold text-gray-900 uppercase tracking-wider">
                    Rating
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-bold text-gray-900 uppercase tracking-wider">
                    Date
                  </th>
                  <th className="px-6 py-4 text-right text-xs font-bold text-gray-900 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredArticles.map((article) => (
                  <tr key={article.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-4">
                      <div className="w-20 h-14 rounded-lg overflow-hidden bg-gray-100 flex items-center justify-center">
                        {article.image ? (
                          <img
                            src={article.image}
                            alt={article.title}
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <span className="text-gray-400 text-xs">No image</span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="font-bold text-gray-900">{article.title}</div>
                      <div className="text-sm text-gray-600 font-medium">{article.slug}</div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="px-3 py-1 bg-indigo-100 text-indigo-700 rounded-full text-sm font-semibold">
                        {article.category_name}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={article.is_published}
                          onChange={() => handleTogglePublish(article.id, article.is_published)}
                          className="w-5 h-5 text-indigo-600 rounded focus:ring-indigo-500 border-gray-300"
                        />
                        <span className={`px-2 py-1 rounded-full text-xs font-semibold ${article.is_published
                          ? 'bg-green-100 text-green-700'
                          : 'bg-amber-100 text-amber-700'
                          }`}>
                          {article.is_published ? 'Published' : 'Draft'}
                        </span>
                      </label>
                    </td>
                    <td className="px-6 py-4">
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={article.is_hero || false}
                          onChange={() => handleToggleHero(article.id, article.is_hero)}
                          className="w-5 h-5 text-purple-600 rounded focus:ring-purple-500 border-gray-300"
                        />
                        <span className={`px-2 py-1 rounded-full text-xs font-semibold ${article.is_hero
                          ? 'bg-purple-100 text-purple-700'
                          : 'bg-gray-100 text-gray-400'
                          }`}>
                          {article.is_hero ? 'Active' : 'No'}
                        </span>
                      </label>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-1">
                        <span className="text-amber-500">★</span>
                        <span className="font-bold text-gray-900">{article.average_rating.toFixed(1)}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-700 font-medium">
                      {new Date(article.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Link
                          href={`/articles/${article.slug}`}
                          target="_blank"
                          className="p-2 text-gray-600 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                          title="View"
                        >
                          <Eye size={18} />
                        </Link>
                        <Link
                          href={`/admin/articles/${article.id}/edit`}
                          className="p-2 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                          title="Edit"
                        >
                          <Edit size={18} />
                        </Link>
                        <button
                          onClick={() => handleDelete(article.id)}
                          className="p-2 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                          title="Delete"
                        >
                          <Trash2 size={18} />
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
