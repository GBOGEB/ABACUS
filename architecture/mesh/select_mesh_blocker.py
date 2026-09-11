#!/usr/bin/env python3
import argparse,json
RANK={"RED":7,"BLOCKED":6,"AMBER":5,"UNKNOWN":4,"DEFER":3,"GREEN":1,"NA":0}
def load(p):
 with open(p,encoding="utf-8") as f:return json.load(f)
def main():
 ap=argparse.ArgumentParser(); ap.add_argument("vectors",nargs="+"); ap.add_argument("--out",default="mesh-rollup.json"); a=ap.parse_args()
 vs=[load(p) for p in a.vectors]
 if len(vs)<3: raise SystemExit("need >=3 repo vectors")
 candidates=[]
 for v in vs:
  bg=v["dimensions"]["BG"]
  candidates.append((RANK.get(bg["state"],4),v["repo"],v.get("blocking_atom"),v.get("next_action"),v["source_sha"]))
 candidates.sort(reverse=True)
 chosen=candidates[0]
 out={"repos":[{"repo":v["repo"],"source_sha":v["source_sha"],"freshness_timestamp":v["freshness_timestamp"]} for v in vs],"selection_basis":"mesh_status_vectors_only","selected_repo":chosen[1],"selected_blocking_atom":chosen[2],"next_CG_action":chosen[3],"repo_count":len(vs),"commit_or_pr_noise_read":False}
 with open(a.out,"w",encoding="utf-8") as f:json.dump(out,f,indent=2,sort_keys=True);f.write("\n")
 print("PASS contract-only selection",chosen[1],chosen[2])
if __name__=="__main__":main()
