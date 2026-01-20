'use client';

import { useState, useEffect } from 'react';
import { MessageCircle, User, Mail, Send } from 'lucide-react';
import api from '@/lib/api';
import { getUserFromStorage, isAuthenticated } from '@/lib/auth';

interface Comment {
  id: number;
  author_name: string;
  author_email: string;
  content: string;
  created_at: string;
  is_approved: boolean;
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

  useEffect(() => {
    fetchComments();
    
    // Check if user is authenticated and pre-fill form
    const authCheck = isAuthenticated();
    console.log('Comment Section - Auth check:', authCheck);
    
    if (authCheck) {
      const user = getUserFromStorage();
      console.log('Comment Section - User data:', user);
      
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

  const fetchComments = async () => {
    try {
      const response = await api.get(`/comments/?article=${articleId}&is_approved=true`);
      setComments(response.data.results || response.data || []);
    } catch (error) {
      console.error('Failed to load comments:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setMessage('');

    try {
      await api.post('/comments/', {
        article: articleId,
        name: formData.author_name,
        email: formData.author_email,
        content: formData.content
      });

      setMessage('✓ Comment submitted! It will appear after moderation.');
      setFormData({ 
        author_name: isUserAuthenticated ? formData.author_name : '', 
        author_email: isUserAuthenticated ? formData.author_email : '', 
        content: '' 
      });
      setTimeout(() => setMessage(''), 5000);
    } catch (error: any) {
      console.error('Failed to submit comment:', error);
      const errorMsg = error.response?.data?.detail || error.response?.data?.error || 'Failed to submit comment. Please try again.';
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

      {/* Comment Form */}
      <div className="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-xl shadow-md p-6 mb-8 border-2 border-indigo-100">
        <h4 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
          <MessageCircle className="text-indigo-600" size={24} />
          Leave a Comment
        </h4>
        
        <form onSubmit={handleSubmit} className="space-y-4">
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

          {isUserAuthenticated && (
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
              rows={4}
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
            <p className={`text-sm font-medium ${
              message.includes('✓') ? 'text-green-600' : 'text-red-600'
            }`}>
              {message}
            </p>
          )}
        </form>
      </div>

      {/* Comments List */}
      {loading ? (
        <div className="text-center py-8 text-gray-500">Loading comments...</div>
      ) : comments.length > 0 ? (
        <div className="space-y-4">
          {comments.map((comment) => (
            <div
              key={comment.id}
              className="bg-white rounded-xl shadow-md p-6 border border-gray-100 hover:shadow-lg transition-shadow"
            >
              <div className="flex items-center gap-3 mb-3">
                <div className="w-12 h-12 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold text-xl">
                  {comment.author_name.charAt(0).toUpperCase()}
                </div>
                <div>
                  <h5 className="font-bold text-gray-900">{comment.author_name}</h5>
                  <p className="text-sm text-gray-500">
                    {formatDate(comment.created_at)}
                  </p>
                </div>
              </div>
              <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
                {comment.content}
              </p>
            </div>
          ))}
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
