/**
 * gg_MATH Bradley-Terry consumer admission preflight.
 * Mathematical authority: GBOGEB/gg_MATH/kernels/bradley_terry.py.
 * A positive result is ONLY graph eligibility, never an authoritative fit.
 */
export interface BtComparison {
  slideAId: number;
  slideBId: number;
  winnerId: number | null;
  isTie: boolean;
}
export type BtAdmissionStatus = 'BT_PREFLIGHT_ELIGIBLE' | 'DEFER_NO_USABLE_COMPARISONS' |
  'DEFER_DISCONNECTED_COMPARISON_GRAPH' | 'DEFER_NO_FINITE_MLE' |
  'DEFER_INVALID_COMPARISON';
export interface BtAdmission {
  status: BtAdmissionStatus;
  eligible: boolean;
  decisiveComparisons: number;
  authority: 'CONSUMER_PREFLIGHT_ONLY';
  provider: 'GBOGEB/gg_MATH';
}
function reached(start: number, graph: Map<number, Set<number>>): Set<number> {
  const seen = new Set<number>(), queue = [start];
  while (queue.length) {
    const current = queue.pop()!;
    if (seen.has(current)) continue;
    seen.add(current);
    for (const next of graph.get(current) ?? []) if (!seen.has(next)) queue.push(next);
  }
  return seen;
}
export function assessBtAdmission(ids: readonly number[], comps: readonly BtComparison[]): BtAdmission {
  const verdict = (status: BtAdmissionStatus, decisiveComparisons: number): BtAdmission => ({
    status, eligible: status === 'BT_PREFLIGHT_ELIGIBLE', decisiveComparisons,
    authority: 'CONSUMER_PREFLIGHT_ONLY', provider: 'GBOGEB/gg_MATH'
  });
  if (ids.length < 2 || new Set(ids).size !== ids.length ||
      ids.some((id) => !Number.isSafeInteger(id))) return verdict('DEFER_INVALID_COMPARISON', 0);
  const nodes = new Set(ids);
  const forward = new Map(ids.map((id) => [id, new Set<number>()]));
  const reverse = new Map(ids.map((id) => [id, new Set<number>()]));
  const undirected = new Map(ids.map((id) => [id, new Set<number>()]));
  let decisive = 0;
  for (const c of comps) {
    if (!nodes.has(c.slideAId) || !nodes.has(c.slideBId) || c.slideAId === c.slideBId ||
        (c.winnerId !== null && c.winnerId !== c.slideAId && c.winnerId !== c.slideBId) ||
        (c.isTie && c.winnerId !== null) || (!c.isTie && c.winnerId === null))
      return verdict('DEFER_INVALID_COMPARISON', decisive);
    if (c.isTie) continue;
    const winner = c.winnerId!;
    const loser = winner === c.slideAId ? c.slideBId : c.slideAId;
    forward.get(winner)!.add(loser);
    reverse.get(loser)!.add(winner);
    undirected.get(winner)!.add(loser);
    undirected.get(loser)!.add(winner);
    decisive++;
  }
  if (decisive === 0) return verdict('DEFER_NO_USABLE_COMPARISONS', 0);
  if (reached(ids[0], undirected).size !== ids.length)
    return verdict('DEFER_DISCONNECTED_COMPARISON_GRAPH', decisive);
  if (reached(ids[0], forward).size !== ids.length || reached(ids[0], reverse).size !== ids.length)
    return verdict('DEFER_NO_FINITE_MLE', decisive);
  return verdict('BT_PREFLIGHT_ELIGIBLE', decisive);
}
