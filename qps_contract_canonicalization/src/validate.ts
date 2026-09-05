import fs from "node:fs";
import crypto from "node:crypto";
import {Ssot} from "./schema.js";

const p=new URL("../ssot/review_projection.json",import.meta.url);
const raw=fs.readFileSync(p,"utf8");
const s=Ssot.parse(JSON.parse(raw));
const projectionScoreRows=s.rows.filter(r=>r.scoreEligible);
const leak=projectionScoreRows.filter(r=>r.scopeTags.some(t=>s.removedScopeTags.includes(t)));
if(leak.length)throw new Error("obsolete QSN/LN2 scope leaked into artifact population");

console.log(JSON.stringify({
  validated:true,
  sha256:crypto.createHash("sha256").update(raw).digest("hex"),
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
