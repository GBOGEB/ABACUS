export const dynamic = 'force-dynamic';

import { NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';

export async function GET() {
  try {
    const slides = await prisma.slide.findMany({
      orderBy: { pageNumber: 'asc' },
      include: {
        abWins: true,
      },
    });

    const result = (slides ?? [])?.map((s: any) => ({
      id: s?.id,
      pageNumber: s?.pageNumber,
      imageFilename: s?.imageFilename,
      starred: s?.starred ?? false,
      votesUp: s?.votesUp ?? 0,
      votesDown: s?.votesDown ?? 0,
      netVotes: (s?.votesUp ?? 0) - (s?.votesDown ?? 0),
      abWins: s?.abWins?.length ?? 0,
    }));

    return NextResponse.json(result ?? []);
  } catch (err: any) {
    console.error('GET /api/results error:', err);
    return NextResponse.json({ error: 'Failed to fetch results' }, { status: 500 });
  }
}
