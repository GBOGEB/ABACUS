import { z } from 'zod';

export const PressureAxisSchema = z.enum([
  'scope','frequency','coverage','workers','evidence','schema','runtime','qa','binary_freshness'
]);
export const PressureLevelSchema = z.enum(['LOW','MEDIUM','HIGH','CRITICAL']);
export const RecommendationActionSchema = z.enum([
  'HOLD','NARROW','EXPAND_SCOPE','INCREASE_FREQUENCY','DECREASE_FREQUENCY',
  'ADD_COVERAGE','ADD_WORKERS','REDUCE_WORKERS','ESCALATE_EVIDENCE_RECOVERY',
  'REGENERATE_BINARIES','REQUIRE_HUMAN_REVIEW'
]);
export const ReversePressureSignalSchema = z.object({
  axis: PressureAxisSchema,
  level: PressureLevelSchema,
  score: z.number().min(0).max(1),
  residual: z.number().min(0).max(1),
  sourceMetrics: z.array(z.string()).min(1),
  rationale: z.string().min(1),
});
export const ThreeP3RecommendationSchema = z.object({
  action: RecommendationActionSchema,
  targetAxis: PressureAxisSchema,
  proposedDelta: z.number().min(-1).max(1),
  boundedBy: z.array(z.string()).min(1),
  requiresChildAcceptance: z.boolean(),
  autoExecutable: z.boolean(),
  expectedBenefit: z.number().min(0).max(1),
  confidence: z.number().min(0).max(1),
});
export const ThreeP3SelfEvaluationSchema = z.object({
  moniker: z.literal('3PR'),
  scheme: z.literal('3P3'),
  pulse: z.enum(['P1_QPS','P2_KEB','P3_DOW','ROLLUP']),
  payloadSha256: z.string().regex(/^[a-f0-9]{64}$/),
  priorPulseReceiptSha256: z.string().regex(/^[a-f0-9]{64}$/).optional(),
  reversePressure: z.array(ReversePressureSignalSchema).min(1),
  recommendations: z.array(ThreeP3RecommendationSchema),
  dovScore: z.number().min(0).max(1),
  pcaResidualScore: z.number().min(0).max(1),
  btPriorityScore: z.number().min(0).max(1),
  stopConditions: z.array(z.string()),
  nextPulseAllowed: z.boolean(),
  generatedAt: z.string().datetime(),
});
export type ThreeP3SelfEvaluation = z.infer<typeof ThreeP3SelfEvaluationSchema>;
