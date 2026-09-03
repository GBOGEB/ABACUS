'use client';

import { useState, useCallback } from 'react';
import Image from 'next/image';
import { Star, ThumbsUp, ThumbsDown, Maximize2, MoveHorizontal } from 'lucide-react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

export interface SlideData {
  id: number;
  pageNumber: number;
  imageFilename: string;
  title?: string | null;
  groupName?: string | null;
  starred: boolean;
  votesUp: number;
  votesDown: number;
  votesNeutral: number;
}

export type VoteDirection = 'up' | 'neutral' | 'down';

interface SlideCardProps {
  slide: SlideData;
  index: number;
  onStar: (id: number) => void;
  onVote: (id: number, direction: VoteDirection) => void;
  onExpand: (slide: SlideData) => void;
}

export function VoteButtons({
  slide,
  onVote,
  size = 'sm',
}: {
  slide: SlideData;
  onVote: (id: number, direction: VoteDirection) => void;
  size?: 'sm' | 'lg';
}) {
  const [voting, setVoting] = useState(false);
  const handleVote = useCallback(
    (direction: VoteDirection) => {
      if (voting) return;
      setVoting(true);
      onVote?.(slide?.id, direction);
      setTimeout(() => setVoting(false), 300);
    },
    [voting, onVote, slide?.id]
  );
  const icon = size === 'lg' ? 'h-5 w-5' : 'h-3.5 w-3.5';
  const pad = size === 'lg' ? 'px-4 py-2 text-base' : 'px-2 py-1 text-sm';
  return (
    <div className={cn('flex items-center', size === 'lg' ? 'gap-3' : 'gap-1.5')}>
      <button
        onClick={() => handleVote('up')}
        disabled={voting}
        className={cn('flex items-center gap-1 rounded-lg text-muted-foreground transition-colors hover:bg-green-50 hover:text-green-600', pad)}
        aria-label="Vote up"
        title="Vote up"
      >
        <ThumbsUp className={icon} />
        <span className="font-mono text-xs">{slide?.votesUp ?? 0}</span>
      </button>
      <button
        onClick={() => handleVote('neutral')}
        disabled={voting}
        className={cn('flex items-center gap-1 rounded-lg text-muted-foreground transition-colors hover:bg-amber-50 hover:text-amber-600', pad)}
        aria-label="Vote neutral"
        title="Neutral / sideways"
      >
        <MoveHorizontal className={icon} />
        <span className="font-mono text-xs">{slide?.votesNeutral ?? 0}</span>
      </button>
      <button
        onClick={() => handleVote('down')}
        disabled={voting}
        className={cn('flex items-center gap-1 rounded-lg text-muted-foreground transition-colors hover:bg-red-50 hover:text-red-500', pad)}
        aria-label="Vote down"
        title="Vote down"
      >
        <ThumbsDown className={icon} />
        <span className="font-mono text-xs">{slide?.votesDown ?? 0}</span>
      </button>
    </div>
  );
}

export function StarButton({
  slide,
  onStar,
  size = 'sm',
}: {
  slide: SlideData;
  onStar: (id: number) => void;
  size?: 'sm' | 'lg';
}) {
  return (
    <button
      onClick={() => onStar?.(slide?.id)}
      className={cn(
        'flex items-center gap-1 rounded-lg transition-colors hover:bg-secondary',
        size === 'lg' ? 'px-4 py-2 text-base' : 'px-2 py-1 text-sm'
      )}
      aria-label={slide?.starred ? 'Unstar slide' : 'Star slide'}
    >
      <Star
        className={cn(
          size === 'lg' ? 'h-5 w-5' : 'h-4 w-4',
          'transition-colors',
          slide?.starred ? 'fill-primary text-primary' : 'text-muted-foreground'
        )}
      />
      <span className={cn('text-xs font-medium', slide?.starred ? 'text-primary' : 'text-muted-foreground')}>
        {slide?.starred ? 'Key slide' : 'Star'}
      </span>
    </button>
  );
}

export function SlideCard({ slide, index, onStar, onVote, onExpand }: SlideCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: Math.min(index, 12) * 0.04 }}
      className={cn(
        'group relative flex flex-col overflow-hidden rounded-xl bg-card transition-all duration-300',
        slide?.starred ? 'glow-purple ring-2 ring-primary' : 'hover:shadow-lg'
      )}
      style={{ boxShadow: 'var(--shadow-md)' }}
    >
      {/* Slide number badge */}
      <div className="absolute right-2 top-2 z-10 flex h-7 w-7 items-center justify-center rounded-full bg-primary/90 text-xs font-bold text-primary-foreground font-mono shadow">
        {slide?.pageNumber ?? 0}
      </div>

      {/* Expand button */}
      <button
        onClick={() => onExpand?.(slide)}
        className="absolute left-2 top-2 z-10 flex h-7 w-7 items-center justify-center rounded-full bg-black/50 text-white opacity-0 transition-opacity group-hover:opacity-100"
        aria-label="Expand slide"
      >
        <Maximize2 className="h-3.5 w-3.5" />
      </button>

      {/* Slide image */}
      <button
        onClick={() => onExpand?.(slide)}
        className="relative aspect-[16/9] w-full cursor-pointer overflow-hidden bg-muted"
      >
        <Image
          src={`/slides/${slide?.imageFilename ?? 'slide-01.png'}`}
          alt={slide?.title ? `Slide ${slide.pageNumber}: ${slide.title}` : `Slide ${slide?.pageNumber ?? 0}`}
          fill
          className="object-contain transition-transform duration-300 group-hover:scale-[1.02]"
          sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
        />
      </button>

      {/* Title / group */}
      <div className="px-3 pt-2">
        <p className="truncate text-xs font-medium text-foreground" title={slide?.title ?? ''}>
          {slide?.title ?? `Slide ${slide?.pageNumber}`}
        </p>
        {slide?.groupName && (
          <span className="mt-1 inline-block rounded-full bg-secondary px-2 py-0.5 text-[10px] font-medium text-primary">
            {slide.groupName}
          </span>
        )}
      </div>

      {/* Actions bar */}
      <div className="mt-1 flex items-center justify-between border-t px-2 py-2">
        <StarButton slide={slide} onStar={onStar} />
        <VoteButtons slide={slide} onVote={onVote} />
      </div>
    </motion.div>
  );
}
