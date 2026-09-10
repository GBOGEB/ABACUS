import assert from "node:assert/strict";
import test from "node:test";
import {SourceAuthorityContract} from "./sourceAuthority.js";

const base={
  schemaVersion:"1.1.0" as const,
  mode:"PRODUCTION" as const,
  canonicalAuthority:{
    logicalId:"QPS_MASTER_01_OFFER_RTM",
    sourceClass:"CANONICAL_SOURCE_AUTHORITY" as const,
    pathOrLogicalRef:"registry#MASTER_01_OFFER_RTM",
    authorityUse:"AUTHORITATIVE" as const,
    authorityReceipt:"receipt.json",
    sourceSha256:"a".repeat(64),
    semanticSha256:"b".repeat(64),
  },
  localProjection:{
    path:"review_projection.json",
    sourceClass:"GENERATED_VIEW" as const,
    authorityUse:"NON_AUTHORITATIVE" as const,
  },
  sources:[] as any[],
};

test("canonical source authority is valid without mislabelling it SSOT",()=>{
  const parsed=SourceAuthorityContract.parse(base);
  assert.equal(parsed.canonicalAuthority.sourceClass,"CANONICAL_SOURCE_AUTHORITY");
});

test("contract mirror cannot be authoritative or earn production credit",()=>{
  const bad={...base,sources:[{
    id:"mirror",sourceClass:"CONTRACT_REQUIREMENT_MIRROR",pathOrLogicalRef:"mirror.pdf",
    sha256:"c".repeat(64),authorityUse:"AUTHORITATIVE",productionCreditAllowed:true,freshnessState:"CURRENT"
  }]};
  assert.equal(SourceAuthorityContract.safeParse(bad).success,false);
});

test("hardcoded fixtures remain usable only as non-authoritative non-credit inputs",()=>{
  const good={...base,sources:[{
    id:"fixture",sourceClass:"HARDCODED_FIXTURE",pathOrLogicalRef:"legacy.py",
    authorityUse:"NON_AUTHORITATIVE",productionCreditAllowed:false,freshnessState:"STALE"
  }]};
  assert.equal(SourceAuthorityContract.safeParse(good).success,true);
  const bad={...base,sources:[{...good.sources[0],productionCreditAllowed:true}]};
  assert.equal(SourceAuthorityContract.safeParse(bad).success,false);
});

test("generated projection cannot be promoted by directory placement",()=>{
  const bad={...base,sources:[{
    id:"projection",sourceClass:"GENERATED_VIEW",pathOrLogicalRef:"ssot/review_projection.json",
    authorityUse:"AUTHORITATIVE",productionCreditAllowed:false,freshnessState:"CURRENT"
  }]};
  assert.equal(SourceAuthorityContract.safeParse(bad).success,false);
});
