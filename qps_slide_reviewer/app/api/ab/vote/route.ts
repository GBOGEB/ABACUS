export const dynamic = 'force-dynamic';

import { NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';

export async function POST(request: Request) {
  try {
    const body = await request?.json();
    const { sessionId, slideAId, slideBId, winnerId, isTie, reason } = body ?? {};

    if (!sessionId || !slideAId || !slideBId || (!winnerId && !isTie)) {
      return NextResponse.json({ error: 'Missing fields' }, { status: 400 });
    }

    const [result] = await prisma.$transaction([
      prisma.abResult.create({
        data: {
          sessionId: Number(sessionId),
          slideAId: Number(slideAId),
          slideBId: Number(slideBId),
          winnerId: isTie ? null : Number(winnerId),
          isTie: Boolean(isTie),
          reason: typeof reason === 'string' && reason.trim() ? reason.trim().slice(0, 500) : null,
        },
      }),
      prisma.abSession.update({
        where: { id: Number(sessionId) },
        data: { currentRound: { increment: 1 } },
      }),
    ]);

    return NextResponse.json(result);
  } catch (err: any) {
    console.error('POST /api/ab/vote error:', err);
    return NextResponse.json({ error: 'Failed to record vote' }, { status: 500 });
  }
}
