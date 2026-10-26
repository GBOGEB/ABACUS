/** Raw comparison telemetry; never a model fit or mathematical authority. */
import type { BtComparison } from './bt_admission';

export interface BtObserved {
  wins: number;
  losses: number;
  ties: number;
  comparisons: number;
  winRate: number;
}
export function countBtObservations(ids: readonly number[], comps: readonly BtComparison[]): Map<number, BtObserved> {
  const mutable = new Map(ids.map((id) => [id, {
    wins: 0, losses: 0, ties: 0, comparisons: 0, winRate: 0
  }]));
  for (const c of comps) {
    const a = mutable.get(c.slideAId);
    const b = mutable.get(c.slideBId);
    if (!a || !b || c.slideAId === c.slideBId) continue;
    if (c.isTie) {
      if (c.winnerId !== null) continue;
      a.ties++; b.ties++; a.comparisons++; b.comparisons++;
    } else {
      if (c.winnerId !== c.slideAId && c.winnerId !== c.slideBId) continue;
      const w = c.winnerId === c.slideAId ? a : b;
      const l = c.winnerId === c.slideAId ? b : a;
      w.wins++; l.losses++; a.comparisons++; b.comparisons++;
    }
  }
  for (const counts of mutable.values()) {
    const decisive = counts.wins + counts.losses;
    counts.winRate = decisive ? counts.wins / decisive : 0;
  }
  return mutable;
}
