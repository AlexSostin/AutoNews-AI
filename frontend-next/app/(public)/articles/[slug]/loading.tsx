export default function ArticleLoading() {
  return (
    <main className="flex-1 bg-gradient-to-b from-gray-50 to-white">
      {/* Hero skeleton */}
      <div className="relative w-full h-[50vh] md:h-[60vh] bg-gray-200 animate-pulse">
        <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/30 to-transparent" />
        <div className="absolute bottom-0 left-0 right-0 p-6 md:p-12">
          <div className="max-w-4xl mx-auto space-y-4">
            <div className="h-6 w-24 bg-white/20 rounded-full" />
            <div className="h-10 w-3/4 bg-white/20 rounded-lg" />
            <div className="h-6 w-1/2 bg-white/20 rounded-lg" />
          </div>
        </div>
      </div>

      {/* Content skeleton */}
      <div className="max-w-4xl mx-auto px-4 py-12 space-y-8">
        {/* Article body blocks */}
        <div className="bg-white rounded-xl shadow-md p-8 space-y-4">
          <div className="h-4 bg-gray-200 rounded animate-pulse w-full" />
          <div className="h-4 bg-gray-200 rounded animate-pulse w-5/6" />
          <div className="h-4 bg-gray-200 rounded animate-pulse w-full" />
          <div className="h-4 bg-gray-200 rounded animate-pulse w-4/6" />
          <div className="h-4 bg-gray-200 rounded animate-pulse w-full" />
          <div className="h-4 bg-gray-200 rounded animate-pulse w-3/4" />

          <div className="h-8 w-0" /> {/* spacer */}

          <div className="h-4 bg-gray-200 rounded animate-pulse w-full" />
          <div className="h-4 bg-gray-200 rounded animate-pulse w-5/6" />
          <div className="h-4 bg-gray-200 rounded animate-pulse w-full" />
          <div className="h-4 bg-gray-200 rounded animate-pulse w-2/3" />
        </div>

        {/* Image placeholder */}
        <div className="w-full aspect-video bg-gray-200 rounded-2xl animate-pulse" />

        {/* More content */}
        <div className="bg-white rounded-xl shadow-md p-8 space-y-4">
          <div className="h-4 bg-gray-200 rounded animate-pulse w-full" />
          <div className="h-4 bg-gray-200 rounded animate-pulse w-4/5" />
          <div className="h-4 bg-gray-200 rounded animate-pulse w-full" />
          <div className="h-4 bg-gray-200 rounded animate-pulse w-3/4" />
        </div>
      </div>
    </main>
  );
}
