'use client';

import { useState, useEffect } from 'react';
import { MessageCircle, User, Mail, Send, Reply, ChevronDown, ChevronUp } from 'lucide-react';
import api from '@/lib/api';
import { getUserFromStorage, isAuthenticated } from '@/lib/auth';

interface Comment {
  id: number;
  author_name: string;
  author_email: string;
  content: string;
  created_at: string;
  is_approved: boolean;
  parent: number | null;
  parent_author: string | null;
  replies_count: number;
  replies?: Comment[];
}

interface CommentSectionProps {
  articleId: number;
}

export default function CommentSection({ articleId }: CommentSectionProps) {
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState('');
  const [formData, setFormData] = useState({
    author_name: '',
    author_email: '',
    content: ''
  });
  const [isUserAuthenticated, setIsUserAuthenticated] = useState(false);
  const [replyingTo, setReplyingTo] = useState<number | null>(null);
  const [expandedReplies, setExpandedReplies] = useState<Set<number>>(new Set());

  useEffect(() => {
    fetchComments();

    const authCheck = isAuthenticated();
    if (authCheck) {
      const user = getUserFromStorage();
      if (user) {
        setIsUserAuthenticated(true);
        setFormData(prev => ({
          ...prev,
          author_name: user.username,
          author_email: user.email || ''
        }));
      }
    }
  }, [articleId]);

  // Helper to get API URL
  const getApiUrl = () => process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

  const fetchComments = async () => {
    try {
      // Use fetch instead of api.get to avoid sending auth token for public endpoint
      const response = await fetch(`${getApiUrl()}/comments/?article=${articleId}&is_approved=true`);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      setComments(data.results || data || []);
    } catch (error) {
      console.error('Failed to load comments:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchReplies = async (parentId: number) => {
    try {
      // Use fetch instead of api.get to avoid sending auth token for public endpoint
      const response = await fetch(`${getApiUrl()}/comments/?article=${articleId}&is_approved=true&include_replies=true&parent=${parentId}`);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      const replies = (data.results || data || []).filter((c: Comment) => c.parent === parentId);

      setComments(prevComments =>
        prevComments.map(comment =>
          comment.id === parentId
            ? { ...comment, replies }
            : comment
        )
      );
    } catch (error) {
      console.error('Failed to load replies:', error);
    }
  };

  const toggleReplies = async (commentId: number) => {
    const newExpanded = new Set(expandedReplies);

    if (newExpanded.has(commentId)) {
      newExpanded.delete(commentId);
    } else {
      newExpanded.add(commentId);
      const comment = comments.find(c => c.id === commentId);
      if (comment && !comment.replies) {
        await fetchReplies(commentId);
      }
    }

    setExpandedReplies(newExpanded);
  };

  const handleSubmit = async (e: React.FormEvent, parentId: number | null = null) => {
    e.preventDefault();
    setSubmitting(true);
    setMessage('');

    try {
      const commentData: any = {
        article: articleId,
        content: formData.content
      };

      if (parentId) {
        commentData.parent = parentId;
      }

      if (!isUserAuthenticated) {
        commentData.name = formData.author_name;
        commentData.email = formData.author_email;
      } else {
        if (formData.author_name.trim()) {
          commentData.name = formData.author_name.trim();
        }
        if (formData.author_email.trim()) {
          commentData.email = formData.author_email.trim();
        }
      }

      await api.post('/comments/', commentData);

      setMessage('✓ Comment submitted! It will appear after moderation.');
      setFormData({
        author_name: isUserAuthenticated ? formData.author_name : '',
        author_email: isUserAuthenticated ? formData.author_email : '',
        content: ''
      });
      setReplyingTo(null);
      setTimeout(() => setMessage(''), 5000);
    } catch (error: any) {
      console.error('Failed to submit comment:', error);

      let errorMsg = error.response?.data?.detail || error.response?.data?.error;

      if (!errorMsg && error.response?.data) {
        const fieldErrors = Object.values(error.response.data as Record<string, any[]>).flat();
        if (fieldErrors.length > 0) {
          errorMsg = fieldErrors.join(' ');
        }
      }

      if (!errorMsg) {
        errorMsg = 'Failed to submit comment. Please check your input.';
      }

      setMessage(`✗ ${errorMsg}`);
      setTimeout(() => setMessage(''), 5000);
    } finally {
      setSubmitting(false);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const renderCommentForm = (parentId: number | null = null, parentAuthor: string | null = null) => (
    <form onSubmit={(e) => handleSubmit(e, parentId)} className="space-y-4">
      {parentAuthor && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-indigo-700 font-medium">
            <Reply size={14} className="inline mr-1" />
            Replying to <strong>@{parentAuthor}</strong>
          </p>
          <button
            type="button"
            onClick={() => {
              setReplyingTo(null);
              setFormData(prev => ({ ...prev, content: '' }));
            }}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            Cancel
          </button>
        </div>
      )}

      {!isUserAuthenticated && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              <User size={16} className="inline mr-1" />
              Name *
            </label>
            <input
              type="text"
              value={formData.author_name}
              onChange={(e) => setFormData({ ...formData, author_name: e.target.value })}
              required
              className="w-full px-4 py-3 border-2 border-indigo-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none bg-white text-gray-900 placeholder-gray-700"
              placeholder="Your name"
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              <Mail size={16} className="inline mr-1" />
              Email * (won&apos;t be published)
            </label>
            <input
              type="email"
              value={formData.author_email}
              onChange={(e) => setFormData({ ...formData, author_email: e.target.value })}
              required
              className="w-full px-4 py-3 border-2 border-indigo-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none bg-white text-gray-900 placeholder-gray-700"
              placeholder="your@email.com"
            />
          </div>
        </div>
      )}

      {isUserAuthenticated && !parentId && (
        <div className="bg-indigo-100 border border-indigo-300 rounded-lg p-3 mb-2">
          <p className="text-sm text-indigo-800 font-medium">
            <User size={16} className="inline mr-1" />
            Commenting as: <strong>{formData.author_name}</strong>
          </p>
        </div>
      )}

      <div>
        <label className="block text-sm font-semibold text-gray-700 mb-2">
          Comment *
        </label>
        <textarea
          value={formData.content}
          onChange={(e) => setFormData({ ...formData, content: e.target.value })}
          required
          rows={parentId ? 3 : 4}
          className="w-full px-4 py-3 border-2 border-indigo-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none resize-none bg-white text-gray-900 placeholder-gray-700"
          placeholder="Share your thoughts..."
        />
      </div>

      <button
        type="submit"
        disabled={submitting}
        className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white px-6 py-3 rounded-lg font-semibold hover:from-indigo-700 hover:to-purple-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-lg"
      >
        <Send size={18} />
        {submitting ? 'Submitting...' : 'Submit Comment'}
      </button>

      {message && (
        <p className={`text-sm font-medium ${message.includes('✓') ? 'text-green-600' : 'text-red-600'
          }`}>
          {message}
        </p>
      )}
    </form>
  );

  const renderComment = (comment: Comment, isReply: boolean = false) => (
    <div
      key={comment.id}
      className={`${isReply ? 'ml-8 md:ml-12 bg-gray-50 border-l-4 border-indigo-300' : 'bg-white'
        } rounded-xl shadow-md p-6 border border-gray-100 hover:shadow-lg transition-shadow`}
    >
      <div className="flex items-center gap-3 mb-3">
        <div className={`w-${isReply ? '10' : '12'} h-${isReply ? '10' : '12'} rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold ${isReply ? 'text-base' : 'text-xl'
          }`}>
          {comment.author_name.charAt(0).toUpperCase()}
        </div>
        <div>
          <h5 className="font-bold text-gray-900">
            {comment.author_name}
            {comment.parent_author && isReply && (
              <span className="text-sm text-indigo-600 font-normal ml-2">
                → @{comment.parent_author}
              </span>
            )}
          </h5>
          <p className="text-sm text-gray-500">
            {formatDate(comment.created_at)}
          </p>
        </div>
      </div>

      <p className="text-gray-700 leading-relaxed whitespace-pre-wrap mb-3">
        {comment.content}
      </p>

      {!isReply && (
        <div className="flex items-center gap-4 border-t border-gray-200 pt-3 mt-3">
          <button
            onClick={() => setReplyingTo(comment.id)}
            className="text-sm text-indigo-600 hover:text-indigo-800 font-medium flex items-center gap-1"
          >
            <Reply size={16} />
            Reply
          </button>

          {comment.replies_count > 0 && (
            <button
              onClick={() => toggleReplies(comment.id)}
              className="text-sm text-gray-600 hover:text-gray-800 font-medium flex items-center gap-1"
            >
              {expandedReplies.has(comment.id) ? (
                <>
                  <ChevronUp size={16} />
                  Hide replies
                </>
              ) : (
                <>
                  <ChevronDown size={16} />
                  Show {comment.replies_count} {comment.replies_count === 1 ? 'reply' : 'replies'}
                </>
              )}
            </button>
          )}
        </div>
      )}

      {/* Reply Form */}
      {replyingTo === comment.id && (
        <div className="ml-8 md:ml-12 mt-4 p-4 bg-gradient-to-br from-indigo-50 to-purple-50 rounded-lg border-2 border-indigo-100">
          {renderCommentForm(comment.id, comment.author_name)}
        </div>
      )}

      {/* Nested Replies */}
      {!isReply && expandedReplies.has(comment.id) && comment.replies && (
        <div className="mt-4 space-y-3">
          {comment.replies.map(reply => renderComment(reply, true))}
        </div>
      )}
    </div>
  );

  return (
    <div className="mt-12">
      <div className="flex items-center gap-3 mb-6">
        <h3 className="text-2xl font-bold text-gray-900">
          💬 Comments
        </h3>
        <span className="bg-indigo-100 text-indigo-800 px-3 py-1 rounded-full text-sm font-semibold">
          {comments.length}
        </span>
      </div>

      {/* Main Comment Form */}
      <div className="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-xl shadow-md p-6 mb-8 border-2 border-indigo-100">
        <h4 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
          <MessageCircle className="text-indigo-600" size={24} />
          Leave a Comment
        </h4>
        {renderCommentForm()}
      </div>

      {/* Comments List */}
      {loading ? (
        <div className="text-center py-8 text-gray-500">Loading comments...</div>
      ) : comments.length > 0 ? (
        <div className="space-y-4">
          {comments.map((comment) => renderComment(comment))}
        </div>
      ) : (
        <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-8 text-center border-2 border-blue-100">
          <div className="text-6xl mb-4">💭</div>
          <h4 className="text-xl font-bold text-gray-900 mb-2">No comments yet</h4>
          <p className="text-gray-600">Be the first to share your thoughts!</p>
        </div>
      )}
    </div>
  );
}
