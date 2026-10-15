"""Actual Hinata analysis/geometry/export after hair-only changes, immutable trial."""
import argparse,json,shutil,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--trial',required=True);parser.add_argument('--source',default='3c2829b70fe046328b86d2a1141736d4');parser.add_argument('--reference',default='data/test-inputs/hinata-shoyo-reference-20261011.png');parser.add_argument('--analysis-only',action='store_true');parser.add_argument('--target-face',nargs=4,type=float);args=parser.parse_args()
qa=ROOT/'data/hair-upgrade-20261013'/args.trial;qa.mkdir(exist_ok=False);source=ROOT/'data/assets'/args.source/'model.glb'
analysis=qa/'analysis';analysis.mkdir();shutil.copy2(ROOT/args.reference,analysis/'source.png');(analysis/'options.json').write_text(json.dumps({'front_axis':'negative_y','style':'anime','preset':'auto',**({'target_face':args.target_face} if args.target_face else {})}))
with (analysis/'process.log').open('w') as log:subprocess.run([str(ROOT/'.venv-hair/Scripts/python.exe'),str(ROOT/'backend/hair/cli.py'),'--mode','analysis','--input',str(source),'--output',str(analysis),'--options',str(analysis/'options.json')],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
context=json.loads((analysis/'hair_analysis.json').read_text());assert context['status']=='reviewable',context
if args.analysis_only:print(json.dumps(context,indent=2));raise SystemExit(0)
result=qa/'candidate';result.mkdir();options={'reviewed':True,'front_axis':'negative_y','preset':'auto','attributes':{}};(result/'options.json').write_text(json.dumps(options))
with (result/'process.log').open('w') as log:subprocess.run([str(ROOT/'.venv-hair/Scripts/python.exe'),str(ROOT/'backend/hair/cli.py'),'--mode','reconstruct','--input',str(source),'--output',str(result),'--options',str(result/'options.json'),'--analysis',str(analysis)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
report=json.loads((result/'hair_geometry.json').read_text());print(json.dumps({key:report.get(key) for key in ['status','hair_triangles','protected_face_occlusion_pixels','silhouette_before','silhouette_after','seconds']},indent=2),flush=True)
if report['status']=='reviewable_candidate':
    with (result/'export.log').open('w') as log:subprocess.run([str(ROOT/'tools/blender-4.5.3-windows-x64/blender.exe'),'--background','--factory-startup','--disable-autoexec','--threads','6','--python-exit-code','1','--python',str(ROOT/'blender/pipeline.py'),'--','--input',str(result/'model.glb'),'--output',str(result),'--mode','export','--options',str(result/'options.json')],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    subprocess.run([str(ROOT/'.venv-ai/Scripts/python.exe'),str(ROOT/'backend/texture_engine/validate_export.py'),'--source',str(result/'model.glb'),'--directory',str(result)],cwd=ROOT,check=True)
