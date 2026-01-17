export function ArticleCardSkeleton() {
  return (
    <div className="bg-white rounded-xl shadow-md overflow-hidden animate-pulse">
      <div className="relative h-48 bg-gray-300" />
      <div className="p-6">
        <div className="h-4 bg-gray-300 rounded w-20 mb-3" />
        <div className="h-6 bg-gray-300 rounded mb-3" />
        <div className="h-4 bg-gray-300 rounded mb-2" />
        <div className="h-4 bg-gray-300 rounded w-5/6 mb-4" />
        <div className="flex items-center justify-between">
          <div className="h-4 bg-gray-300 rounded w-24" />
          <div className="h-4 bg-gray-300 rounded w-16" />
        </div>
      </div>
    </div>
  );
}

export function ArticleGridSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
      {Array.from({ length: count }).map((_, i) => (
        <ArticleCardSkeleton key={i} />
      ))}
    </div>
  );
}

export function ArticleDetailSkeleton() {
  return (
    <div className="animate-pulse">
      {/* Hero */}
      <div className="relative h-[500px] bg-gray-300 mb-8" />
      
      <div className="container mx-auto px-4 py-12">
        <div className="max-w-4xl mx-auto">
          {/* Meta */}
          <div className="bg-white rounded-xl shadow-md p-6 mb-8">
            <div className="flex gap-6">
              <div className="h-4 bg-gray-300 rounded w-32" />
              <div className="h-4 bg-gray-300 rounded w-32" />
              <div className="h-4 bg-gray-300 rounded w-32" />
            </div>
          </div>

          {/* Content */}
          <div className="bg-white rounded-xl shadow-md p-8 mb-8">
            <div className="space-y-3">
              <div className="h-4 bg-gray-300 rounded" />
              <div className="h-4 bg-gray-300 rounded" />
              <div className="h-4 bg-gray-300 rounded w-5/6" />
              <div className="h-4 bg-gray-300 rounded" />
              <div className="h-4 bg-gray-300 rounded" />
              <div className="h-4 bg-gray-300 rounded w-4/6" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export function CategorySkeleton() {
  return (
    <div className="inline-block animate-pulse">
      <div className="h-10 bg-gray-300 rounded-full w-32" />
    </div>
  );
}

export function CommentSkeleton() {
  return (
    <div className="bg-white rounded-lg p-4 animate-pulse">
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-full bg-gray-300" />
        <div className="flex-1">
          <div className="h-4 bg-gray-300 rounded w-32 mb-2" />
          <div className="h-4 bg-gray-300 rounded w-full mb-2" />
          <div className="h-4 bg-gray-300 rounded w-5/6" />
        </div>
      </div>
    </div>
  );
}
