'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import Image from 'next/image';
import { motion, AnimatePresence } from 'framer-motion';
import { LayoutGrid, Star, TrendingUp, Loader2, Rows3, ChevronLeft, ChevronRight, Layers } from 'lucide-react';
import { SlideCard, StarButton, VoteButtons, type SlideData, type VoteDirection } from './slide-card';
import { SlideModal } from './slide-modal';
import { cn } from '@/lib/utils';

type Filter = 'all' | 'starred' | 'most-voted';
type ViewMode = 'grid' | 'focus';

export function SlideBrowserClient() {
  const [slides, setSlides] = useState<SlideData[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<Filter>('all');
  const [group, setGroup] = useState<string>('all');
  const [view, setView] = useState<ViewMode>('grid');
  const [focusIdx, setFocusIdx] = useState(0);
  const [expandedSlide, setExpandedSlide] = useState<SlideData | null>(null);

  const fetchSlides = useCallback(async () => {
    try {
      const res = await fetch('/api/slides');
      if (res?.ok) {
        const data = await res?.json();
        setSlides(data ?? []);
      }
    } catch (err: any) {
      console.error('Failed to fetch slides:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSlides();
  }, [fetchSlides]);

  const handleStar = useCallback(async (id: number) => {
    try {
      const res = await fetch(`/api/slides/${id}/star`, { method: 'POST' });
      if (res?.ok) {
        const updated = await res?.json();
        setSlides((prev) => (prev ?? []).map((s) => (s?.id === id ? { ...s, starred: updated?.starred } : s)));
        setExpandedSlide((prev) => (prev && prev.id === id ? { ...prev, starred: updated?.starred } : prev));
      }
    } catch (err: any) {
      console.error('Failed to toggle star:', err);
    }
  }, []);

  const handleVote = useCallback(async (id: number, direction: VoteDirection) => {
    try {
      const res = await fetch(`/api/slides/${id}/vote`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ direction }),
      });
      if (res?.ok) {
        const u = await res?.json();
        const patch = { votesUp: u?.votesUp ?? 0, votesDown: u?.votesDown ?? 0, votesNeutral: u?.votesNeutral ?? 0 };
        setSlides((prev) => (prev ?? []).map((s) => (s?.id === id ? { ...s, ...patch } : s)));
        setExpandedSlide((prev) => (prev && prev.id === id ? { ...prev, ...patch } : prev));
      }
    } catch (err: any) {
      console.error('Failed to vote:', err);
    }
  }, []);

  const groups = useMemo(() => {
    const set = new Set<string>();
    for (const s of slides) if (s.groupName) set.add(s.groupName);
    return Array.from(set);
  }, [slides]);

  const filteredSlides = useMemo(() => {
    let list = slides ?? [];
    if (group !== 'all') list = list.filter((s) => s.groupName === group);
    switch (filter) {
      case 'starred':
        return list.filter((s) => s?.starred);
      case 'most-voted':
        return [...list].sort((a, b) => (b.votesUp - b.votesDown) - (a.votesUp - a.votesDown));
      default:
        return list;
    }
  }, [slides, group, filter]);

  useEffect(() => {
    setFocusIdx(0);
  }, [group, filter, view]);

  const focusSlide = filteredSlides[Math.min(focusIdx, Math.max(0, filteredSlides.length - 1))] ?? null;

  const goPrev = useCallback(() => setFocusIdx((i) => Math.max(0, i - 1)), []);
  const goNext = useCallback(() => setFocusIdx((i) => Math.min(filteredSlides.length - 1, i + 1)), [filteredSlides.length]);

  useEffect(() => {
    if (view !== 'focus' || expandedSlide) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft') goPrev();
      if (e.key === 'ArrowRight') goNext();
      if (focusSlide) {
        if (e.key === 's' || e.key === 'S') handleStar(focusSlide.id);
        if (e.key === '1') handleVote(focusSlide.id, 'up');
        if (e.key === '2') handleVote(focusSlide.id, 'neutral');
        if (e.key === '3') handleVote(focusSlide.id, 'down');
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [view, expandedSlide, goPrev, goNext, focusSlide, handleStar, handleVote]);

  const handleExpandPrev = useCallback(() => {
    if (!expandedSlide) return;
    const idx = filteredSlides.findIndex((s) => s?.id === expandedSlide?.id);
    if (idx > 0) setExpandedSlide(filteredSlides[idx - 1] ?? null);
  }, [expandedSlide, filteredSlides]);

  const handleExpandNext = useCallback(() => {
    if (!expandedSlide) return;
    const idx = filteredSlides.findIndex((s) => s?.id === expandedSlide?.id);
    if (idx < filteredSlides.length - 1) setExpandedSlide(filteredSlides[idx + 1] ?? null);
  }, [expandedSlide, filteredSlides]);

  const filters: { key: Filter; label: string; icon: typeof LayoutGrid }[] = [
    { key: 'all', label: 'All', icon: LayoutGrid },
    { key: 'starred', label: 'Starred', icon: Star },
    { key: 'most-voted', label: 'Most Voted', icon: TrendingUp },
  ];

  const pill = (active: boolean) =>
    cn(
      'flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-all',
      active ? 'bg-primary text-primary-foreground shadow-sm' : 'bg-secondary text-secondary-foreground hover:bg-accent'
    );

  return (
    <div className="mx-auto max-w-[1200px] px-4 py-8">
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
        <h1 className="font-display text-3xl font-bold tracking-tight text-primary">QPLANT-LB Slide Review</h1>
        <p className="mt-1 text-muted-foreground">
          Browse the full deck, step through one slide at a time, or work by topic group. Star key slides and vote up / neutral / down.
        </p>
      </motion.div>

      {/* Controls */}
      <div className="mb-6 flex flex-wrap items-center gap-2">
        {filters.map((f) => {
          const Icon = f.icon;
          return (
            <button key={f.key} onClick={() => setFilter(f.key)} className={pill(filter === f.key)}>
              <Icon className="h-4 w-4" />
              {f.label}
            </button>
          );
        })}
        <span className="mx-1 hidden h-6 w-px bg-border sm:block" />
        <div className="flex items-center gap-2">
          <Layers className="h-4 w-4 text-muted-foreground" />
          <select
            value={group}
            onChange={(e) => setGroup(e.target.value)}
            className="rounded-lg border bg-card px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-primary"
            aria-label="Slide group"
          >
            <option value="all">All groups</option>
            {groups.map((g) => (
              <option key={g} value={g}>
                {g}
              </option>
            ))}
          </select>
        </div>
        <span className="mx-1 hidden h-6 w-px bg-border sm:block" />
        <button onClick={() => setView('grid')} className={pill(view === 'grid')} title="Grid view">
          <LayoutGrid className="h-4 w-4" /> Grid
        </button>
        <button onClick={() => setView('focus')} className={pill(view === 'focus')} title="One slide at a time">
          <Rows3 className="h-4 w-4" /> One at a time
        </button>
        <span className="ml-auto font-mono text-xs text-muted-foreground">
          {filteredSlides.length} / {slides.length} slides
        </span>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      )}

      {/* Grid view */}
      {!loading && view === 'grid' && (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {filteredSlides.map((slide, i) => (
            <SlideCard key={slide?.id ?? i} slide={slide} index={i} onStar={handleStar} onVote={handleVote} onExpand={setExpandedSlide} />
          ))}
        </div>
      )}

      {/* Focus view: one slide at a time */}
      {!loading && view === 'focus' && focusSlide && (
        <div className="mx-auto max-w-[1000px]">
          <div className="mb-3 flex items-center justify-between">
            <span className="font-mono text-sm text-muted-foreground">
              {focusIdx + 1} of {filteredSlides.length}
            </span>
            <div className="h-2 w-48 overflow-hidden rounded-full bg-secondary">
              <div className="h-full rounded-full bg-primary transition-all duration-300" style={{ width: `${((focusIdx + 1) / filteredSlides.length) * 100}%` }} />
            </div>
          </div>
          <AnimatePresence mode="wait">
            <motion.div
              key={focusSlide.id}
              initial={{ opacity: 0, x: 30 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -30 }}
              transition={{ duration: 0.2 }}
              className={cn('overflow-hidden rounded-xl bg-card', focusSlide.starred && 'glow-purple ring-2 ring-primary')}
              style={{ boxShadow: 'var(--shadow-md)' }}
            >
              <button onClick={() => setExpandedSlide(focusSlide)} className="relative block aspect-[16/9] w-full bg-muted">
                <Image
                  src={`/slides/${focusSlide.imageFilename}`}
                  alt={focusSlide.title ? `Slide ${focusSlide.pageNumber}: ${focusSlide.title}` : `Slide ${focusSlide.pageNumber}`}
                  fill
                  className="object-contain"
                  sizes="(max-width: 1000px) 100vw, 1000px"
                  priority
                />
              </button>
              <div className="flex flex-wrap items-center justify-between gap-3 border-t px-4 py-3">
                <div className="min-w-0">
                  <p className="font-display font-bold text-primary">
                    Slide {focusSlide.pageNumber}
                    {focusSlide.title ? ` — ${focusSlide.title}` : ''}
                  </p>
                  {focusSlide.groupName && <p className="text-xs text-muted-foreground">{focusSlide.groupName}</p>}
                </div>
                <div className="flex items-center gap-2">
                  <StarButton slide={focusSlide} onStar={handleStar} size="lg" />
                  <VoteButtons slide={focusSlide} onVote={handleVote} size="lg" />
                </div>
              </div>
            </motion.div>
          </AnimatePresence>
          <div className="mt-4 flex items-center justify-between">
            <button onClick={goPrev} disabled={focusIdx === 0} className="flex items-center gap-1 rounded-lg bg-secondary px-4 py-2 text-sm font-medium disabled:opacity-40">
              <ChevronLeft className="h-4 w-4" /> Previous
            </button>
            <p className="hidden text-xs text-muted-foreground sm:block">
              Keys: ← → navigate · S star · 1 up · 2 neutral · 3 down
            </p>
            <button onClick={goNext} disabled={focusIdx >= filteredSlides.length - 1} className="flex items-center gap-1 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-40">
              Next <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {!loading && filteredSlides.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
          <Star className="mb-2 h-10 w-10" />
          <p className="text-lg">No slides match this filter.</p>
        </div>
      )}

      <SlideModal slide={expandedSlide} onClose={() => setExpandedSlide(null)} onPrev={handleExpandPrev} onNext={handleExpandNext} />
    </div>
  );
}
