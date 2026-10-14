import argparse
import json
from pathlib import Path
from .core import receipt, ingest, census, verify
def main():
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("produce")
    for key in ("mission","task","root","sha","run","output"):
        a.add_argument("--"+key,required=True)
    a.add_argument("--receipt",default="receipt.json")
    b=sub.add_parser("ingest");b.add_argument("receipt");b.add_argument("--db",default="mcl.sqlite")
    b.add_argument("--artifact-root", required=True)
    c=sub.add_parser("census");c.add_argument("--db",default="mcl.sqlite")
    x=p.parse_args()
    if x.cmd=="produce":
        r=receipt(x.mission,x.task,x.root,x.sha,x.run,[x.output])
        Path(x.receipt).write_text(json.dumps(r,indent=2)+"\n")
    elif x.cmd=="ingest":
        data = json.loads(Path(x.receipt).read_text())
        if not verify(data, x.artifact_root):
            raise ValueError("artifact content does not match receipt")
        ingest(x.db, data)
    else:print(json.dumps(census(x.db),indent=2))
if __name__=="__main__":main()
