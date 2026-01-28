'use client';

import { useState } from 'react';
import Image from 'next/image';
import { ChevronLeft, ChevronRight, X } from 'lucide-react';

interface GalleryImage {
  id: number;
  image: string;
  image_url: string;
  caption: string;
  order: number;
}

interface ImageGalleryProps {
  images: GalleryImage[];
}

export default function ImageGallery({ images }: ImageGalleryProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isOpen, setIsOpen] = useState(false);

  if (!images || images.length === 0) {
    return null;
  }

  const goToPrevious = () => {
    setCurrentIndex((prev) => (prev === 0 ? images.length - 1 : prev - 1));
  };

  const goToNext = () => {
    setCurrentIndex((prev) => (prev === images.length - 1 ? 0 : prev + 1));
  };

  const getImageUrl = (img: GalleryImage) => {
    const getMediaUrl = () => {
      if (typeof window !== 'undefined') {
        const host = window.location.hostname;
        if (host !== 'localhost' && host !== '127.0.0.1') {
          return 'https://heroic-healing-production-2365.up.railway.app';
        }
      }
      return 'http://localhost:8001';
    };
    const mediaUrl = getMediaUrl();
    
    if (img.image_url) return img.image_url.replace('http://backend:8001', mediaUrl).replace('http://localhost:8001', mediaUrl);
    if (img.image.startsWith('http')) return img.image.replace('http://backend:8001', mediaUrl).replace('http://localhost:8001', mediaUrl);
    return `${mediaUrl}${img.image}`;
  };

  return (
    <>
      {/* Gallery Grid */}
      <div className="bg-white rounded-xl shadow-md p-6 mb-8">
        <h3 className="text-2xl font-bold text-gray-900 mb-4">📸 Image Gallery</h3>
        
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {images.map((img, index) => (
            <div
              key={img.id}
              onClick={() => {
                setCurrentIndex(index);
                setIsOpen(true);
              }}
              className="relative aspect-square rounded-lg overflow-hidden cursor-pointer group"
            >
              <Image
                src={getImageUrl(img)}
                alt={img.caption || `Gallery image ${index + 1}`}
                fill
                className="object-cover transition-transform group-hover:scale-110"
                sizes="(max-width: 768px) 50vw, (max-width: 1200px) 33vw, 25vw"
              />
              <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-30 transition-all flex items-center justify-center">
                <span className="text-white opacity-0 group-hover:opacity-100 transition-opacity text-4xl">
                  🔍
                </span>
              </div>
              {img.caption && (
                <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent p-2 text-white text-xs">
                  {img.caption}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Lightbox Modal */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-95 z-50 flex items-center justify-center p-4"
          onClick={() => setIsOpen(false)}
        >
          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsOpen(false);
            }}
            className="absolute top-4 right-4 text-white hover:text-gray-300 transition-colors z-10"
          >
            <X size={32} />
          </button>

          <button
            onClick={(e) => {
              e.stopPropagation();
              goToPrevious();
            }}
            className="absolute left-4 text-white hover:text-gray-300 transition-colors z-10 bg-black/50 rounded-full p-2"
          >
            <ChevronLeft size={48} />
          </button>

          <button
            onClick={(e) => {
              e.stopPropagation();
              goToNext();
            }}
            className="absolute right-4 text-white hover:text-gray-300 transition-colors z-10 bg-black/50 rounded-full p-2"
          >
            <ChevronRight size={48} />
          </button>

          <div
            className="relative max-w-5xl max-h-[80vh] w-full h-full flex items-center justify-center"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="relative w-full h-full">
              <Image
                src={getImageUrl(images[currentIndex])}
                alt={images[currentIndex].caption || `Image ${currentIndex + 1}`}
                fill
                className="object-contain"
                sizes="90vw"
              />
            </div>
            
            {images[currentIndex].caption && (
              <div className="absolute bottom-0 left-0 right-0 bg-black/70 text-white p-4 text-center">
                <p className="text-lg">{images[currentIndex].caption}</p>
                <p className="text-sm text-gray-300 mt-1">
                  {currentIndex + 1} / {images.length}
                </p>
              </div>
            )}
          </div>

          {/* Thumbnails */}
          <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 flex gap-2 max-w-full overflow-x-auto px-4">
            {images.map((img, index) => (
              <button
                key={img.id}
                onClick={(e) => {
                  e.stopPropagation();
                  setCurrentIndex(index);
                }}
                className={`relative w-16 h-16 rounded-lg overflow-hidden flex-shrink-0 border-2 ${
                  index === currentIndex ? 'border-white' : 'border-transparent opacity-50'
                } hover:opacity-100 transition-all`}
              >
                <Image
                  src={getImageUrl(img)}
                  alt=""
                  fill
                  className="object-cover"
                  sizes="64px"
                />
              </button>
            ))}
          </div>
        </div>
      )}
    </>
  );
}
