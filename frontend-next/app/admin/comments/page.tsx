'use client';

import { useState, useEffect } from 'react';
import { CheckCircle, XCircle, Trash2, MessageSquare } from 'lucide-react';
import Link from 'next/link';
import api from '@/lib/api';

interface Comment {
  id: number;
  article_title: string;
  article_slug: string;
  author_name: string;
  author_email: string;
  content: string;
  approved: boolean;
  created_at: string;
}

export default function CommentsPage() {
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'pending' | 'approved'>('pending');

  useEffect(() => {
    fetchComments();
  }, [filter]);

  const fetchComments = async () => {
    try {
      setLoading(true);
      const params: any = { page_size: 100 };
      if (filter !== 'all') {
        params.approved = filter === 'approved' ? 'true' : 'false';
      }
      const response = await api.get('/comments/', { params });
      setComments(response.data.results || response.data);
    } catch (error) {
      console.error('Failed to fetch comments:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (id: number) => {
    try {
      await api.patch(`/comments/${id}/`, { approved: true });
      setComments(comments.map(c => c.id === id ? { ...c, approved: true } : c));
    } catch (error) {
      console.error('Failed to approve comment:', error);
      alert('Failed to approve comment');
    }
  };

  const handleReject = async (id: number) => {
    try {
      await api.patch(`/comments/${id}/`, { approved: false });
      setComments(comments.map(c => c.id === id ? { ...c, approved: false } : c));
    } catch (error) {
      console.error('Failed to reject comment:', error);
      alert('Failed to reject comment');
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this comment?')) return;

    try {
      await api.delete(`/comments/${id}/`);
      setComments(comments.filter(c => c.id !== id));
    } catch (error) {
      console.error('Failed to delete comment:', error);
      alert('Failed to delete comment');
    }
  };

  const pendingCount = comments.filter(c => !c.approved).length;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-black text-gray-950">Comments Moderation</h1>
          {pendingCount > 0 && (
            <p className="text-amber-600 font-bold mt-2">
              {pendingCount} comment{pendingCount !== 1 ? 's' : ''} awaiting moderation
            </p>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow-md p-4 mb-6">
        <div className="flex gap-2">
          <button
            onClick={() => setFilter('all')}
            className={`px-4 py-2 rounded-lg font-medium transition-all ${
              filter === 'all'
                ? 'bg-indigo-600 text-white shadow-md'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            All
          </button>
          <button
            onClick={() => setFilter('pending')}
            className={`px-4 py-2 rounded-lg font-medium transition-all ${
              filter === 'pending'
                ? 'bg-amber-600 text-white shadow-md'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Pending {pendingCount > 0 && `(${pendingCount})`}
          </button>
          <button
            onClick={() => setFilter('approved')}
            className={`px-4 py-2 rounded-lg font-medium transition-all ${
              filter === 'approved'
                ? 'bg-green-600 text-white shadow-md'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Approved
          </button>
        </div>
      </div>

      {/* Comments List */}
      <div className="space-y-4">
        {loading ? (
          <div className="bg-white rounded-lg shadow-md p-12 text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
            <p className="text-gray-600 mt-4 font-medium">Loading comments...</p>
          </div>
        ) : comments.length === 0 ? (
          <div className="bg-white rounded-lg shadow-md p-12 text-center">
            <MessageSquare size={48} className="mx-auto text-gray-400 mb-4" />
            <p className="text-gray-700 font-semibold text-lg">No comments found</p>
            <p className="text-gray-600 mt-2">
              {filter === 'pending' ? 'No comments awaiting moderation' : 'No comments yet'}
            </p>
          </div>
        ) : (
          comments.map((comment) => (
            <div
              key={comment.id}
              className={`bg-white rounded-lg shadow-md p-6 border-l-4 ${
                comment.approved
                  ? 'border-green-500'
                  : 'border-amber-500'
              }`}
            >
              <div className="flex items-start justify-between gap-4 mb-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="font-black text-gray-950">{comment.author_name}</h3>
                    <span className="text-sm text-gray-600 font-medium">{comment.author_email}</span>
                    {comment.approved ? (
                      <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-xs font-bold">
                        Approved
                      </span>
                    ) : (
                      <span className="px-3 py-1 bg-amber-100 text-amber-700 rounded-full text-xs font-bold">
                        Pending
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-gray-600 font-medium mb-3">
                    On article:{' '}
                    <Link
                      href={`/articles/${comment.article_slug}`}
                      target="_blank"
                      className="text-indigo-600 hover:underline font-bold"
                    >
                      {comment.article_title}
                    </Link>
                  </p>
                  <p className="text-gray-800 font-medium">{comment.content}</p>
                  <p className="text-xs text-gray-500 mt-2 font-medium">
                    {new Date(comment.created_at).toLocaleString()}
                  </p>
                </div>
              </div>

              <div className="flex gap-2 pt-4 border-t border-gray-200">
                {!comment.approved ? (
                  <button
                    onClick={() => handleApprove(comment.id)}
                    className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors flex items-center gap-2 font-bold shadow-md"
                  >
                    <CheckCircle size={18} />
                    Approve
                  </button>
                ) : (
                  <button
                    onClick={() => handleReject(comment.id)}
                    className="px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 transition-colors flex items-center gap-2 font-bold shadow-md"
                  >
                    <XCircle size={18} />
                    Unapprove
                  </button>
                )}
                <button
                  onClick={() => handleDelete(comment.id)}
                  className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center gap-2 font-bold shadow-md"
                >
                  <Trash2 size={18} />
                  Delete
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      <div className="mt-4 text-sm text-gray-600 font-medium">
        Showing {comments.length} comment{comments.length !== 1 ? 's' : ''}
      </div>
    </div>
  );
}
