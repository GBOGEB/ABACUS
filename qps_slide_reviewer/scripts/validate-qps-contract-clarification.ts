import {
  CanonicalRequirementSetSchema,
  canonicalDenominator,
} from "../lib/qps-contract-clarification-schema";

const valid = {
  schemaVersion: "1.1" as const,
  authority: "QPS_child" as const,
  requirements: [
    {
      canonicalRequirementId: "CANON-QPS-QSN-001",
      sourceFragmentIds: ["RTM-045", "PDF-4.2.5-L1"],
      sourceRtmIds: ["RTM-045"],
      sourceOfferIds: [],
      sourcePdfLocators: ["Addendum II §4.2.5"],
      applicabilityState: "ITEM_OBSOLETE" as const,
      contractChangeClass: "SCOPE_OBSOLETE_NOT_APPLICABLE" as const,
      ownerClarification: "QSN/LN2 precooling is not part of selected QPS scope.",
      contractChangeNote: "Owner scope clarification to be formalised in negotiated contract/clarification.",
      obsolescenceReason: "No QSN/LN2 precooling architecture in selected scope.",
      evidenceClass: "OWNER_CLARIFICATION" as const,
      scoreEligible: false,
      penaltyEligible: false,
      canonicalScoreWeight: 1,
      bidderComplianceCredit: 0,
    },
    {
      canonicalRequirementId: "CANON-QPS-TABLE9-001",
      sourceFragmentIds: ["RTM-030", "TABLE9-DESIGN-POINT"],
      sourceRtmIds: ["RTM-030"],
      sourceOfferIds: [],
      sourcePdfLocators: ["Addendum II Table 9"],
      applicabilityState: "APPLICABLE" as const,
      contractChangeClass: "DUPLICATE_OR_SPLIT_RTM_NORMALIZATION" as const,
      ownerClarification: "",
      contractChangeNote: "",
      obsolescenceReason: "",
      evidenceClass: "CONTRACT" as const,
      scoreEligible: true,
      penaltyEligible: true,
      canonicalScoreWeight: 1,
      bidderComplianceCredit: 0,
    },
  ],
};

CanonicalRequirementSetSchema.parse(valid);
if (canonicalDenominator(valid) !== 1) {
  throw new Error("Expected denominator=1 after excluding obsolete QSN requirement");
}

const invalidObsoleteScored = structuredClone(valid);
invalidObsoleteScored.requirements[0].scoreEligible = true;
if (CanonicalRequirementSetSchema.safeParse(invalidObsoleteScored).success) {
  throw new Error("Regression: obsolete QSN row was allowed back into scoring");
}

const invalidOwnerCredit = structuredClone(valid);
invalidOwnerCredit.requirements[0].bidderComplianceCredit = 1;
if (CanonicalRequirementSetSchema.safeParse(invalidOwnerCredit).success) {
  throw new Error("Regression: owner clarification was allowed to create bidder compliance credit");
}

const invalidDoubleMembership = structuredClone(valid);
invalidDoubleMembership.requirements.push({
  ...invalidDoubleMembership.requirements[1],
  canonicalRequirementId: "CANON-QPS-TABLE9-DUPLICATE",
  sourceFragmentIds: ["TABLE9-DESIGN-POINT"],
});
if (CanonicalRequirementSetSchema.safeParse(invalidDoubleMembership).success) {
  throw new Error("Regression: one source fragment was allowed in two active canonical requirements");
}

console.log("QPS contract clarification/canonicalization Zod validation PASS");
