export const dynamic = 'force-dynamic';

import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';

/**
 * Returns the next pair for a session. Pair selection is adaptive: among all
 * candidate pairs (optionally within a slide group) it prefers pairs that have
 * been compared least often across ALL sessions, which maximises coverage for
 * the Bradley–Terry fit. Ties in count are broken randomly. Side (A/B) is
 * randomised to avoid position bias.
 */
export async function GET(request: NextRequest) {
  try {
    const sessionId = parseInt(request?.nextUrl?.searchParams?.get('sessionId') ?? '', 10);
    if (isNaN(sessionId)) {
      return NextResponse.json({ error: 'Missing sessionId' }, { status: 400 });
    }

    const session = await prisma.abSession.findUnique({ where: { id: sessionId } });
    if (!session) {
      return NextResponse.json({ error: 'Session not found' }, { status: 404 });
    }

    if ((session.currentRound ?? 0) >= (session.totalRounds ?? 10)) {
      return NextResponse.json({ done: true });
    }

    const slides = await prisma.slide.findMany({
      where: session.groupName ? { groupName: session.groupName } : undefined,
      orderBy: { pageNumber: 'asc' },
    });
    if (slides.length < 2) {
      return NextResponse.json({ error: 'Not enough slides in this group' }, { status: 400 });
    }

    const [allResults, sessionResults] = await Promise.all([
      prisma.abResult.findMany({ select: { slideAId: true, slideBId: true } }),
      prisma.abResult.findMany({ where: { sessionId }, select: { slideAId: true, slideBId: true } }),
    ]);
    const key = (a: number, b: number) => (a < b ? `${a}-${b}` : `${b}-${a}`);
    const counts = new Map<string, number>();
    for (const r of allResults) counts.set(key(r.slideAId, r.slideBId), (counts.get(key(r.slideAId, r.slideBId)) ?? 0) + 1);
    const seenThisSession = new Set(sessionResults.map((r) => key(r.slideAId, r.slideBId)));

    // Build candidate pairs; skip pairs already seen in this session if possible
    type Cand = { a: number; b: number; count: number };
    let cands: Cand[] = [];
    for (let i = 0; i < slides.length; i++)
      for (let j = i + 1; j < slides.length; j++) {
        const k = key(slides[i].id, slides[j].id);
        if (seenThisSession.has(k)) continue;
        cands.push({ a: i, b: j, count: counts.get(k) ?? 0 });
      }
    if (!cands.length) {
      for (let i = 0; i < slides.length; i++)
        for (let j = i + 1; j < slides.length; j++)
          cands.push({ a: i, b: j, count: counts.get(key(slides[i].id, slides[j].id)) ?? 0 });
    }
    const minCount = Math.min(...cands.map((c) => c.count));
    cands = cands.filter((c) => c.count === minCount);
    const pick = cands[Math.floor(Math.random() * cands.length)];
    const swap = Math.random() < 0.5;
    const slideA = swap ? slides[pick.b] : slides[pick.a];
    const slideB = swap ? slides[pick.a] : slides[pick.b];

    return NextResponse.json({
      slideA: { id: slideA.id, pageNumber: slideA.pageNumber, imageFilename: slideA.imageFilename, title: slideA.title },
      slideB: { id: slideB.id, pageNumber: slideB.pageNumber, imageFilename: slideB.imageFilename, title: slideB.title },
      currentRound: (session.currentRound ?? 0) + 1,
      totalRounds: session.totalRounds ?? 10,
      groupName: session.groupName,
    });
  } catch (err: any) {
    console.error('GET /api/ab/pair error:', err);
    return NextResponse.json({ error: 'Failed to get pair' }, { status: 500 });
  }
}
