import { ArticleGridSkeleton } from '@/components/public/Skeletons';

export default function Loading() {
  return (
    <div className="min-h-screen bg-gray-50 py-12">
      <div className="container mx-auto px-4">
        <div className="h-10 bg-gray-300 rounded w-64 mb-8 animate-pulse" />
        <ArticleGridSkeleton count={9} />
      </div>
    </div>
  );
}
