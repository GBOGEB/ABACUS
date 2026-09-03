'use client';

import { useEffect, useCallback } from 'react';
import Image from 'next/image';
import { X, ChevronLeft, ChevronRight } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import type { SlideData } from './slide-card';

interface SlideModalProps {
  slide: SlideData | null;
  onClose: () => void;
  onPrev?: () => void;
  onNext?: () => void;
}

export function SlideModal({ slide, onClose, onPrev, onNext }: SlideModalProps) {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose?.();
      if (e.key === 'ArrowLeft') onPrev?.();
      if (e.key === 'ArrowRight') onNext?.();
    },
    [onClose, onPrev, onNext]
  );

  useEffect(() => {
    window?.addEventListener?.('keydown', handleKeyDown);
    return () => window?.removeEventListener?.('keydown', handleKeyDown);
  }, [handleKeyDown]);

  return (
    <AnimatePresence>
      {slide && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
          onClick={onClose}
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.9, opacity: 0 }}
            transition={{ type: 'spring', damping: 25 }}
            className="relative max-h-[90vh] max-w-[90vw] overflow-hidden rounded-xl bg-card"
            onClick={(e: React.MouseEvent) => e?.stopPropagation?.()}
          >
            <div className="flex items-center justify-between border-b px-4 py-2">
              <span className="font-display font-bold text-primary">
                Slide {slide?.pageNumber ?? 0}
              </span>
              <button
                onClick={onClose}
                className="rounded-full p-1 hover:bg-muted transition-colors"
                aria-label="Close"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="relative aspect-[16/9] w-[80vw] max-w-[1100px] bg-muted">
              <Image
                src={`/slides/${slide?.imageFilename ?? 'slide-01.png'}`}
                alt={`Slide ${slide?.pageNumber ?? 0}`}
                fill
                className="object-contain"
                sizes="80vw"
                priority
              />
            </div>
            {/* Navigation arrows */}
            {onPrev && (
              <button
                onClick={onPrev}
                className="absolute left-2 top-1/2 -translate-y-1/2 rounded-full bg-black/50 p-2 text-white hover:bg-black/70 transition-colors"
                aria-label="Previous slide"
              >
                <ChevronLeft className="h-6 w-6" />
              </button>
            )}
            {onNext && (
              <button
                onClick={onNext}
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded-full bg-black/50 p-2 text-white hover:bg-black/70 transition-colors"
                aria-label="Next slide"
              >
                <ChevronRight className="h-6 w-6" />
              </button>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
