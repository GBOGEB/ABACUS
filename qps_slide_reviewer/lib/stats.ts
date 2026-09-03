/**
 * Statistics helpers: Bradley–Terry ranking (MM algorithm), PCA (power iteration),
 * DMAIC-style KPI computation and a minimal YAML serializer.
 * Pure TypeScript — no external dependencies so it runs in the standalone build.
 */

export interface SlideRow {
  id: number;
  pageNumber: number;
  imageFilename: string;
  title: string | null;
  groupName: string | null;
  starred: boolean;
  votesUp: number;
  votesDown: number;
  votesNeutral: number;
}

export interface Comparison {
  slideAId: number;
  slideBId: number;
  winnerId: number | null;
  isTie: boolean;
}

export interface BtResult {
  id: number;
  strength: number; // π_i (normalised so mean = 1)
  logStrength: number; // ln π_i (0 = average)
  wins: number;
  losses: number;
  ties: number;
  comparisons: number;
  winRate: number; // wins / decisive comparisons
  stdError: number; // approx SE of logStrength (Fisher information)
}

// ---------- Bradley–Terry ----------
export function bradleyTerry(ids: number[], comps: Comparison[], iterations = 200): BtResult[] {
  const n = ids.length;
  const idx = new Map<number, number>();
  ids.forEach((id, i) => idx.set(id, i));
  const wins = new Array(n).fill(0);
  const losses = new Array(n).fill(0);
  const ties = new Array(n).fill(0);
  // pair counts n_ij (times i and j were compared, decisive only; ties count half to each)
  const nij: number[][] = Array.from({ length: n }, () => new Array(n).fill(0));
  const wij: number[][] = Array.from({ length: n }, () => new Array(n).fill(0)); // i beat j

  for (const c of comps) {
    const a = idx.get(c.slideAId);
    const b = idx.get(c.slideBId);
    if (a === undefined || b === undefined || a === b) continue;
    if (c.isTie || c.winnerId == null) {
      ties[a]++; ties[b]++;
      // treat tie as half win each
      wij[a][b] += 0.5; wij[b][a] += 0.5;
      nij[a][b] += 1; nij[b][a] += 1;
      continue;
    }
    const w = idx.get(c.winnerId);
    if (w === undefined) continue;
    const l = w === a ? b : a;
    wins[w]++; losses[l]++;
    wij[w][l] += 1;
    nij[a][b] += 1; nij[b][a] += 1;
  }

  // MM algorithm (Hunter 2004) with a small prior to keep strengths finite
  const prior = 0.1;
  let pi = new Array(n).fill(1);
  for (let it = 0; it < iterations; it++) {
    const next = new Array(n).fill(0);
    for (let i = 0; i < n; i++) {
      let W = prior;
      let denom = 0;
      for (let j = 0; j < n; j++) {
        if (i === j) continue;
        W += wij[i][j];
        if (nij[i][j] > 0) denom += nij[i][j] / (pi[i] + pi[j]);
      }
      denom += prior * 2 / (pi[i] + 1); // prior pseudo-comparison vs strength-1 opponent
      next[i] = W / denom;
    }
    const gm = Math.exp(next.reduce((s, v) => s + Math.log(v), 0) / n);
    pi = next.map((v) => v / gm);
  }

  return ids.map((id, i) => {
    // Fisher information approximation: I_i = Σ_j n_ij * p_ij * (1 - p_ij)
    let info = 0;
    for (let j = 0; j < n; j++) {
      if (i === j || nij[i][j] === 0) continue;
      const p = pi[i] / (pi[i] + pi[j]);
      info += nij[i][j] * p * (1 - p);
    }
    const decisive = wins[i] + losses[i];
    return {
      id,
      strength: pi[i],
      logStrength: Math.log(pi[i]),
      wins: wins[i],
      losses: losses[i],
      ties: ties[i],
      comparisons: decisive + ties[i],
      winRate: decisive > 0 ? wins[i] / decisive : 0,
      stdError: info > 0 ? 1 / Math.sqrt(info) : Infinity,
    };
  });
}

/** Pairwise-consistency: fraction of intransitive triads among fully-observed triads. */
export function transitivityScore(ids: number[], comps: Comparison[]): { triads: number; cyclic: number; consistency: number } {
  const beats = new Map<string, number>();
  for (const c of comps) {
    if (c.isTie || c.winnerId == null) continue;
    const l = c.winnerId === c.slideAId ? c.slideBId : c.slideAId;
    const k = `${c.winnerId}>${l}`;
    beats.set(k, (beats.get(k) ?? 0) + 1);
  }
  const pref = (a: number, b: number): number => {
    const ab = beats.get(`${a}>${b}`) ?? 0;
    const ba = beats.get(`${b}>${a}`) ?? 0;
    if (ab === ba) return 0;
    return ab > ba ? 1 : -1;
  };
  let triads = 0, cyclic = 0;
  for (let i = 0; i < ids.length; i++)
    for (let j = i + 1; j < ids.length; j++)
      for (let k = j + 1; k < ids.length; k++) {
        const ab = pref(ids[i], ids[j]), bc = pref(ids[j], ids[k]), ca = pref(ids[k], ids[i]);
        if (ab === 0 || bc === 0 || ca === 0) continue;
        triads++;
        if (ab === bc && bc === ca) cyclic++;
      }
  return { triads, cyclic, consistency: triads > 0 ? 1 - cyclic / triads : 1 };
}

// ---------- PCA ----------
export interface PcaResult {
  features: string[];
  explainedVariance: number[]; // ratio per component
  components: number[][]; // loadings: components[k][feature]
  scores: { id: number; pc1: number; pc2: number }[];
}

export function pca(ids: number[], features: string[], matrix: number[][], nComponents = 2): PcaResult {
  const n = matrix.length;
  const m = features.length;
  if (n < 2) return { features, explainedVariance: [], components: [], scores: ids.map((id) => ({ id, pc1: 0, pc2: 0 })) };

  // standardise
  const means = features.map((_, j) => matrix.reduce((s, r) => s + r[j], 0) / n);
  const sds = features.map((_, j) => {
    const v = matrix.reduce((s, r) => s + (r[j] - means[j]) ** 2, 0) / (n - 1);
    return Math.sqrt(v) || 1;
  });
  const Z = matrix.map((r) => r.map((v, j) => (v - means[j]) / sds[j]));

  // covariance
  const C: number[][] = Array.from({ length: m }, () => new Array(m).fill(0));
  for (let i = 0; i < m; i++)
    for (let j = 0; j < m; j++) C[i][j] = Z.reduce((s, r) => s + r[i] * r[j], 0) / (n - 1);

  const totalVar = C.reduce((s, row, i) => s + row[i], 0) || 1;
  const comps: number[][] = [];
  const eig: number[] = [];
  let A = C.map((r) => [...r]);
  for (let k = 0; k < Math.min(nComponents, m); k++) {
    let v = new Array(m).fill(0).map((_, i) => 1 + i * 0.01);
    let lambda = 0;
    for (let it = 0; it < 500; it++) {
      const Av = A.map((row) => row.reduce((s, a, j) => s + a * v[j], 0));
      const norm = Math.sqrt(Av.reduce((s, x) => s + x * x, 0));
      if (norm < 1e-12) {
        lambda = 0;
        v = new Array(m).fill(0);
        break;
      }
      v = Av.map((x) => x / norm);
      lambda = norm;
    }
    comps.push(v);
    eig.push(lambda);
    // deflate
    A = A.map((row, i) => row.map((a, j) => a - lambda * v[i] * v[j]));
  }
  const scores = Z.map((r, i) => ({
    id: ids[i],
    pc1: comps[0] ? r.reduce((s, x, j) => s + x * comps[0][j], 0) : 0,
    pc2: comps[1] ? r.reduce((s, x, j) => s + x * comps[1][j], 0) : 0,
  }));
  return { features, explainedVariance: eig.map((e) => e / totalVar), components: comps, scores };
}

// ---------- DMAIC KPIs ----------
export interface DmaicKpis {
  define: { slides: number; groups: string[]; sessions: number; comparisons: number; ties: number };
  measure: {
    starredCount: number;
    starRate: number;
    totalVotes: number;
    approvalRate: number; // up / (up+down)
    neutralRate: number; // neutral / total
    coverage: number; // fraction of possible pairs observed at least once
    meanComparisonsPerSlide: number;
  };
  analyze: {
    transitivityConsistency: number;
    cyclicTriads: number;
    observedTriads: number;
    btSpread: number; // max-min logStrength
    meanStdError: number;
    pc1Variance: number;
    pc2Variance: number;
  };
  improve: { topSlides: number[]; bottomSlides: number[]; underSampled: number[] };
  control: { sigmaLevelProxy: number; readiness: 'red' | 'amber' | 'green'; notes: string[] };
}

export function dmaicKpis(
  slides: SlideRow[],
  comps: Comparison[],
  sessions: number,
  bt: BtResult[],
  pcaRes: PcaResult
): DmaicKpis {
  const n = slides.length;
  const pairsPossible = (n * (n - 1)) / 2;
  const seen = new Set<string>();
  for (const c of comps) seen.add([c.slideAId, c.slideBId].sort((a, b) => a - b).join('-'));
  const up = slides.reduce((s, x) => s + x.votesUp, 0);
  const down = slides.reduce((s, x) => s + x.votesDown, 0);
  const neutral = slides.reduce((s, x) => s + x.votesNeutral, 0);
  const totalVotes = up + down + neutral;
  const trans = transitivityScore(slides.map((s) => s.id), comps);
  const logs = bt.map((b) => b.logStrength);
  const finiteSe = bt.map((b) => b.stdError).filter((x) => Number.isFinite(x));
  const sortedBt = [...bt].sort((a, b) => b.strength - a.strength);
  const pageOf = (id: number) => slides.find((s) => s.id === id)?.pageNumber ?? id;
  const meanComps = n ? bt.reduce((s, b) => s + b.comparisons, 0) / n : 0;
  const underSampled = bt.filter((b) => b.comparisons < Math.max(2, meanComps * 0.5)).map((b) => pageOf(b.id));

  const coverage = pairsPossible ? seen.size / pairsPossible : 0;
  // Sigma-level proxy: consistency mapped onto a 0–6 scale weighted by coverage
  const sigmaProxy = Math.round((trans.consistency * 4 + coverage * 2) * 100) / 100;
  const notes: string[] = [];
  if (coverage < 0.5) notes.push('Pair coverage below 50% — run more A/B rounds for a stable ranking.');
  if (trans.consistency < 0.8 && trans.triads > 0) notes.push('Intransitive preferences detected — review cyclic triads.');
  if (finiteSe.length && finiteSe.reduce((s, x) => s + x, 0) / finiteSe.length > 1) notes.push('Standard errors > 1 — ranking not yet discriminative.');
  if (!notes.length) notes.push('Ranking is stable enough for design decisions.');
  const readiness: DmaicKpis['control']['readiness'] = sigmaProxy >= 4.5 ? 'green' : sigmaProxy >= 3 ? 'amber' : 'red';

  return {
    define: {
      slides: n,
      groups: Array.from(new Set(slides.map((s) => s.groupName ?? 'Ungrouped'))),
      sessions,
      comparisons: comps.length,
      ties: comps.filter((c) => c.isTie).length,
    },
    measure: {
      starredCount: slides.filter((s) => s.starred).length,
      starRate: n ? slides.filter((s) => s.starred).length / n : 0,
      totalVotes,
      approvalRate: up + down > 0 ? up / (up + down) : 0,
      neutralRate: totalVotes > 0 ? neutral / totalVotes : 0,
      coverage,
      meanComparisonsPerSlide: meanComps,
    },
    analyze: {
      transitivityConsistency: trans.consistency,
      cyclicTriads: trans.cyclic,
      observedTriads: trans.triads,
      btSpread: logs.length ? Math.max(...logs) - Math.min(...logs) : 0,
      meanStdError: finiteSe.length ? finiteSe.reduce((s, x) => s + x, 0) / finiteSe.length : 0,
      pc1Variance: pcaRes.explainedVariance[0] ?? 0,
      pc2Variance: pcaRes.explainedVariance[1] ?? 0,
    },
    improve: {
      topSlides: sortedBt.slice(0, 3).map((b) => pageOf(b.id)),
      bottomSlides: sortedBt.slice(-3).reverse().map((b) => pageOf(b.id)),
      underSampled,
    },
    control: { sigmaLevelProxy: sigmaProxy, readiness, notes },
  };
}

// ---------- Minimal YAML serializer ----------
function yamlScalar(v: unknown): string {
  if (v === null || v === undefined) return 'null';
  if (typeof v === 'number') return Number.isFinite(v) ? String(v) : '.inf';
  if (typeof v === 'boolean') return String(v);
  const s = String(v);
  if (s === '' || /[:#\-?\[\]{},&*!|>'"%@`\n]/.test(s) || /^\s|\s$/.test(s) || /^(true|false|null|yes|no|~)$/i.test(s) || /^[\d.+-]/.test(s)) {
    return JSON.stringify(s);
  }
  return s;
}

export function toYaml(value: unknown, indent = 0): string {
  const pad = '  '.repeat(indent);
  if (Array.isArray(value)) {
    if (value.length === 0) return `${pad}[]\n`;
    return value
      .map((item) => {
        if (item !== null && typeof item === 'object') {
          const inner = toYaml(item, indent + 1).replace(/^\s{2}/, '');
          return `${pad}- ${inner.trimStart()}`;
        }
        return `${pad}- ${yamlScalar(item)}\n`;
      })
      .join('');
  }
  if (value !== null && typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>);
    if (entries.length === 0) return `${pad}{}\n`;
    return entries
      .map(([k, v]) => {
        if (v !== null && typeof v === 'object') {
          const isEmpty = Array.isArray(v) ? v.length === 0 : Object.keys(v).length === 0;
          if (isEmpty) return `${pad}${k}: ${Array.isArray(v) ? '[]' : '{}'}\n`;
          return `${pad}${k}:\n${toYaml(v, indent + 1)}`;
        }
        return `${pad}${k}: ${yamlScalar(v)}\n`;
      })
      .join('');
  }
  return `${pad}${yamlScalar(value)}\n`;
}
