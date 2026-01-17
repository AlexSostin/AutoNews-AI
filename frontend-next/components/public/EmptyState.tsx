'use client';

import Link from 'next/link';

export default function EmptyState() {
  const handleRetry = () => {
    window.location.reload();
  };

  return (
    <div className="text-center py-20 bg-white rounded-2xl shadow-sm border border-gray-100">
      <div className="text-6xl mb-4">📰</div>
      <p className="text-gray-600 text-lg mb-2">No articles available yet.</p>
      <p className="text-gray-400 text-sm mb-6">
        Make sure Django backend is running on port 8001
      </p>
      <div className="flex flex-col sm:flex-row gap-3 justify-center">
        <Link 
          href="/admin" 
          className="bg-indigo-600 text-white px-6 sm:px-8 py-3 rounded-full hover:bg-indigo-700 transition-colors inline-block font-semibold"
        >
          Go to Admin Panel
        </Link>
        <button 
          onClick={handleRetry}
          className="bg-gray-100 text-gray-700 px-6 sm:px-8 py-3 rounded-full hover:bg-gray-200 transition-colors inline-block font-semibold"
        >
          🔄 Retry Connection
        </button>
      </div>
    </div>
  );
}
