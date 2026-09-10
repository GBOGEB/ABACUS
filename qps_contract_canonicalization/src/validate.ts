import fs from "node:fs";
import crypto from "node:crypto";
import {Ssot} from "./schema.js";
import {SourceAuthorityContract} from "./sourceAuthority.js";

const projectionPath=new URL("../ssot/review_projection.json",import.meta.url);
const authorityPath=new URL("../ssot/source_authority.json",import.meta.url);
const raw=fs.readFileSync(projectionPath,"utf8");
const authorityRaw=fs.readFileSync(authorityPath,"utf8");

// Validate authority first. A structurally valid projection is not permitted to confer
// authority on itself, on a contract mirror, or on stale/sample/hardcoded source material.
const authority=SourceAuthorityContract.parse(JSON.parse(authorityRaw));
const s=Ssot.parse(JSON.parse(raw));
const projectionScoreRows=s.rows.filter(r=>r.scoreEligible);
const leak=projectionScoreRows.filter(r=>r.scopeTags.some(t=>s.removedScopeTags.includes(t)));
if(leak.length)throw new Error("obsolete QSN/LN2 scope leaked into artifact population");

console.log(JSON.stringify({
  validated:true,
  projectionSha256:crypto.createHash("sha256").update(raw).digest("hex"),
  authorityContractSha256:crypto.createHash("sha256").update(authorityRaw).digest("hex"),
  authority:{
    mode:authority.mode,
    logicalId:authority.canonicalAuthority.logicalId,
    sourceClass:authority.canonicalAuthority.sourceClass,
    sourceSha256:authority.canonicalAuthority.sourceSha256,
    semanticSha256:authority.canonicalAuthority.semanticSha256,
    authorityReceipt:authority.canonicalAuthority.authorityReceipt,
    localProjectionClass:authority.localProjection.sourceClass,
    localProjectionAuthorityUse:authority.localProjection.authorityUse,
    supportingSources:authority.sources.map(x=>({
      id:x.id,
      sourceClass:x.sourceClass,
      authorityUse:x.authorityUse,
      productionCreditAllowed:x.productionCreditAllowed,
      freshnessState:x.freshnessState
    }))
  },
  projectionRows:s.rows.length,
  projectionScoreEligibleRows:projectionScoreRows.length,
  projectionExcludedRows:s.rows.length-projectionScoreRows.length,
  canonicalGroupCount:s.canonicalGroups.length,
  numberedRtmDenominator:{
    raw:s.denominatorReceipt.rawNumberedRtmRows,
    obsolete:s.denominatorReceipt.obsoleteNumberedRtmRows,
    applicable:s.denominatorReceipt.applicableNumberedRtmRows,
    tableFragmentNormalizationDelta:s.denominatorReceipt.tableFragmentNormalizationDeltaToNumberedRtmDenominator
  },
  outwardArtifacts:s.outwardArtifacts.map(a=>a.id)
},null,2));
