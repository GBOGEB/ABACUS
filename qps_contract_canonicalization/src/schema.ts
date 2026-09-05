import {z} from "zod";

export const Row=z.object({
  id:z.string().min(1),
  canonicalId:z.string().min(1),
  semanticGroupKey:z.string().min(1),
  applicability:z.enum(["APPLICABLE","NOT_APPLICABLE","OBSOLETE","SUPERSEDED","PENDING_SCOPE_CONFIRMATION"]),
  complianceStatus:z.enum(["PASS","PARTIAL","FAIL","OPEN","NOT_SCORED"]),
  scoreEligible:z.boolean(),
  reviewWeight:z.number().nonnegative(),
  scopeTags:z.array(z.string()),
  overrideEvidence:z.array(z.string()).default([])
}).superRefine((r,c)=>{
  if(["NOT_APPLICABLE","OBSOLETE","SUPERSEDED"].includes(r.applicability)&&(r.scoreEligible||r.reviewWeight!==0||r.complianceStatus!=="NOT_SCORED"))
    c.addIssue({code:z.ZodIssueCode.custom,message:`${r.id}: excluded row leaked into score`});
});

export const CanonicalGroup=z.object({
  canonicalId:z.string().min(1),
  governingRtmIds:z.array(z.string().regex(/^RTM-\d+$/)).min(1),
  sourceFragments:z.array(z.string().min(1)).min(1),
  linkedNonmergedRtmIds:z.array(z.string().regex(/^RTM-\d+$/)).default([]),
  scoreOnce:z.literal(true)
});

export const DenominatorReceipt=z.object({
  rawNumberedRtmRows:z.number().int().nonnegative(),
  obsoleteNumberedRtmRows:z.number().int().nonnegative(),
  applicableNumberedRtmRows:z.number().int().nonnegative(),
  tableFragmentNormalizationDeltaToNumberedRtmDenominator:z.number().int()
}).superRefine((r,c)=>{
  const expected=r.rawNumberedRtmRows-r.obsoleteNumberedRtmRows+r.tableFragmentNormalizationDeltaToNumberedRtmDenominator;
  if(r.applicableNumberedRtmRows!==expected)
    c.addIssue({code:z.ZodIssueCode.custom,message:`authoritative denominator mismatch: expected ${expected}, got ${r.applicableNumberedRtmRows}`});
});

export const Ssot=z.object({
  schemaVersion:z.literal("1.1.0"),
  removedScopeTags:z.array(z.string()),
  rows:z.array(Row),
  canonicalGroups:z.array(CanonicalGroup),
  denominatorReceipt:DenominatorReceipt,
  outwardArtifacts:z.array(z.object({id:z.string(),dependsOn:z.array(z.string()).min(1)}))
}).superRefine((s,c)=>{
  const ids=new Set<string>(),groups=new Set<string>();
  for(const r of s.rows.filter(x=>x.scoreEligible)){
    if(ids.has(r.canonicalId))c.addIssue({code:z.ZodIssueCode.custom,message:`duplicate canonical ${r.canonicalId}`});
    if(groups.has(r.semanticGroupKey))c.addIssue({code:z.ZodIssueCode.custom,message:`duplicate semantic ${r.semanticGroupKey}`});
    ids.add(r.canonicalId);groups.add(r.semanticGroupKey);
    if(r.scopeTags.some(t=>s.removedScopeTags.includes(t))&&!r.overrideEvidence.length)
      c.addIssue({code:z.ZodIssueCode.custom,message:`${r.id}: obsolete scope resurrected`});
  }

  const canonicalIds=new Set<string>();
  const fragments=new Map<string,string>();
  const governingRtms=new Map<string,string>();
  for(const g of s.canonicalGroups){
    if(canonicalIds.has(g.canonicalId))c.addIssue({code:z.ZodIssueCode.custom,message:`duplicate canonical group ${g.canonicalId}`});
    canonicalIds.add(g.canonicalId);
    for(const f of g.sourceFragments){
      const prior=fragments.get(f);
      if(prior)c.addIssue({code:z.ZodIssueCode.custom,message:`source fragment ${f} assigned to both ${prior} and ${g.canonicalId}`});
      else fragments.set(f,g.canonicalId);
    }
    for(const rtm of g.governingRtmIds){
      const prior=governingRtms.get(rtm);
      if(prior)c.addIssue({code:z.ZodIssueCode.custom,message:`governing ${rtm} assigned to both ${prior} and ${g.canonicalId}`});
      else governingRtms.set(rtm,g.canonicalId);
    }
  }

  const obsoleteNumbered=s.rows.filter(r=>/^RTM-\d+$/.test(r.id)&&r.applicability==="OBSOLETE").length;
  if(obsoleteNumbered!==s.denominatorReceipt.obsoleteNumberedRtmRows)
    c.addIssue({code:z.ZodIssueCode.custom,message:`obsolete numbered RTM receipt mismatch: rows=${obsoleteNumbered}, receipt=${s.denominatorReceipt.obsoleteNumberedRtmRows}`});
});
