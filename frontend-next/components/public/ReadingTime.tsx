'use client';

import { Clock } from 'lucide-react';

interface ReadingTimeProps {
  content: string;
}

export default function ReadingTime({ content }: ReadingTimeProps) {
  // Calculate reading time (average 200 words per minute)
  const wordsPerMinute = 200;
  const textContent = content.replace(/<[^>]*>/g, ''); // Strip HTML tags
  const wordCount = textContent.split(/\s+/).length;
  const readingTime = Math.ceil(wordCount / wordsPerMinute);

  return (
    <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-brand-50 text-brand-700 rounded-full text-sm font-medium border border-brand-200">
      <Clock size={16} className="text-brand-600" />
      <span>{readingTime} min read</span>
    </div>
  );
}
