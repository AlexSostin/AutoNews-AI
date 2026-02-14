'use client';

import Image from 'next/image';
import { useEffect, useState, type ReactElement } from 'react';

interface ArticleContentWithImagesProps {
  content: string;
  images: string[];
}

export default function ArticleContentWithImages({ content, images }: ArticleContentWithImagesProps) {
  const [contentParts, setContentParts] = useState<ReactElement[]>([]);

  useEffect(() => {
    console.log('📸 Images available:', images);
    console.log('📝 Content length:', content.length);

    // Split content into top-level block elements, preserving nested structures
    // We split on top-level block closing tags only (not nested ones like </li>)
    const topLevelBlocks: string[] = [];
    let current = '';
    let depth = 0;

    // Split on closing tags that mark the end of a top-level element
    // Track nesting for block-level elements
    const tokens = content.split(/(<\/?[^>]+>)/g);

    for (const token of tokens) {
      const openMatch = token.match(/^<(ul|ol|table|blockquote|pre|div|section)[\s>]/i);
      const closeMatch = token.match(/^<\/(ul|ol|table|blockquote|pre|div|section)>/i);

      if (openMatch) {
        depth++;
      }

      current += token;

      if (closeMatch) {
        depth--;
        if (depth <= 0) {
          depth = 0;
          // End of a top-level block element - split here
          if (current.trim()) {
            topLevelBlocks.push(current);
            current = '';
          }
        }
      } else if (depth === 0) {
        // At top level, also split on </h2>, </h3>, </h4>, </p>
        const topCloseMatch = token.match(/^<\/(h[1-6]|p)>/i);
        if (topCloseMatch) {
          if (current.trim()) {
            topLevelBlocks.push(current);
            current = '';
          }
        }
      }
    }

    // Add any remaining content
    if (current.trim()) {
      topLevelBlocks.push(current);
    }

    const parts: ReactElement[] = [];
    let imageIndex = 0;

    topLevelBlocks.forEach((block, idx) => {
      if (block.trim()) {
        parts.push(
          <div
            key={`element-${idx}`}
            dangerouslySetInnerHTML={{ __html: block }}
            className="article-element"
          />
        );

        // Insert image after every 4 elements (if we have images)
        if ((idx + 1) % 4 === 0 && imageIndex < images.length) {
          console.log(`🖼️ Inserting image ${imageIndex + 1} at position ${idx + 1}`);
          const currentImage = images[imageIndex];
          const isPexelsImage = currentImage.includes('pexels.com');

          parts.push(
            <div key={`img-${imageIndex}`} className="my-10 rounded-2xl overflow-hidden shadow-2xl bg-gradient-to-br from-gray-50 to-gray-100 transform hover:scale-[1.02] transition-transform duration-300">
              <div className="relative w-full aspect-video">
                <Image
                  src={currentImage}
                  alt={`Article image ${imageIndex + 1}`}
                  fill
                  className="object-cover"
                  unoptimized
                />
              </div>
              {isPexelsImage && (
                <div className="px-4 py-2 bg-black/20 backdrop-blur-sm">
                  <p className="text-xs text-gray-300 text-center">Photo via Pexels</p>
                </div>
              )}
            </div>
          );
          imageIndex++;
        }
      }
    });


    console.log('✅ Total parts created:', parts.length);
    setContentParts(parts);
  }, [content, images]);

  return (
    <div className="article-content-wrapper">
      {contentParts}
    </div>
  );
}

