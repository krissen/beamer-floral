#!/usr/bin/env python3
"""Per-pass wall time, user time, peak RSS and PDF size for test/reuse-benchmark.tex.

Usage: TIKZFLORA=<engine> [REUSE=all] [S=5] [WARM=1] measure_reuse.py LABEL VARIANT N K [PASSES]
macOS /usr/bin/time -l reports peak RSS. Results append to build/reuse-benchmark/results.jsonl.
"""
import json,os,re,shutil,subprocess,sys,time
from pathlib import Path
R=Path(__file__).resolve().parents[1]
E=os.environ['TIKZFLORA']
label,v,N,K=sys.argv[1:5]; passes=int(sys.argv[5]) if len(sys.argv)>5 else 3
warm=os.environ.get('WARM')=='1'
out=R/'build/reuse-benchmark'/label
if not warm: shutil.rmtree(out,ignore_errors=True)
out.mkdir(parents=True,exist_ok=True)
env=dict(os.environ,LC_ALL='C',TIKZFLORA=E,FLORA_LUA=E+'/lua',TEXINPUTS=f'{R}:{E}/tex//:')
src=out/'d.tex'
S=os.environ.get('S','0')
src.write_text(f"\\def\\floralreuse{{{os.environ.get('REUSE','')}}}\\def\\benchS{{{S}}}\\def\\floralvariant{{{v}}}\\def\\benchN{{{N}}}\\def\\benchK{{{K}}}\\input{{test/reuse-benchmark.tex}}\n")
rows=[]
for p in range(passes):
    t=time.monotonic()
    r=subprocess.run(['/usr/bin/time','-l','lualatex','-interaction=nonstopmode','-halt-on-error',f'-output-directory={out.relative_to(R)}',str(src.relative_to(R))],cwd=R,env=env,capture_output=True,text=True)
    w=time.monotonic()-t
    m=re.search(r'(\d+)\s+maximum resident',r.stderr); u=re.search(r'([\d.]+) user',r.stderr)
    log=(out/'d.log').read_text(errors='replace')
    pdf=out/'d.pdf'
    rows.append(dict(label=label,variant=v,N=int(N),K=int(K),warm=warm,pass_=p+1,rc=r.returncode,wall=round(w,1),user=float(u.group(1)) if u else None,rss_mb=round(int(m.group(1))/1e6) if m else None,pdf_mb=round(pdf.stat().st_size/1e6,2) if pdf.exists() else None,rerun='Rerun to get' in log or 'may have changed. Rerun' in log,load=os.getloadavg()[0]))
    print(json.dumps(rows[-1]),flush=True)
    if r.returncode: print(r.stdout[-1500:]); sys.exit(1)
with open(R/'build/reuse-benchmark/results.jsonl','a') as f:
    for x in rows: f.write(json.dumps(x)+'\n')
