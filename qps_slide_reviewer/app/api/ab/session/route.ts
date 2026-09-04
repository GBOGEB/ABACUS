export const dynamic = 'force-dynamic';

import { NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';
import crypto from 'crypto';

export async function POST(request: Request) {
  try {
    let body: any = {};
    try {
      body = await request.json();
    } catch {
      body = {};
    }
    const rounds = Math.min(60, Math.max(3, parseInt(String(body?.rounds ?? 10), 10) || 10));
    const groupName = typeof body?.group === 'string' && body.group.trim() ? body.group.trim() : null;

    const session = await prisma.abSession.create({
      data: {
        sessionToken: crypto.randomUUID(),
        totalRounds: rounds,
        currentRound: 0,
        groupName,
      },
    });
    return NextResponse.json(session);
  } catch (err: any) {
    console.error('POST /api/ab/session error:', err);
    return NextResponse.json({ error: 'Failed to create session' }, { status: 500 });
  }
}
