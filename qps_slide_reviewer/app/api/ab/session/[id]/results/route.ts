export const dynamic = 'force-dynamic';

import { NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const sessionId = parseInt(id, 10);
    if (isNaN(sessionId)) {
      return NextResponse.json({ error: 'Invalid id' }, { status: 400 });
    }

    const results = await prisma.abResult.findMany({
      where: { sessionId },
      include: { winner: true },
    });

    // Aggregate wins per slide
    const winMap: Record<number, { slideId: number; pageNumber: number; wins: number }> = {};
    for (const r of results ?? []) {
      const wId = r?.winnerId;
      if (!wId) continue;
      if (!winMap[wId]) {
        winMap[wId] = {
          slideId: wId,
          pageNumber: r?.winner?.pageNumber ?? 0,
          wins: 0,
        };
      }
      winMap[wId].wins += 1;
    }

    const ranked = Object.values(winMap ?? {})?.sort(
      (a: any, b: any) => (b?.wins ?? 0) - (a?.wins ?? 0)
    ) ?? [];

    return NextResponse.json(ranked);
  } catch (err: any) {
    console.error('GET /api/ab/session/[id]/results error:', err);
    return NextResponse.json({ error: 'Failed to get results' }, { status: 500 });
  }
}
