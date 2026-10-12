"""Build Portuguese report and a self-contained research comparison gallery."""
import base64
import hashlib
import html
import json
import re
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OUT=ROOT/'data/research-2026-10-11'
LABELS={'sg_front_baseline':'TripoSG frente · padrão','sg_front_small':'TripoSG frente · ocupação 65%','sg_front_large':'TripoSG frente · ocupação 87,5%','sg_front_seed7':'TripoSG frente · seed 7','sg_front_steps25':'TripoSG frente · 25 passos','sg_front_quality512':'TripoSG frente · extração 512³','sg_three_quarter':'TripoSG · entrada três quartos','sr_three_quarter_neural':'TripoSR · atlas neural 1024','sr_three_quarter_vertex':'TripoSR · vértices 512','sr_three_quarter_vertex1024':'TripoSR · vértices 1024','sg_best_medium':'TripoSG melhor · 31.926 tris','sg_best_low':'TripoSG melhor · 6.384 tris','sg_quality_refined':'TripoSG 512 · silhueta refinada','ground_truth':'Referência procedural limpa'}

def read(path):return json.loads(path.read_text(encoding='utf-8'))
def link(path,label):return f'[{label}](<{path.resolve().as_posix()}>)'
def pct(value):return f'{value:.2f}'.replace('.',',')
def integer(value):return f'{value:,}'.replace(',','.')

def main():
    metrics=read(OUT/'geometry_metrics.json')
    byname={m['name']:m for m in metrics}
    runs={p.parent.name:read(p) for p in (OUT/'runs').glob('*/inference.json')}
    rows=['| Variante | Triângulos | Distância de superfície ↓ | F-score (2%) ↑ |','|---|---:|---:|---:|']
    for m in metrics:
        rows.append(f"| {LABELS[m['name']]} | {integer(m['triangles'])} | {pct(m['normalized_surface_distance_percent'])}% | {pct(m['surface_fscore_at_2_percent']*100)}% |")
    table='\n'.join(rows)
    timing=['| Inferência | Tempo subprocesso | Geração/extração | Pico PyTorch |','|---|---:|---:|---:|']
    for name,r in runs.items():timing.append(f"| {LABELS[name]} | {r['total_seconds']:.2f} s | {r['inference_seconds']:.2f} s | {r['peak_vram_mb']:.1f} MiB |")
    baseline=byname['sg_front_baseline'];quarter=byname['sg_three_quarter'];quality=byname['sg_front_quality512'];low=byname['sg_best_low']
    reduction=(1-quarter['normalized_surface_distance_percent']/baseline['normalized_surface_distance_percent'])*100
    observed=f"""- **A vista em três quartos ajudou neste objeto:** distância {pct(baseline['normalized_surface_distance_percent'])}% → {pct(quarter['normalized_surface_distance_percent'])}%, redução relativa de {pct(reduction)}% dessa métrica. A imagem revela profundidade e separação de partes que a frente esconde. Isso não prova a mesma melhora em todos os objetos.
- **512³ não melhorou a forma medida:** {baseline['triangles']:,} → {quality['triangles']:,} triângulos, com distância {pct(baseline['normalized_surface_distance_percent'])}% → {pct(quality['normalized_surface_distance_percent'])}%. O aumento da amostragem do mesmo campo acrescentou densidade e um componente separado.
- **Ocupação maior não foi melhor:** 87,5% teve erro maior que o padrão 83,33%; 65% também piorou a distância média. F-score e distância não ordenaram todas as variantes da mesma forma.
- **25 passos foi uma opção de velocidade nesta amostra:** distância próxima ao padrão de 50 passos. Comparar os tempos de geração na tabela; carregamento e cache também influenciam o tempo total.
- **Seed altera o resultado:** seed 7 piorou a distância desta cadeira. Testar alternativas é útil, mas escolher um seed com base no objeto conhecido não demonstra generalização."""
    observed+='\n- **TripoSG foi mais fiel que TripoSR nesta cadeira:** no input em três quartos, a distância TripoSR foi 6,01%, contra 0,86% TripoSG. TripoSR também mostrou falhas claras em pernas, encosto e profundidade. Uma importação/renderização tecnicamente válida não torna essas formas equivalentes.'
    texture=read(OUT/'texture_control.json')
    texture_text=f"No controle adicional, MC256 e texturas1024² foram iguais nas duas pipelines. Posições de vértices idênticas: **{texture['vertices_identical']}**; faces idênticas: **{texture['faces_identical']}**; cores de vértice idênticas: **{texture['vertex_colors_identical']}**. Portanto, mudar o bake/atlas **não corrigiu a geometria**. UVs e amostragem de cor diferem, e este teste não atribui nota artística de textura. O caso anterior com bake512 foi mantido como outra pipeline, sem atribuir sua diferença exclusivamente ao método. TripoSR aqui gera base color, sem mapas novos de normal/metallic/roughness."
    refine=read(OUT/'optimized/sg_quality_refined/refinement.json')['refinement']
    post=f"""A simplificação do melhor caso reduziu **{quarter['triangles']:,} → {low['triangles']:,} triângulos (98%)**. A distância foi {pct(quarter['normalized_surface_distance_percent'])}% → {pct(low['normalized_surface_distance_percent'])}% e o F-score permaneceu próximo. A revisão por vistas e o Unity complementam esse número; não se conclui que 6 mil triângulos sejam o orçamento ideal para todo jogo. A variante intermediária tem31.926 triângulos.

Refinar a silhueta do caso512 aumentou IoU frontal de **{pct(refine['silhouette_iou_before']*100)}% → {pct(refine['silhouette_iou_after']*100)}%**, com limite de deslocamento e sem mudar conectividade. Distância3D passou de {pct(quality['normalized_surface_distance_percent'])}% para {pct(byname['sg_quality_refined']['normalized_surface_distance_percent'])}%. É um ganho frontal pequeno, não uma reconstrução nova das costas ou profundidade."""
    unity=read(OUT/'unity-validation.json')
    unity_records=[]
    for path in sorted((OUT/'unity-results').glob('*.json')):
        if path.name=='lod-chain.json':continue
        value=read(path)
        if value.get('imported'):unity_records.append((path.stem,value))
    unity_text='Verificação real em Unity 6000.3.0f1 com URP: importação FBX, arrays, materiais, prefab, collider e renders. O controle original com defeito é mantido como reprovação esperada; a referência limpa é a entrega procedural. Os relatórios distinguem integração de limpeza superficial.\n\n'
    unity_text+='| Caso Unity | Triângulos | Compatibilidade de importação | Limpeza superficial |\n|---|---:|---|---|\n'
    for name,value in unity_records:
        triangles=value.get('triangles',value.get('actualTriangles','—'))
        compatible=value.get('importCompatibilityPassed',False)
        clean=value.get('surfaceCleanlinessPassed',False)
        unity_text+=f'| {name} | {integer(triangles) if isinstance(triangles,int) else triangles} | {"Sim" if compatible else "Não"} | {"Sim" if clean else "Não"} |\n'
    unity_text+='\n'+link(OUT/'unity-validation.json','Resumo completo da validação Unity')+'. Os testes não medem frame time de um jogo ou comportamento final de física.'
    unity_text+='\n\nO prefab com três LODs usa realmente as malhas de 319.266, 31.926 e 6.384 triângulos, com níveis forçados e renderizados. O collider de caixa foi conferido por limites e raycast. A malha alta ainda tem duas faces de área quase zero; as reduzidas passaram a inspeção de limpeza. A altura de saída neural é cerca de 1,90 m e precisa ser ajustada ao uso: a normalização do benchmark não resolve escala física automaticamente. Pacote portátil para URP: '+link(OUT/'unity-results/sg_best_lod.unitypackage','sg_best_lod.unitypackage')+'.'
    paths=[(OUT/'geometry_metrics.json','Métricas geométricas'),(OUT/'manifest.json','Manifest das nove inferências iniciais'),(OUT/'metric_calibration.json','Calibração da amostragem'),(OUT/'texture_control.json','Controle de texturas1024'),(OUT/'selection.json','Seleção experimental'),(OUT/'fixture/ground_truth_clean.glb','Cadeira procedural limpaGLB'),(OUT/'optimized/sg_best_low/model.glb','Cadeira neural reduzidaGLB'),(OUT/'unity-validation.json','Verificação no Unity'),(OUT/'galeria.html','Galeria por quatro vistas'),(OUT/'comparacao.png','Comparação visual neutra')]
    artifacts='\n'.join('- '+link(path,label) for path,label in paths)
    artifacts+='\n\nScripts: '+', '.join(link(HERE/name,name) for name in ['create_fixture.py','clean_fixture.py','run_experiments.py','evaluate_geometry.py','postprocess_experiments.py','texture_control.py','render_aligned.py','blender_safe_pipeline.py','verify_research.py','UnityResearchValidation.cs','run_unity_validation.ps1'])
    template=(HERE/'report-template.md').read_text(encoding='utf-8')
    values={'INFERENCE_COUNT':str(len(runs)),'SAMPLING_FLOOR':pct(read(OUT/'metric_calibration.json')['same_surface_independent_samples_distance_percent']),'GEOMETRY_TABLE':table,'INFERENCE_TABLE':'\n'.join(timing),'OBSERVED_RESULTS':observed,'TEXTURE_CONTROL':texture_text,'POSTPROCESS_RESULTS':post,'UNITY_RESULTS':unity_text,'ARTIFACT_LINKS':artifacts}
    for key,value in values.items():template=template.replace('{{'+key+'}}',value)
    for old,new in [('texturas1024','texturas 1024'),('textura1024','textura 1024'),('texturas1024','texturas 1024'),('texturas1024','texturas 1024'),('caso512','caso 512'),('Distância3D','Distância 3D'),('triângulos. A variante intermediária tem31.926','triângulos. A variante intermediária tem 31.926'),('limpaGLB','limpa GLB'),('reduzidaGLB','reduzida GLB'),('MC256','MC 256'),('TripoSG256','TripoSG 256'),('e512','e 512'),('bake512','bake 512')]:template=template.replace(old,new)
    for value in [230912,921552,319266,6384]:template=template.replace(f'{value:,}',integer(value))
    template=template.replace('tem31.926','tem 31.926').replace('**True**','**Sim**').replace('**False**','**Não**')
    if re.search(r'\{\{[A-Z_]+\}\}',template):raise ValueError('Unresolved report marker')
    (HERE/'RELATORIO.md').write_text(template,encoding='utf-8')
    urls=sorted(set(re.findall(r'https://[^\s)]+',template)))
    (HERE/'sources.json').write_text(json.dumps({'access_date':'2026-10-11','count':len(urls),'sources':urls,'evidence':'official docs/papers for capabilities; forums anecdotal; Wikipedia conceptual background'},indent=2),encoding='utf-8')
    gallery=[]
    for path in sorted((OUT/'comparison').iterdir()):
        if not path.is_dir():continue
        views={p.stem:'data:image/png;base64,'+base64.b64encode(p.read_bytes()).decode() for p in path.glob('*.png')}
        gallery.append({'name':path.name,'label':LABELS[path.name],'views':views,'metric':byname.get(path.name)})
    payload=json.dumps(gallery,ensure_ascii=False)
    page='''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Forge3D · comparação de métodos</title><style>body{font:16px system-ui;margin:32px;background:#111923;color:#e7edf4}h1{font-size:28px}p{max-width:900px;color:#bcc9d8}select{font:inherit;padding:9px;border-radius:6px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:18px;margin-top:20px}article{background:#1a2533;border-radius:12px;padding:16px}img{width:100%;border-radius:8px}small{display:block;color:#b9c8d9;line-height:1.7}h2{font-size:17px}footer{margin-top:20px;color:#aabaca}</style><h1>Modelagem3D: forma antes da textura</h1><p>Uma cadeira conhecida, diferentes métodos. Câmera, escala normalizada e material neutro iguais; yaw alinhado usando a referência. Pontuação descreve superfície amostrada, não qualidade artística universal.</p><label>Vista: <select id="view"><option value="three_quarter">Três quartos</option><option value="front">Frente</option><option value="side">Lado</option><option value="rear">Costas</option></select></label><main id="cards"></main><footer>11/10/2026 · RTX4060 8GB · imagens e dados embutidos, sem conexão externa.</footer><script>const data=PAYLOAD;const cards=document.getElementById('cards');function draw(){cards.textContent='';const view=document.getElementById('view').value;data.forEach(row=>{const article=document.createElement('article'),title=document.createElement('h2'),img=document.createElement('img'),text=document.createElement('small');title.textContent=row.label;img.src=row.views[view];img.alt=row.label+' — '+view;text.textContent=row.metric?row.metric.triangles.toLocaleString('pt-BR')+' triângulos · distância '+row.metric.normalized_surface_distance_percent.toFixed(2)+'% · F-score '+(row.metric.surface_fscore_at_2_percent*100).toFixed(1)+'%':'214 triângulos · geometria conhecida';article.append(title,img,text);cards.append(article)})}document.getElementById('view').addEventListener('change',draw);draw()</script></html>'''
    (OUT/'galeria.html').write_text(page.replace('PAYLOAD',payload),encoding='utf-8')
    names=['ground_truth','sr_three_quarter_neural','sg_three_quarter','sg_best_low']
    width=1200;height=744
    board=Image.new('RGB',(width,height),'#111923');draw=ImageDraw.Draw(board)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17)
    heading=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',22)
    draw.text((18,14),'Mesma cadeira · material neutro · câmeras iguais',fill='white',font=heading)
    for i,name in enumerate(names):
        x=i*300
        label=LABELS[name].replace('TripoSG melhor · ','TripoSG reduzido · ')
        draw.text((x+9,54),label,fill='#e7edf4',font=font)
        count=214 if name=='ground_truth' else byname[name]['triangles']
        draw.text((x+9,80),f'{integer(count)} triângulos',fill='#b9c8d9',font=font)
        for j,view in enumerate(['three_quarter','rear']):
            img=Image.open(OUT/'comparison'/name/(view+'.png')).convert('RGB').resize((294,294))
            board.paste(img,(x+3,112+j*306))
    draw.text((18,724),'Acima: três quartos. Abaixo: costas. Alinhamento favorável aos geradores; teste de um objeto.',fill='#b9c8d9',font=font)
    board.save(OUT/'comparacao.png')
    files=[p for p in OUT.rglob('*') if p.is_file() and p.suffix in ['.json','.glb','.fbx','.png'] and 'UnityValidation' not in p.parts]
    proof={'new_inferences':len(runs),'variants_measured':len(metrics),'sources_count':len(urls),'files':[{'path':str(p.relative_to(OUT)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]}
    (OUT/'evidence_manifest.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
    print(json.dumps({'report':str(HERE/'RELATORIO.md'),'inferences':len(runs),'variants':len(metrics),'sources':len(urls),'gallery_cards':len(gallery)}),flush=True)

if __name__=='__main__':main()
