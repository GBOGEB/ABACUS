import test from "node:test";
import assert from "node:assert/strict";
import {Ssot} from "./schema.js";

const active={id:"RTM-999",canonicalId:"C",semanticGroupKey:"G",applicability:"APPLICABLE" as const,complianceStatus:"OPEN" as const,scoreEligible:true,reviewWeight:1,scopeTags:[],overrideEvidence:[]};
const obsolete=(id:string)=>({id,canonicalId:id,semanticGroupKey:`OBS.${id}`,applicability:"OBSOLETE" as const,complianceStatus:"NOT_SCORED" as const,scoreEligible:false,reviewWeight:0,scopeTags:["QSN"],overrideEvidence:[]});
const groups=[
 {canonicalId:"CANON-T04",governingRtmIds:["RTM-019"],sourceFragments:["RTM019","TABLE4"],linkedNonmergedRtmIds:[],scoreOnce:true as const},
 {canonicalId:"CANON-T05",governingRtmIds:["RTM-031"],sourceFragments:["RTM031","TABLE5"],linkedNonmergedRtmIds:["RTM-043"],scoreOnce:true as const},
 {canonicalId:"CANON-T06T07",governingRtmIds:["RTM-034"],sourceFragments:["RTM034","TABLE6","TABLE7"],linkedNonmergedRtmIds:["RTM-035","RTM-036","RTM-037","RTM-038","RTM-039"],scoreOnce:true as const},
 {canonicalId:"CANON-T08",governingRtmIds:["RTM-040"],sourceFragments:["RTM040","TABLE8"],linkedNonmergedRtmIds:[],scoreOnce:true as const},
 {canonicalId:"CANON-T09",governingRtmIds:["RTM-041"],sourceFragments:["RTM041","TABLE9"],linkedNonmergedRtmIds:["RTM-035"],scoreOnce:true as const}
];
const obsoleteRows=["RTM-045","RTM-046","RTM-047","RTM-249","RTM-250","RTM-251"].map(obsolete);
const base={schemaVersion:"1.1.0" as const,removedScopeTags:["QSN"],canonicalGroups:groups,denominatorReceipt:{rawNumberedRtmRows:722,obsoleteNumberedRtmRows:6,applicableNumberedRtmRows:716,tableFragmentNormalizationDeltaToNumberedRtmDenominator:0},outwardArtifacts:[{id:"HTML",dependsOn:["review_projection.json"]}]};

test("source-bound P2N receipt validates with 716 numbered RTMs",()=>assert.equal(Ssot.safeParse({...base,rows:obsoleteRows}).success,true));
test("wrong 715 denominator fails",()=>assert.equal(Ssot.safeParse({...base,denominatorReceipt:{...base.denominatorReceipt,applicableNumberedRtmRows:715},rows:obsoleteRows}).success,false));
test("duplicate source fragment across table groups fails",()=>assert.equal(Ssot.safeParse({...base,canonicalGroups:[...groups,{canonicalId:"CANON-X",governingRtmIds:["RTM-998"],sourceFragments:["TABLE9"],linkedNonmergedRtmIds:[],scoreOnce:true as const}],rows:obsoleteRows}).success,false));
test("obsolete QSN row cannot score",()=>assert.equal(Ssot.safeParse({...base,rows:[...obsoleteRows.slice(0,5),{...obsoleteRows[5],scoreEligible:true,reviewWeight:1,complianceStatus:"OPEN" as const}]}).success,false));
test("duplicate active scoring still fails",()=>assert.equal(Ssot.safeParse({...base,rows:[...obsoleteRows,active,{...active,id:"RTM-998"}]}).success,false));
test("removed scope resurrection still fails",()=>assert.equal(Ssot.safeParse({...base,rows:[...obsoleteRows,{...active,scopeTags:["QSN"]}]}).success,false));
