export const dynamic = 'force-dynamic';

import { NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';

export async function POST(request: Request) {
  try {
    const body = await request?.json();
    const { sessionId, slideAId, slideBId, winnerId, isTie, reason } = body ?? {};
    const sessionIdNum = Number(sessionId);
    const slideAIdNum = Number(slideAId);
    const slideBIdNum = Number(slideBId);
    const winnerIdNum = winnerId == null ? null : Number(winnerId);
    const isTieVote = Boolean(isTie);

    if (
      !Number.isInteger(sessionIdNum) ||
      !Number.isInteger(slideAIdNum) ||
      !Number.isInteger(slideBIdNum) ||
      (!isTieVote && !Number.isInteger(winnerIdNum))
    ) {
      return NextResponse.json({ error: 'Missing fields' }, { status: 400 });
    }

    if (!isTieVote && winnerIdNum !== slideAIdNum && winnerIdNum !== slideBIdNum) {
      return NextResponse.json({ error: 'winnerId must match slideAId or slideBId' }, { status: 400 });
    }

    const [result] = await prisma.$transaction([
      prisma.abResult.create({
        data: {
          sessionId: sessionIdNum,
          slideAId: slideAIdNum,
          slideBId: slideBIdNum,
          winnerId: isTieVote ? null : winnerIdNum,
          isTie: isTieVote,
          reason: typeof reason === 'string' && reason.trim() ? reason.trim().slice(0, 500) : null,
        },
      }),
      prisma.abSession.update({
        where: { id: sessionIdNum },
        data: { currentRound: { increment: 1 } },
      }),
    ]);

    return NextResponse.json(result);
  } catch (err: any) {
    console.error('POST /api/ab/vote error:', err);
    return NextResponse.json({ error: 'Failed to record vote' }, { status: 500 });
  }
}
