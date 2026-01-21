'use client';

export default function EmptyState() {
  return (
    <div className="text-center py-20 bg-white rounded-2xl shadow-sm border border-gray-100">
      <div className="text-6xl mb-4">📰</div>
      <p className="text-gray-600 text-lg mb-2">No articles available yet.</p>
      <p className="text-gray-400 text-sm">
        Check back soon for the latest automotive news and reviews.
      </p>
    </div>
  );
}
