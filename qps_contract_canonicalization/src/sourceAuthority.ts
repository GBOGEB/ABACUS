import { z } from "zod";

export const SourceClass = z.enum([
  "SSOT",
  "CONTRACT_REQUIREMENT_MIRROR",
  "SOURCE_DOCUMENT",
  "SOURCE_RECEIPT",
  "GENERATED_VIEW",
  "COMPARATIVE",
  "TEST",
  "SAMPLE",
  "HISTORICAL",
  "HARDCODED_FIXTURE",
]);

export const InputMode = z.enum(["PRODUCTION", "COMPARATIVE", "TEST", "SAMPLE"]);

export const SourceBinding = z.object({
  id: z.string().min(1),
  sourceClass: SourceClass,
  pathOrLogicalRef: z.string().min(1),
  sha256: z.string().regex(/^[a-f0-9]{64}$/).optional(),
  authorityUse: z.enum(["AUTHORITATIVE", "SUPPORTING_ONLY", "NON_AUTHORITATIVE"]),
  productionCreditAllowed: z.boolean(),
  freshnessState: z.enum(["CURRENT", "UNKNOWN", "STALE", "NOT_APPLICABLE"]).default("UNKNOWN"),
  notes: z.string().optional(),
});

export const SourceAuthorityContract = z.object({
  schemaVersion: z.literal("1.0.0"),
  mode: InputMode,
  canonicalAuthority: z.object({
    logicalId: z.string().min(1),
    sourceClass: z.literal("SSOT"),
    pathOrLogicalRef: z.string().min(1),
    authorityUse: z.literal("AUTHORITATIVE"),
  }),
  localProjection: z.object({
    path: z.string().min(1),
    sourceClass: z.literal("GENERATED_VIEW"),
    authorityUse: z.literal("NON_AUTHORITATIVE"),
  }),
  sources: z.array(SourceBinding),
}).superRefine((value, ctx) => {
  const nonAuthority = new Set([
    "GENERATED_VIEW", "COMPARATIVE", "TEST", "SAMPLE", "HISTORICAL", "HARDCODED_FIXTURE"
  ]);

  for (const source of value.sources) {
    if (nonAuthority.has(source.sourceClass) && source.authorityUse === "AUTHORITATIVE") {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: `${source.id}: non-authoritative source class cannot be authoritative`,
      });
    }
    if (nonAuthority.has(source.sourceClass) && source.productionCreditAllowed) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: `${source.id}: fixture/view/history source cannot earn production credit`,
      });
    }
    if (source.sourceClass === "CONTRACT_REQUIREMENT_MIRROR" && source.authorityUse !== "SUPPORTING_ONLY") {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: `${source.id}: contract mirror must remain SUPPORTING_ONLY`,
      });
    }
  }

  if (value.mode === "PRODUCTION") {
    const authoritativeInputs = value.sources.filter(s => s.authorityUse === "AUTHORITATIVE");
    if (authoritativeInputs.length > 0) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "production authority must come from canonicalAuthority only; source bindings are supporting/non-authoritative",
      });
    }
  }
});

export type SourceAuthorityContract = z.infer<typeof SourceAuthorityContract>;
