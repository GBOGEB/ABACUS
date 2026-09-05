import { z } from "zod";

export const ApplicabilityStateSchema = z.enum([
  "APPLICABLE",
  "NOT_APPLICABLE",
  "ITEM_OBSOLETE",
  "SUPERSEDED",
  "CLARIFICATION_PENDING",
]);

export const ContractChangeClassSchema = z.enum([
  "NONE",
  "DISCREPANCY_WRONG_VALUE",
  "TYPO",
  "MINOR_WORDING_CLARIFICATION_NO_MEANING_CHANGE",
  "DUPLICATE_OR_SPLIT_RTM_NORMALIZATION",
  "OWNER_KNOWN_INPUT_CLARIFICATION",
  "SCOPE_OBSOLETE_NOT_APPLICABLE",
  "RISK_REDUCTION_FROM_OWNER_CLARIFICATION",
]);

export const EvidenceClassSchema = z.enum([
  "CONTRACT",
  "SOURCE_SUPPORTED",
  "CONTROLLED",
  "DERIVED",
  "POSTULATED",
  "OWNER_CLARIFICATION",
  "BIDDER_EVIDENCE",
]);

export const CanonicalRequirementSchema = z
  .object({
    canonicalRequirementId: z.string().min(1),
    sourceFragmentIds: z.array(z.string().min(1)).min(1),
    sourceRtmIds: z.array(z.string().regex(/^RTM-\d+$/)).default([]),
    sourceOfferIds: z.array(z.string().regex(/^OFFER-\d+$/)).default([]),
    sourcePdfLocators: z.array(z.string().min(1)).default([]),
    applicabilityState: ApplicabilityStateSchema,
    contractChangeClass: ContractChangeClassSchema,
    ownerClarification: z.string().default(""),
    contractChangeNote: z.string().default(""),
    obsolescenceReason: z.string().default(""),
    evidenceClass: EvidenceClassSchema,
    scoreEligible: z.boolean(),
    penaltyEligible: z.boolean(),
    canonicalScoreWeight: z.number().nonnegative().default(1),
    bidderComplianceCredit: z.number().nonnegative().default(0),
    riskState: z.string().optional(),
  })
  .superRefine((row, ctx) => {
    const inactive = ["NOT_APPLICABLE", "ITEM_OBSOLETE", "SUPERSEDED", "CLARIFICATION_PENDING"].includes(
      row.applicabilityState,
    );

    if (inactive && row.scoreEligible) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["scoreEligible"],
        message: `${row.applicabilityState} rows must not be score eligible`,
      });
    }

    if (inactive && row.penaltyEligible) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["penaltyEligible"],
        message: `${row.applicabilityState} rows must not create missing-evidence/compliance penalties`,
      });
    }

    if (row.evidenceClass === "OWNER_CLARIFICATION" && row.bidderComplianceCredit > 0) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["bidderComplianceCredit"],
        message: "Owner clarification is not bidder evidence and cannot create positive bidder compliance credit",
      });
    }

    if (
      row.contractChangeClass !== "NONE" &&
      row.contractChangeClass !== "DUPLICATE_OR_SPLIT_RTM_NORMALIZATION" &&
      row.contractChangeNote.trim().length === 0
    ) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["contractChangeNote"],
        message: "Contract/owner clarification changes require an explicit contractChangeNote",
      });
    }

    if (row.applicabilityState === "ITEM_OBSOLETE" && row.obsolescenceReason.trim().length === 0) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["obsolescenceReason"],
        message: "ITEM_OBSOLETE rows require an obsolescenceReason",
      });
    }
  });

export const CanonicalRequirementSetSchema = z
  .object({
    schemaVersion: z.literal("1.1"),
    authority: z.literal("QPS_child"),
    requirements: z.array(CanonicalRequirementSchema),
  })
  .superRefine((doc, ctx) => {
    const activeFragmentOwners = new Map<string, string>();
    const canonicalIds = new Set<string>();

    doc.requirements.forEach((row, rowIndex) => {
      if (canonicalIds.has(row.canonicalRequirementId)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ["requirements", rowIndex, "canonicalRequirementId"],
          message: `Duplicate canonicalRequirementId: ${row.canonicalRequirementId}`,
        });
      }
      canonicalIds.add(row.canonicalRequirementId);

      const active = row.applicabilityState === "APPLICABLE";
      if (active) {
        row.sourceFragmentIds.forEach((fragmentId) => {
          const prior = activeFragmentOwners.get(fragmentId);
          if (prior && prior !== row.canonicalRequirementId) {
            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              path: ["requirements", rowIndex, "sourceFragmentIds"],
              message: `Source fragment ${fragmentId} belongs to more than one active canonical requirement (${prior}, ${row.canonicalRequirementId})`,
            });
          }
          activeFragmentOwners.set(fragmentId, row.canonicalRequirementId);
        });
      }
    });
  });

export type CanonicalRequirement = z.infer<typeof CanonicalRequirementSchema>;
export type CanonicalRequirementSet = z.infer<typeof CanonicalRequirementSetSchema>;

export function applicableCanonicalRequirements(input: unknown): CanonicalRequirement[] {
  const parsed = CanonicalRequirementSetSchema.parse(input);
  return parsed.requirements.filter((row) => row.applicabilityState === "APPLICABLE" && row.scoreEligible);
}

export function canonicalDenominator(input: unknown): number {
  return applicableCanonicalRequirements(input).reduce((sum, row) => sum + row.canonicalScoreWeight, 0);
}
