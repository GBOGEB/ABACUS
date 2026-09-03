'use client';

import { useState, useCallback, useEffect } from 'react';
import Image from 'next/image';
import { motion, AnimatePresence } from 'framer-motion';
import { Play, Trophy, Loader2, RefreshCw, Equal, MessageSquare, BarChart3 } from 'lucide-react';
import Link from 'next/link';
import { cn } from '@/lib/utils';

interface PairSlide {
  id: number;
  pageNumber: number;
  imageFilename: string;
  title?: string | null;
}

interface AbPair {
  slideA: PairSlide;
  slideB: PairSlide;
  currentRound: number;
  totalRounds: number;
  groupName?: string | null;
}

interface WinResult {
  slideId: number;
  pageNumber: number;
  wins: number;
}

type Phase = 'idle' | 'testing' | 'results';

export function AbTestClient() {
  const [phase, setPhase] = useState<Phase>('idle');
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [pair, setPair] = useState<AbPair | null>(null);
  const [results, setResults] = useState<WinResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [choosing, setChoosing] = useState(false);
  const [groups, setGroups] = useState<string[]>([]);
  const [group, setGroup] = useState<string>('');
  const [rounds, setRounds] = useState<number>(10);
  const [reason, setReason] = useState('');
  const [showReason, setShowReason] = useState(false);

  useEffect(() => {
    fetch('/api/slides')
      .then((r) => (r.ok ? r.json() : []))
      .then((data: any[]) => {
        const set = new Set<string>();
        for (const s of data ?? []) if (s?.groupName) set.add(s.groupName);
        setGroups(Array.from(set));
      })
      .catch((err) => console.error('Failed to load groups:', err));
  }, []);

  const fetchResults = async (sid: number) => {
    try {
      const res = await fetch(`/api/ab/session/${sid}/results`);
      if (res?.ok) setResults((await res.json()) ?? []);
    } catch (err: any) {
      console.error('Failed to fetch results:', err);
    }
  };

  const fetchPair = async (sid: number) => {
    try {
      const res = await fetch(`/api/ab/pair?sessionId=${sid}`);
      if (res?.ok) {
        const data = await res.json();
        if (data?.done) {
          await fetchResults(sid);
          setPhase('results');
        } else {
          setPair(data ?? null);
        }
      }
    } catch (err: any) {
      console.error('Failed to fetch pair:', err);
    }
  };

  const startSession = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/ab/session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rounds, group: group || null }),
      });
      if (res?.ok) {
        const data = await res.json();
        setSessionId(data?.id ?? null);
        setPhase('testing');
        await fetchPair(data?.id);
      }
    } catch (err: any) {
      console.error('Failed to start session:', err);
    } finally {
      setLoading(false);
    }
  }, [rounds, group]);

  const submit = useCallback(
    async (winnerId: number | null, isTie = false) => {
      if (!pair || !sessionId || choosing) return;
      setChoosing(true);
      try {
        const res = await fetch('/api/ab/vote', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            sessionId,
            slideAId: pair.slideA.id,
            slideBId: pair.slideB.id,
            winnerId,
            isTie,
            reason: reason.trim() || null,
          }),
        });
        if (res?.ok) {
          setReason('');
          await fetchPair(sessionId);
        }
      } catch (err: any) {
        console.error('Failed to vote:', err);
      } finally {
        setChoosing(false);
      }
    },
    [pair, sessionId, choosing, reason]
  );

  // Keyboard shortcuts: A / B / T (tie)
  useEffect(() => {
    if (phase !== 'testing' || !pair) return;
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === 'TEXTAREA' || tag === 'INPUT') return;
      if (e.key === 'a' || e.key === 'A' || e.key === 'ArrowLeft') submit(pair.slideA.id);
      if (e.key === 'b' || e.key === 'B' || e.key === 'ArrowRight') submit(pair.slideB.id);
      if (e.key === 't' || e.key === 'T') submit(null, true);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [phase, pair, submit]);

  return (
    <div className="mx-auto max-w-[1200px] px-4 py-8">
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
        <h1 className="font-display text-3xl font-bold tracking-tight text-primary">A/B Slide Test (Bradley–Terry)</h1>
        <p className="mt-1 text-muted-foreground">
          Pairwise comparisons feed a Bradley–Terry model. Pairs are chosen adaptively to maximise coverage.
        </p>
      </motion.div>

      <AnimatePresence mode="wait">
        {phase === 'idle' && (
          <motion.div key="idle" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex flex-col items-center justify-center py-16">
            <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-secondary">
              <Play className="h-10 w-10 text-primary" />
            </div>
            <h2 className="mb-2 font-display text-xl font-bold">Configure a session</h2>
            <p className="mb-6 max-w-md text-center text-muted-foreground">
              Choose the scope (whole deck or one topic group) and the number of rounds, then pick the slide you prefer in each pair.
            </p>
            <div className="mb-6 grid w-full max-w-md gap-4 rounded-xl bg-card p-5" style={{ boxShadow: 'var(--shadow-md)' }}>
              <label className="grid gap-1 text-sm">
                <span className="font-medium">Scope</span>
                <select value={group} onChange={(e) => setGroup(e.target.value)} className="rounded-lg border bg-background px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary">
                  <option value="">Whole deck</option>
                  {groups.map((g) => (
                    <option key={g} value={g}>
                      {g}
                    </option>
                  ))}
                </select>
              </label>
              <label className="grid gap-1 text-sm">
                <span className="font-medium">
                  Rounds: <span className="font-mono text-primary">{rounds}</span>
                </span>
                <input type="range" min={3} max={60} step={1} value={rounds} onChange={(e) => setRounds(Number(e.target.value))} className="accent-primary" />
                <span className="text-xs text-muted-foreground">Full deck has 105 unique pairs; ~30+ rounds gives a usable ranking.</span>
              </label>
            </div>
            <button onClick={startSession} disabled={loading} className="flex items-center gap-2 rounded-xl bg-primary px-8 py-3 text-sm font-bold text-primary-foreground shadow-lg transition-all hover:opacity-90 disabled:opacity-50">
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              Start A/B Test
            </button>
          </motion.div>
        )}

        {phase === 'testing' && pair && (
          <motion.div key={`round-${pair.currentRound}`} initial={{ opacity: 0, x: 40 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -40 }} transition={{ type: 'spring', damping: 25 }}>
            <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
              <span className="font-mono text-sm text-muted-foreground">
                Round {pair.currentRound} of {pair.totalRounds}
                {pair.groupName ? ` · ${pair.groupName}` : ' · Whole deck'}
              </span>
              <div className="h-2 w-48 overflow-hidden rounded-full bg-secondary">
                <div className="h-full rounded-full bg-primary transition-all duration-500" style={{ width: `${((pair.currentRound - 1) / pair.totalRounds) * 100}%` }} />
              </div>
            </div>

            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
              {[pair.slideA, pair.slideB].map((slide, idx) => (
                <motion.button
                  key={slide.id}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => submit(slide.id)}
                  disabled={choosing}
                  className="group relative overflow-hidden rounded-xl bg-card transition-all hover:ring-2 hover:ring-primary"
                  style={{ boxShadow: 'var(--shadow-md)' }}
                >
                  <div className="absolute left-3 top-3 z-10 rounded-full bg-primary px-3 py-1 text-xs font-bold text-primary-foreground shadow">
                    {idx === 0 ? 'A' : 'B'} — Slide {slide.pageNumber}
                  </div>
                  <div className="relative aspect-[16/9] w-full bg-muted">
                    <Image src={`/slides/${slide.imageFilename}`} alt={slide.title ? `Slide ${slide.pageNumber}: ${slide.title}` : `Slide ${slide.pageNumber}`} fill className="object-contain" sizes="(max-width: 768px) 100vw, 50vw" />
                  </div>
                  <div className="border-t px-4 py-3 text-center">
                    <span className="text-sm font-bold text-primary group-hover:underline">{choosing ? 'Saving…' : `Prefer ${idx === 0 ? 'A' : 'B'}`}</span>
                    {slide.title && <p className="mt-0.5 truncate text-xs text-muted-foreground">{slide.title}</p>}
                  </div>
                </motion.button>
              ))}
            </div>

            <div className="mt-5 flex flex-wrap items-center justify-center gap-3">
              <button onClick={() => submit(null, true)} disabled={choosing} className="flex items-center gap-2 rounded-lg bg-secondary px-4 py-2 text-sm font-medium text-secondary-foreground hover:bg-accent disabled:opacity-50">
                <Equal className="h-4 w-4" /> No preference (tie)
              </button>
              <button onClick={() => setShowReason((v) => !v)} className={cn('flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium', showReason ? 'bg-primary text-primary-foreground' : 'bg-secondary text-secondary-foreground hover:bg-accent')}>
                <MessageSquare className="h-4 w-4" /> {showReason ? 'Hide reason' : 'Add a reason'}
              </button>
              <span className="hidden text-xs text-muted-foreground sm:block">Keys: A / B / T</span>
            </div>
            {showReason && (
              <textarea
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                maxLength={500}
                placeholder="Why do you prefer this slide? (e.g. clearer hierarchy, better use of the 3D view, less text) — attached to your next pick"
                className="mt-3 w-full rounded-lg border bg-card px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-primary"
                rows={2}
              />
            )}
          </motion.div>
        )}

        {phase === 'results' && (
          <motion.div key="results" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <div className="mb-6 flex items-center gap-3">
              <Trophy className="h-8 w-8 text-primary" />
              <h2 className="font-display text-2xl font-bold">Session Results (wins this session)</h2>
            </div>
            {results.length === 0 && <p className="text-muted-foreground">All rounds were ties — no decisive winners this session.</p>}
            <div className="space-y-3">
              {results.map((r, i) => (
                <motion.div key={r.slideId} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.08 }} className={cn('flex items-center gap-4 rounded-xl px-4 py-3', i === 0 ? 'bg-primary/10 ring-1 ring-primary' : 'bg-card')} style={{ boxShadow: 'var(--shadow-sm)' }}>
                  <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary font-mono text-sm font-bold text-primary-foreground">{i + 1}</span>
                  <div className="relative aspect-[16/9] w-24 overflow-hidden rounded-lg bg-muted">
                    <Image src={`/slides/slide-${String(r.pageNumber).padStart(2, '0')}.png`} alt={`Slide ${r.pageNumber}`} fill className="object-contain" sizes="96px" />
                  </div>
                  <div className="flex-1">
                    <span className="font-medium">Slide {r.pageNumber}</span>
                  </div>
                  <div className="text-right">
                    <span className="font-mono text-lg font-bold text-primary">{r.wins}</span>
                    <span className="ml-1 text-xs text-muted-foreground">wins</span>
                  </div>
                </motion.div>
              ))}
            </div>
            <div className="mt-8 flex flex-wrap justify-center gap-3">
              <button
                onClick={() => {
                  setPhase('idle');
                  setSessionId(null);
                  setPair(null);
                  setResults([]);
                }}
                className="flex items-center gap-2 rounded-xl bg-primary px-6 py-3 text-sm font-bold text-primary-foreground shadow-lg transition-all hover:opacity-90"
              >
                <RefreshCw className="h-4 w-4" /> New Session
              </button>
              <Link href="/results" className="flex items-center gap-2 rounded-xl bg-secondary px-6 py-3 text-sm font-bold text-secondary-foreground shadow transition-all hover:bg-accent">
                <BarChart3 className="h-4 w-4" /> Global BT ranking & KPIs
              </Link>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
