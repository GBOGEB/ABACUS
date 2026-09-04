import { prisma } from '@/lib/prisma';
import { bradleyTerry, pca, dmaicKpis, type SlideRow, type Comparison } from '@/lib/stats';

export async function buildAnalytics() {
  const [slides, results, sessions] = await Promise.all([
    prisma.slide.findMany({ orderBy: { pageNumber: 'asc' } }),
    prisma.abResult.findMany({ orderBy: { createdAt: 'asc' } }),
    prisma.abSession.count(),
  ]);

  const rows: SlideRow[] = slides.map((s) => ({
    id: s.id,
    pageNumber: s.pageNumber,
    imageFilename: s.imageFilename,
    title: s.title,
    groupName: s.groupName,
    starred: s.starred,
    votesUp: s.votesUp,
    votesDown: s.votesDown,
    votesNeutral: s.votesNeutral,
  }));
  const comps: Comparison[] = results.map((r) => ({
    slideAId: r.slideAId,
    slideBId: r.slideBId,
    winnerId: r.winnerId,
    isTie: r.isTie,
  }));

  const ids = rows.map((r) => r.id);
  const bt = bradleyTerry(ids, comps);
  const btById = new Map(bt.map((b) => [b.id, b]));

  const features = ['starred', 'netVotes', 'approval', 'btLogStrength', 'winRate'];
  const matrix = rows.map((r) => {
    const b = btById.get(r.id)!;
    const tot = r.votesUp + r.votesDown;
    return [r.starred ? 1 : 0, r.votesUp - r.votesDown, tot ? r.votesUp / tot : 0.5, b.logStrength, b.winRate];
  });
  const pcaRes = pca(ids, features, matrix, 3);
  const pcaById = new Map(pcaRes.scores.map((s) => [s.id, s]));
  const kpis = dmaicKpis(rows, comps, sessions, bt, pcaRes);

  const btRanked = [...bt].sort((a, b) => b.strength - a.strength);
  const rankById = new Map(btRanked.map((b, i) => [b.id, i + 1]));

  const slideStats = rows.map((r) => {
    const b = btById.get(r.id)!;
    const p = pcaById.get(r.id)!;
    return {
      ...r,
      netVotes: r.votesUp - r.votesDown,
      abWins: b.wins,
      abLosses: b.losses,
      abTies: b.ties,
      abComparisons: b.comparisons,
      winRate: b.winRate,
      btStrength: b.strength,
      btLogStrength: b.logStrength,
      btStdError: Number.isFinite(b.stdError) ? b.stdError : null,
      btRank: rankById.get(r.id) ?? null,
      pc1: p.pc1,
      pc2: p.pc2,
      pc3: p.pc3,
    };
  });

  const reasons = results
    .filter((r) => r.reason && r.reason.trim())
    .map((r) => ({
      sessionId: r.sessionId,
      slideA: slides.find((s) => s.id === r.slideAId)?.pageNumber ?? r.slideAId,
      slideB: slides.find((s) => s.id === r.slideBId)?.pageNumber ?? r.slideBId,
      winner: r.winnerId ? slides.find((s) => s.id === r.winnerId)?.pageNumber ?? r.winnerId : null,
      isTie: r.isTie,
      reason: r.reason,
      at: r.createdAt.toISOString(),
    }));

  return {
    meta: {
      deck: 'QPS- 3D _DKO.pptx',
      docNumber: 'SCK CEN/101648634',
      classification: 'ISC: Restricted',
      generatedAt: new Date().toISOString(),
      method: 'Bradley-Terry (MM, prior 0.1, ties = half win) + PCA (standardised, power iteration)',
    },
    style: {
      primaryColor: '#7030A0',
      secondaryColor: '#F3E8FF',
      headingFont: 'Plus Jakarta Sans',
      bodyFont: 'DM Sans',
      monoFont: 'JetBrains Mono',
      footer: { logo: 'bottom-left', docNumber: 'after logo', slideNumber: 'bottom-right', classification: 'bottom-right below number' },
    },
    kpis,
    pca: { features: pcaRes.features, explainedVariance: pcaRes.explainedVariance, loadings: pcaRes.components },
    slides: slideStats,
    reasons,
  };
}

export type Analytics = Awaited<ReturnType<typeof buildAnalytics>>;
