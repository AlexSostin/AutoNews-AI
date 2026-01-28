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
              className="mb-4"
            />
          );
          
          elementCount++;
          
          // Insert image after every 4 elements (if we have images)
          if (elementCount % 4 === 0 && imageIndex < images.length) {
            console.log(`🖼️ Inserting image ${imageIndex + 1} at position ${elementCount}`);
            parts.push(
              <div key={`img-${imageIndex}`} className="my-8 rounded-xl overflow-hidden shadow-lg bg-gray-900">
                <div className="relative w-full aspect-video">
                  <Image
                    src={images[imageIndex]}
                    alt={`Article image ${imageIndex + 1}`}
                    fill
                    className="object-cover scale-105"
                    unoptimized
                  />
                </div>
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
          className="mb-4"
        />
      );
    }
    
    console.log('✅ Total parts created:', parts.length);
    setContentParts(parts);
  }, [content, images]);

  return (
    <div className="prose prose-lg max-w-none text-gray-800 leading-relaxed">
      {contentParts}
    </div>
  );
}
