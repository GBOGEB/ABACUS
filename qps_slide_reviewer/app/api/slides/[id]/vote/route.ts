export const dynamic = 'force-dynamic';

import { NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';

export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const slideId = parseInt(id, 10);
    if (isNaN(slideId)) {
      return NextResponse.json({ error: 'Invalid id' }, { status: 400 });
    }
    const body = await request?.json();
    const direction = body?.direction;
    if (direction !== 'up' && direction !== 'down' && direction !== 'neutral') {
      return NextResponse.json({ error: 'Invalid direction' }, { status: 400 });
    }
    const data =
      direction === 'up'
        ? { votesUp: { increment: 1 } }
        : direction === 'down'
          ? { votesDown: { increment: 1 } }
          : { votesNeutral: { increment: 1 } };
    const updated = await prisma.slide.update({ where: { id: slideId }, data });
    return NextResponse.json(updated);
  } catch (err: any) {
    console.error('POST /api/slides/[id]/vote error:', err);
    return NextResponse.json({ error: 'Failed to vote' }, { status: 500 });
  }
}
