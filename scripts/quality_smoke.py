"""Run from repository root: PYTHONPATH=. python scripts/quality_smoke.py [--live] [--mkdocs]."""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from contracts.stage import StageInput
from harness.fakes import FakeLLM,FakeSandbox
from stages.report import execute
from stages.quality import write
from gates.g5_docs import check


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',action='store_true')
    parser.add_argument('--mkdocs',action='store_true')
    args=parser.parse_args()
    records=[]
    if args.live:
        from harness.agent import load_dotenv
        from harness.llm import Gateway
        load_dotenv(Path('.env'))
        def start(meta):records.append(meta);return len(records)-1
        def finish(i,value):records[i].update(value)
        llm=Gateway(start=start,finish=finish,budget=lambda:(sum((r.get('usage') or {}).get('total_tokens',0) for r in records),10000,0,10))
    for domain in ('tickets','equipment'):
        root=Path(tempfile.mkdtemp(prefix='rwb-quality-'+domain+'-')).resolve();artifacts={}
        source=Path('contracts/fixtures')/domain
        for name in ('analysis','app','ui','develop'):
            write(root,name+'.json',json.loads((source/(name+'.json')).read_text()));artifacts[name]=name+'.json'
        inp=StageInput(run_id=domain,stage='report',attempt=1,requirements='Проверка отчёта',artifacts=artifacts,snapshot=json.loads((source/'snapshot-failed.json').read_text()))
        out=execute(inp,root,llm if args.live else FakeLLM({'writer':['Проверки не завершены.']}),FakeSandbox({}))
        assert check(root,{**artifacts,**out.artifacts}).passed
        if args.mkdocs:subprocess.run([sys.executable,'-m','mkdocs','build','--strict','-f',str(root/'product/mkdocs.yml')],check=True)
        print(domain,root)
    if args.live:print('LLM calls:',[(r['status'],r.get('usage',{}).get('prompt_tokens'),r.get('usage',{}).get('completion_tokens')) for r in records])


if __name__=='__main__':main()
