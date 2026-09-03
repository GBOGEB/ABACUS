'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import Image from 'next/image';
import { motion } from 'framer-motion';
import {
  Star,
  ThumbsUp,
  Trophy,
  Download,
  Loader2,
  Sigma,
  Activity,
  MessageSquare,
  RefreshCw,
} from 'lucide-react';
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  LabelList,
} from 'recharts';
import { cn } from '@/lib/utils';
import type { Analytics } from '@/lib/analytics';

type SlideStat = Analytics['slides'][number];
type SortMode = 'bt' | 'stars' | 'votes' | 'ab-wins';

function fmt(n: number | null | undefined, d = 2): string {
  if (n == null || !Number.isFinite(n)) return '–';
  return n.toFixed(d);
}
function pct(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return '–';
  return `${Math.round(n * 100)}%`;
}

function download(url: string) {
  const a = document.createElement('a');
  a.href = url;
  a.download = '';
  document.body.appendChild(a);
  a.click();
  a.remove();
}

function KpiCard({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-lg bg-card px-4 py-3" style={{ boxShadow: 'var(--shadow-sm)' }}>
      <div className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="font-mono text-xl font-bold text-foreground">{value}</div>
      {hint && <div className="text-[11px] text-muted-foreground">{hint}</div>}
    </div>
  );
}

function Phase({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border bg-card/50 p-4">
      <h3 className="font-display mb-3 text-sm font-bold uppercase tracking-wide text-primary">{title}</h3>
      <div className="grid grid-cols-2 gap-3">{children}</div>
    </div>
  );
}

export function ResultsClient() {
  const [data, setData] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [sortMode, setSortMode] = useState<SortMode>('bt');

  const fetchResults = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/analytics', { cache: 'no-store' });
      if (res?.ok) setData((await res.json()) as Analytics);
    } catch (err) {
      console.error('Failed to fetch analytics:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchResults();
  }, [fetchResults]);

  const sorted = useMemo(() => {
    const safe = [...(data?.slides ?? [])];
    switch (sortMode) {
      case 'bt':
        return safe.sort((a, b) => (a.btRank ?? 99) - (b.btRank ?? 99) || b.netVotes - a.netVotes);
      case 'stars':
        return safe.sort((a, b) => (b.starred ? 1 : 0) - (a.starred ? 1 : 0) || b.netVotes - a.netVotes);
      case 'votes':
        return safe.sort((a, b) => b.netVotes - a.netVotes || b.abWins - a.abWins);
      case 'ab-wins':
        return safe.sort((a, b) => b.abWins - a.abWins || b.winRate - a.winRate);
      default:
        return safe;
    }
  }, [data, sortMode]);

  const modes: { key: SortMode; label: string; icon: typeof Star }[] = [
    { key: 'bt', label: 'Bradley–Terry', icon: Sigma },
    { key: 'stars', label: 'Starred', icon: Star },
    { key: 'votes', label: 'Net Votes', icon: ThumbsUp },
    { key: 'ab-wins', label: 'A/B Wins', icon: Trophy },
  ];

  const k = data?.kpis;
  const readiness = k?.control.readiness ?? 'red';
  const readinessCls =
    readiness === 'green'
      ? 'bg-emerald-100 text-emerald-800'
      : readiness === 'amber'
        ? 'bg-amber-100 text-amber-800'
        : 'bg-red-100 text-red-800';

  const scatterData = useMemo(
    () =>
      (data?.slides ?? []).map((s) => ({
        x: s.pc1,
        y: s.pc2,
        name: `S${s.pageNumber}`,
        starred: s.starred,
      })),
    [data]
  );

  return (
    <div className="mx-auto max-w-[1200px] px-4 py-8">
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
        <h1 className="font-display text-3xl font-bold tracking-tight text-primary">Results Dashboard</h1>
        <p className="mt-1 text-muted-foreground">
          Bradley–Terry ranking, DMAIC KPIs and PCA across all reviews and A/B sessions.
        </p>
        {data?.meta && (
          <p className="mt-1 font-mono text-xs text-muted-foreground">
            {data.meta.docNumber} · {data.meta.classification} · {data.meta.method}
          </p>
        )}
      </motion.div>

      {/* Controls */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap gap-2">
          {modes.map((m) => {
            const Icon = m.icon;
            return (
              <button
                key={m.key}
                onClick={() => setSortMode(m.key)}
                className={cn(
                  'flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all',
                  sortMode === m.key
                    ? 'bg-primary text-primary-foreground shadow-sm'
                    : 'bg-secondary text-secondary-foreground hover:bg-accent'
                )}
              >
                <Icon className="h-4 w-4" />
                {m.label}
              </button>
            );
          })}
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={fetchResults}
            className="flex items-center gap-2 rounded-lg border bg-card px-3 py-2 text-sm font-medium shadow-sm transition-all hover:bg-secondary"
            title="Refresh"
          >
            <RefreshCw className={cn('h-4 w-4', loading && 'animate-spin')} />
          </button>
          <button
            onClick={() => download('/api/export-csv')}
            className="flex items-center gap-2 rounded-lg border bg-card px-4 py-2 text-sm font-medium shadow-sm transition-all hover:bg-secondary"
          >
            <Download className="h-4 w-4" /> CSV
          </button>
          <button
            onClick={() => download('/api/export?format=json')}
            className="flex items-center gap-2 rounded-lg border bg-card px-4 py-2 text-sm font-medium shadow-sm transition-all hover:bg-secondary"
          >
            <Download className="h-4 w-4" /> JSON
          </button>
          <button
            onClick={() => download('/api/export?format=yaml')}
            className="flex items-center gap-2 rounded-lg border bg-card px-4 py-2 text-sm font-medium shadow-sm transition-all hover:bg-secondary"
          >
            <Download className="h-4 w-4" /> YAML
          </button>
        </div>
      </div>

      {loading && !data && (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      )}

      {data && k && (
        <>
          {/* DMAIC */}
          <section className="mb-10">
            <div className="mb-3 flex flex-wrap items-center gap-3">
              <h2 className="font-display text-xl font-bold text-primary">DMAIC KPIs</h2>
              <span className={cn('rounded-full px-3 py-1 text-xs font-semibold uppercase', readinessCls)}>
                Readiness: {readiness}
              </span>
              <span className="font-mono text-xs text-muted-foreground">
                σ-level proxy {fmt(k.control.sigmaLevelProxy, 1)}
              </span>
            </div>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              <Phase title="Define">
                <KpiCard label="Slides" value={String(k.define.slides)} hint={`${k.define.groups.length} themes`} />
                <KpiCard label="Sessions" value={String(k.define.sessions)} />
                <KpiCard label="Comparisons" value={String(k.define.comparisons)} />
                <KpiCard label="Ties" value={String(k.define.ties)} />
              </Phase>
              <Phase title="Measure">
                <KpiCard label="Starred" value={String(k.measure.starredCount)} hint={pct(k.measure.starRate)} />
                <KpiCard label="Votes" value={String(k.measure.totalVotes)} />
                <KpiCard label="Approval" value={pct(k.measure.approvalRate)} hint="up / (up+down)" />
                <KpiCard label="Neutral rate" value={pct(k.measure.neutralRate)} />
                <KpiCard label="Pair coverage" value={pct(k.measure.coverage)} hint="of 105 pairs" />
                <KpiCard label="Comp./slide" value={fmt(k.measure.meanComparisonsPerSlide, 1)} />
              </Phase>
              <Phase title="Analyze">
                <KpiCard
                  label="Transitivity"
                  value={pct(k.analyze.transitivityConsistency)}
                  hint={`${k.analyze.cyclicTriads}/${k.analyze.observedTriads} cyclic triads`}
                />
                <KpiCard label="BT spread" value={fmt(k.analyze.btSpread)} hint="max−min ln π" />
                <KpiCard label="Mean SE" value={fmt(k.analyze.meanStdError)} hint="ln π" />
                <KpiCard
                  label="PCA var."
                  value={`${pct(k.analyze.pc1Variance)} / ${pct(k.analyze.pc2Variance)}`}
                  hint="PC1 / PC2"
                />
              </Phase>
              <Phase title="Improve">
                <KpiCard label="Top slides" value={k.improve.topSlides.map((n) => `S${n}`).join(' ') || '–'} />
                <KpiCard label="Bottom slides" value={k.improve.bottomSlides.map((n) => `S${n}`).join(' ') || '–'} />
                <div className="col-span-2">
                  <KpiCard
                    label="Under-sampled"
                    value={k.improve.underSampled.length ? k.improve.underSampled.map((n) => `S${n}`).join(' ') : 'none'}
                    hint="run more A/B rounds on these"
                  />
                </div>
              </Phase>
              <div className="rounded-xl border bg-card/50 p-4 md:col-span-2 xl:col-span-2">
                <h3 className="font-display mb-3 text-sm font-bold uppercase tracking-wide text-primary">Control</h3>
                <ul className="space-y-1 text-sm">
                  {k.control.notes.map((n, i) => (
                    <li key={i} className="flex gap-2">
                      <span className="text-primary">•</span>
                      <span>{n}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </section>

          {/* Ranking */}
          <section className="mb-10">
            <h2 className="font-display mb-3 text-xl font-bold text-primary">Slide ranking</h2>
            <div className="overflow-x-auto rounded-xl border" style={{ boxShadow: 'var(--shadow-sm)' }}>
              <table className="w-full min-w-[820px] text-sm">
                <thead className="bg-secondary text-left text-xs uppercase tracking-wide text-secondary-foreground">
                  <tr>
                    <th className="px-3 py-2">#</th>
                    <th className="px-3 py-2">Slide</th>
                    <th className="px-3 py-2">Theme</th>
                    <th className="px-3 py-2 text-right">Net</th>
                    <th className="px-3 py-2 text-right">↑ / ↔ / ↓</th>
                    <th className="px-3 py-2 text-right">W / T / L</th>
                    <th className="px-3 py-2 text-right">Win %</th>
                    <th className="px-3 py-2 text-right">BT π</th>
                    <th className="px-3 py-2 text-right">ln π ± SE</th>
                    <th className="px-3 py-2 text-right">BT rank</th>
                  </tr>
                </thead>
                <tbody>
                  {sorted.map((s: SlideStat, i) => (
                    <motion.tr
                      key={s.id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: i * 0.03 }}
                      className={cn('border-t', i === 0 ? 'bg-primary/10' : 'bg-card')}
                    >
                      <td className="px-3 py-2 font-mono font-bold">{i + 1}</td>
                      <td className="px-3 py-2">
                        <div className="flex items-center gap-3">
                          <div className="relative aspect-[16/9] w-16 shrink-0 overflow-hidden rounded bg-muted">
                            <Image
                              src={`/slides/${s.imageFilename}`}
                              alt={s.title ? `Slide ${s.pageNumber}: ${s.title}` : `Slide ${s.pageNumber}`}
                              fill
                              className="object-contain"
                              sizes="64px"
                            />
                          </div>
                          <div className="min-w-0">
                            <div className="flex items-center gap-1 font-medium">
                              Slide {s.pageNumber}
                              {s.starred && <Star className="h-3.5 w-3.5 fill-primary text-primary" />}
                            </div>
                            {s.title && <div className="truncate text-xs text-muted-foreground">{s.title}</div>}
                          </div>
                        </div>
                      </td>
                      <td className="px-3 py-2 text-xs text-muted-foreground">{s.groupName ?? '–'}</td>
                      <td className="px-3 py-2 text-right font-mono font-bold">{s.netVotes}</td>
                      <td className="px-3 py-2 text-right font-mono text-xs">
                        {s.votesUp} / {s.votesNeutral} / {s.votesDown}
                      </td>
                      <td className="px-3 py-2 text-right font-mono text-xs">
                        {s.abWins} / {s.abTies} / {s.abLosses}
                      </td>
                      <td className="px-3 py-2 text-right font-mono">{pct(s.winRate)}</td>
                      <td className="px-3 py-2 text-right font-mono text-primary">{fmt(s.btStrength)}</td>
                      <td className="px-3 py-2 text-right font-mono text-xs">
                        {fmt(s.btLogStrength)} ± {fmt(s.btStdError)}
                      </td>
                      <td className="px-3 py-2 text-right font-mono font-bold text-primary">{s.btRank ?? '–'}</td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* PCA */}
          <section className="mb-10">
            <div className="mb-3 flex items-center gap-2">
              <Activity className="h-5 w-5 text-primary" />
              <h2 className="font-display text-xl font-bold text-primary">PCA — slide feature space</h2>
            </div>
            <div className="grid gap-4 lg:grid-cols-3">
              <div className="rounded-xl border bg-card p-4 lg:col-span-2" style={{ boxShadow: 'var(--shadow-sm)' }}>
                {data.pca.explainedVariance.some((v) => v > 0) ? (
                  <div className="h-[340px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <ScatterChart margin={{ top: 16, right: 16, bottom: 16, left: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#E9D5FF" />
                        <XAxis
                          type="number"
                          dataKey="x"
                          name="PC1"
                          tick={{ fontSize: 11 }}
                          label={{ value: `PC1 (${pct(data.pca.explainedVariance[0])})`, position: 'insideBottom', offset: -8, fontSize: 11 }}
                        />
                        <YAxis
                          type="number"
                          dataKey="y"
                          name="PC2"
                          tick={{ fontSize: 11 }}
                          label={{ value: `PC2 (${pct(data.pca.explainedVariance[1])})`, angle: -90, position: 'insideLeft', fontSize: 11 }}
                        />
                        <ReferenceLine x={0} stroke="#9CA3AF" />
                        <ReferenceLine y={0} stroke="#9CA3AF" />
                        <Tooltip
                          cursor={{ strokeDasharray: '3 3' }}
                          formatter={(v: number) => fmt(v)}
                          labelFormatter={() => ''}
                          contentStyle={{ fontSize: 12 }}
                        />
                        <Scatter data={scatterData} fill="#7030A0">
                          <LabelList dataKey="name" position="top" style={{ fontSize: 10, fill: '#4B5563' }} />
                        </Scatter>
                      </ScatterChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <p className="py-16 text-center text-sm text-muted-foreground">
                    Not enough variation for PCA yet — star, vote or run A/B rounds first.
                  </p>
                )}
              </div>
              <div className="rounded-xl border bg-card p-4" style={{ boxShadow: 'var(--shadow-sm)' }}>
                <h3 className="font-display mb-2 text-sm font-bold text-primary">Loadings</h3>
                <table className="w-full text-xs">
                  <thead className="text-left text-muted-foreground">
                    <tr>
                      <th className="py-1">Feature</th>
                      <th className="py-1 text-right">PC1</th>
                      <th className="py-1 text-right">PC2</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.pca.features.map((f, j) => (
                      <tr key={f} className="border-t">
                        <td className="py-1 font-medium">{f}</td>
                        <td className="py-1 text-right font-mono">{fmt(data.pca.loadings[0]?.[j])}</td>
                        <td className="py-1 text-right font-mono">{fmt(data.pca.loadings[1]?.[j])}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p className="mt-3 text-[11px] text-muted-foreground">
                  Features are standardised before decomposition. PC1 typically captures overall preference; PC2 separates
                  explicit votes from pairwise wins.
                </p>
              </div>
            </div>
          </section>

          {/* Reasons */}
          <section className="mb-6">
            <div className="mb-3 flex items-center gap-2">
              <MessageSquare className="h-5 w-5 text-primary" />
              <h2 className="font-display text-xl font-bold text-primary">A/B reasons ({data.reasons.length})</h2>
            </div>
            {data.reasons.length === 0 ? (
              <p className="text-sm text-muted-foreground">No reasons recorded yet — add one during an A/B round.</p>
            ) : (
              <ul className="space-y-2">
                {data.reasons
                  .slice()
                  .reverse()
                  .map((r, i) => (
                    <li key={i} className="rounded-lg border bg-card px-4 py-3 text-sm" style={{ boxShadow: 'var(--shadow-sm)' }}>
                      <div className="mb-1 font-mono text-xs text-muted-foreground">
                        S{r.slideA} vs S{r.slideB} → {r.isTie ? 'tie' : `S${r.winner}`} · {r.at.slice(0, 16).replace('T', ' ')}
                      </div>
                      <div>{r.reason}</div>
                    </li>
                  ))}
              </ul>
            )}
          </section>
        </>
      )}
    </div>
  );
}
