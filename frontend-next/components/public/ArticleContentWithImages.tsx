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

    // Split content by closing tags to preserve structure
    const htmlParts = content.split(/(<\/[^>]+>)/g).filter(s => s.trim());

    const parts: ReactElement[] = [];
    let imageIndex = 0;
    let elementCount = 0;

    // Combine split parts back into complete HTML elements
    let currentElement = '';

    htmlParts.forEach((part) => {
      currentElement += part;

      // If we hit a closing tag, we have a complete element
      if (part.includes('</')) {
        if (currentElement.trim()) {
          parts.push(
            <div
              key={`element-${elementCount}`}
              dangerouslySetInnerHTML={{ __html: currentElement }}
              className="article-element"
            />
          );

          elementCount++;

          // Insert image after every 4 elements (if we have images)
          if (elementCount % 4 === 0 && imageIndex < images.length) {
            console.log(`🖼️ Inserting image ${imageIndex + 1} at position ${elementCount}`);
            const currentImage = images[imageIndex];
            const isPexelsImage = currentImage.includes('pexels.com');

            parts.push(
              <div key={`img-${imageIndex}`} className="my-10 rounded-2xl overflow-hidden shadow-2xl bg-gradient-to-br from-gray-50 to-gray-100 transform hover:scale-[1.02] transition-transform duration-300">
                <div className="relative w-full aspect-video">
                  <Image
                    src={currentImage}
                    alt={`Article image ${imageIndex + 1}`}
                    fill
                    className="object-contain"
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
        currentElement = '';
      }
    });

    // Add any remaining content
    if (currentElement.trim()) {
      parts.push(
        <div
          key={`element-final`}
          dangerouslySetInnerHTML={{ __html: currentElement }}
          className="article-element"
        />
      );
    }

    console.log('✅ Total parts created:', parts.length);
    setContentParts(parts);
  }, [content, images]);

  return (
    <div className="article-content-wrapper">
      {contentParts}
    </div>
  );
}

