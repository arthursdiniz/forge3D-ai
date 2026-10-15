import {lazy,Suspense,useEffect,useRef,useState} from 'react';
import {Settings,Check,ArrowRight,Download,SlidersHorizontal} from 'lucide-react';
import {finished,request,type Job} from '../api';
import ModelWorkspace from './ModelWorkspace';
import TextureStudio from './TextureStudio';
import AssetLibrary from './AssetLibrary';
import {Modal,ImportModel,JobProgress,stageLabel} from './ui';
import {useStudio} from './useStudio';
import {SubmissionGuard} from './submission';
import {readSession,saveSession} from './session';
import './studio.css';
const Viewer=lazy(()=>import('../Viewer'));
const AdvancedTools=lazy(()=>import('./AdvancedTools'));
type Area='modelar'|'texturizar'|'biblioteca';
function areaFromHash():Area{const hash=location.hash;return ['#texturizar','#texture'].includes(hash)?'texturizar':hash==='#biblioteca'?'biblioteca':'modelar';}

export default function StudioApp(){
  const {jobs,assets,health,caps,connection,onJob,loadJob,refreshAssets}=useStudio();
  const [area,setArea]=useState<Area>(areaFromHash),[file,setFile]=useState<File|null>(null);
  const [modelId,setModelId]=useState(()=>readSession().model||''),[sourceId,setSourceId]=useState(()=>readSession().source||''),[textureId,setTextureId]=useState(()=>readSession().texture||''),[libraryId,setLibraryId]=useState(()=>readSession().library||'');
  const [compare,setCompare]=useState(false),[error,setError]=useState(''),[advanced,setAdvanced]=useState(''),[importing,setImporting]=useState(false);
  const [exportTarget,setExportTarget]=useState<Job|null>(null),[pipeline,setPipeline]=useState('URP'),[exportSending,setExportSending]=useState(false);
  const [modelSending,setModelSending]=useState(false),[textureSending,setTextureSending]=useState(false);
  const mainTitle=useRef<HTMLHeadingElement>(null),selection=useRef(0),currentSource=useRef(sourceId),currentModel=useRef(modelId),exportPending=useRef(false);
  const modelSubmission=useRef(new SubmissionGuard()),textureSubmission=useRef(new SubmissionGuard());
  currentSource.current=sourceId;
  currentModel.current=modelId;
  // Every selection/navigation intent shares this revision, including modal callbacks.
  const revision=selection.current;
  useEffect(()=>{saveSession({model:modelId,source:sourceId,texture:textureId,library:libraryId});},[modelId,sourceId,textureId,libraryId]);
  useEffect(()=>{for(const id of [modelId,sourceId,textureId,libraryId])if(id&&!jobs.some(j=>j.id===id))void loadJob(id).catch(()=>{});},[modelId,sourceId,textureId,libraryId,loadJob]);
  const model=jobs.find(j=>j.id===modelId),source=jobs.find(j=>j.id===sourceId),texture=jobs.find(j=>j.id===textureId),library=jobs.find(j=>j.id===libraryId);
  const originalLibraryId=assets.flatMap(a=>a.versions).find(v=>v.id===libraryId)?.original_id;
  const displayed=area==='modelar'?model?.status==='completed'?model:undefined:area==='texturizar'?compare?source:texture?.status==='completed'?texture:source:compare?jobs.find(j=>j.id===originalLibraryId)||library:library;
  const busy=modelSending||textureSending||exportSending||jobs.some(j=>!finished(j)),active=jobs.find(j=>!finished(j));
  useEffect(()=>{const change=()=>{selection.current++;setArea(areaFromHash());setCompare(false);if(location.hash==='#hair')setAdvanced('hair');if(location.hash==='#comparison')setAdvanced('comparison');};change();window.addEventListener('hashchange',change);return()=>window.removeEventListener('hashchange',change);},[]);
  const lastCompleted=jobs.filter(j=>j.status==='completed').map(j=>j.id).join(',');
  useEffect(()=>{void refreshAssets().catch(()=>{});},[lastCompleted,refreshAssets]);
  function navigate(next:Area){selection.current++;setError('');setCompare(false);setArea(next);location.hash=next;mainTitle.current?.focus();}
  function modelingJob(job:Job){onJob(job);if(currentModel.current===modelId){selection.current++;setModelId(job.id);}}
  function textureJob(job:Job){
    onJob(job);
    if(job.kind==='import'){
      if(revision!==selection.current)return;
      selection.current++;setSourceId(job.id);setTextureId('');setImporting(false);
    }else if(job.parent===currentSource.current)setTextureId(job.id);
  }
  async function choose(id:string,context:Area=area){
    const ticket=++selection.current;
    try{const job=await loadJob(id);if(ticket!==selection.current)return;
      if(context==='texturizar'){setSourceId(job.id);setTextureId('');navigate('texturizar');}
      else if(context==='modelar'){setModelId(job.id);setCompare(false);}
      else{setLibraryId(job.id);setCompare(false);}
    }catch(e){if(ticket===selection.current)setError(String(e));}
  }
  function useForTexture(){if(!displayed)return;selection.current++;setSourceId(displayed.id);setTextureId('');navigate('texturizar');}
  async function compareOriginal(){
    const ticket=++selection.current;
    if(compare){setCompare(false);return;}
    if(!originalLibraryId)return;
    try{await loadJob(originalLibraryId);if(ticket===selection.current)setCompare(true);}catch(e){if(ticket===selection.current)setError(String(e));}
  }
  async function exportModel(){
    if(!exportTarget||exportPending.current)return;
    exportPending.current=true;setExportSending(true);setError('');
    const target=exportTarget.id,selectedPipeline=pipeline,ticket=selection.current;
    try{onJob(await request<Job>(`/api/jobs/${target}/export`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pipeline:selectedPipeline})}));}
    catch(e){if(ticket===selection.current)setError(String(e));}
    finally{exportPending.current=false;setExportSending(false);}
  }
  const exported=exportTarget?jobs.find(j=>j.kind==='export'&&j.parent===exportTarget.id&&(j.options?.pipeline||'URP')===pipeline&&!['cancelled','failed'].includes(j.status)):undefined;
  const exportFailure=exportTarget?jobs.find(j=>j.kind==='export'&&j.parent===exportTarget.id&&(j.options?.pipeline||'URP')===pipeline&&['cancelled','failed'].includes(j.status)):undefined;
  const versionGroup=assets.find(a=>a.versions.some(v=>v.id===displayed?.id));
  const textured=displayed&&(displayed.kind!=='model_workflow'&&displayed.options?.texture_output!=='geometry_only')&&!!displayed.metadata.materials?.some(m=>m.images?.length);
  const viewerActions=displayed?.artifacts.model?<>
    {area!=='texturizar'&&<button onClick={useForTexture}>Texturizar<ArrowRight size={15}/></button>}
    <button onClick={()=>{selection.current++;setExportTarget(displayed);}}><Download size={15}/>Exportar</button>
    <button aria-label="Ferramentas avançadas do modelo" title="Ferramentas avançadas" onClick={()=>{selection.current++;setAdvanced('geometry');}}><SlidersHorizontal size={17}/></button>
  </>:undefined;
  const openAdvanced=(tab:string)=>{selection.current++;setAdvanced(tab);};
  return <div className="studio">
    <a className="s-skip" href="#studio-main" onClick={e=>{e.preventDefault();document.getElementById('studio-main')?.focus();}}>Ir para o conteúdo</a>
    <header className="s-header">
      <a className="s-brand" href="#modelar" aria-label="Forge3D AI, Modelar"><img src="/forge.svg" alt=""/><span>Forge3D <b>AI</b></span></a>
      <nav aria-label="Navegação principal">{(['modelar','texturizar','biblioteca'] as Area[]).map(key=><a key={key} href={`#${key}`} aria-current={area===key?'page':undefined} onClick={()=>navigate(key)}>{key==='modelar'?'Modelar':key==='texturizar'?'Texturizar':'Biblioteca'}</a>)}</nav>
      <div className="s-local"><span className={connection?'offline':''}/><span>{connection?'Desconectado':'Local'}</span><button aria-label="Configurações locais" onClick={()=>openAdvanced('settings')}><Settings size={18}/></button></div>
    </header>
    <h1 className="s-sr" ref={mainTitle} tabIndex={-1}>Forge3D · {area}</h1>
    {(error||connection)&&<div className="s-error-banner" role="alert">{error||connection}<button aria-label="Fechar mensagem" onClick={()=>setError('')}>×</button></div>}
    <main id="studio-main" tabIndex={-1} className="s-main">
      {/* Keep drafts mounted; guards and pending intents live above all three surfaces. */}
      <div className="s-workspace-panel" hidden={area!=='modelar'}><ModelWorkspace file={file} setFile={setFile} result={model} onJob={modelingJob} busy={busy} providers={caps?.model||[]} onAdvanced={()=>openAdvanced('model')} onError={setError} submission={modelSubmission.current} sending={modelSending} setSending={setModelSending}/></div>
      <div className="s-workspace-panel" hidden={area!=='texturizar'}><TextureStudio source={source} result={texture||(source?.kind==='import'?source:undefined)} onJob={textureJob} busy={busy} onLibrary={()=>navigate('biblioteca')} onAdvanced={()=>openAdvanced('texture')} onError={setError} providers={caps?.texture||[]} submission={textureSubmission.current} sending={textureSending} setSending={setTextureSending}/></div>
      <div className="s-workspace-panel" hidden={area!=='biblioteca'}><AssetLibrary assets={assets} selected={libraryId} onSelect={id=>void choose(id)} onImport={()=>{selection.current++;setImporting(true);}}/></div>
      <div className="s-stage">
        {area==='biblioteca'&&library&&library.status!=='completed'&&<JobProgress job={library} onJob={onJob}/>}
        <Suspense fallback={<div className="s-view-loading">Carregando visualizador…</div>}><Viewer key={area} compact actions={viewerActions}
          emptyTitle={area==='biblioteca'&&!library?'Selecione um modelo na biblioteca':area==='texturizar'&&!source?'Escolha um modelo para começar':undefined}
          emptyDescription={area==='biblioteca'&&!library?'Escolha uma miniatura para inspecionar o modelo e suas versões.':area==='texturizar'&&!source?'Use a biblioteca ou importe um arquivo no painel ao lado.':undefined}
          url={displayed?.artifacts.model} name={displayed?.name} height={displayed?.metadata.dimensions?.[2]} hasTextures={!!textured} frontAxis={displayed?.metadata.render_front_axis||'negative_y'}
          stage={area==='modelar'&&model&&!finished(model)?model.stage:area==='texturizar'&&!source?'Escolha um modelo para começar':area==='biblioteca'&&!library?'Selecione um modelo na biblioteca':undefined}/></Suspense>
        {displayed&&<div className="s-version-bar">
          {versionGroup&&<label>Versão<select aria-label="Versão do modelo" value={displayed.id} onChange={e=>void choose(e.target.value,area)}>{versionGroup.versions.map((version,i)=><option key={version.id} value={version.id}>{version.candidate_index!=null?`Candidato ${version.candidate_index+1} · ${version.original_id===version.id?'Original':`Versão ${i+1}`}`:i===0?'Original':`Versão ${i+1}`} · {version.has_texture?'Com textura':'Geometria'}</option>)}</select></label>}
          {area==='texturizar'&&texture?.status==='completed'&&<button aria-pressed={compare} onClick={()=>{selection.current++;setCompare(!compare);}}>{compare?'Mostrar resultado':'Comparar com a origem'}</button>}
          {area==='biblioteca'&&originalLibraryId&&libraryId!==originalLibraryId&&<button aria-pressed={compare} onClick={()=>void compareOriginal()}>{compare?'Mostrar versão selecionada':'Comparar com original'}</button>}
          <span>{displayed.metadata.triangles?.toLocaleString('pt-BR')} triângulos{displayed.metadata.total_seconds?` · ${Math.round(displayed.metadata.total_seconds)} s`:''}</span>
        </div>}
        {displayed?.metadata.warnings?.length?<details className="s-result-note"><summary>Observações deste resultado ({displayed.metadata.warnings.length})</summary><ul>{displayed.metadata.warnings.map(w=><li key={w}>{w}</li>)}</ul><button onClick={()=>openAdvanced('geometry')}>Abrir diagnóstico e correções opcionais</button></details>:null}
      </div>
    </main>
    <footer className="s-footer"><span><Check size={13}/>{active?stageLabel(active.stage):modelSending||textureSending||exportSending?'Enviando solicitação…':'Tudo salvo neste computador'}</span><span title={health?.gpu.name}>{health?.gpu.total_mb?`${health.gpu.name.replace('NVIDIA GeForce ','')} · ${(health.gpu.used_mb/1024).toFixed(1)} / ${(health.gpu.total_mb/1024).toFixed(1)} GB`:''}</span></footer>
    {advanced&&<Modal wide title="Ferramentas avançadas" onClose={()=>{selection.current++;setAdvanced('');}}><Suspense fallback={<p>Carregando…</p>}><AdvancedTools tab={advanced} selected={displayed||source} jobs={jobs} health={health} file={file} onJob={j=>{onJob(j);void refreshAssets();}} onSelect={id=>{if(revision===selection.current)void choose(id,area);}}/></Suspense></Modal>}
    {importing&&<Modal title="Importar modelo" onClose={()=>{selection.current++;setImporting(false);}}><ImportModel disabled={busy} onError={setError} onJob={j=>{onJob(j);if(revision===selection.current){selection.current++;setLibraryId(j.id);setCompare(false);setImporting(false);}}}/></Modal>}
    {exportTarget&&<Modal title="Exportar modelo" onClose={()=>{selection.current++;setExportTarget(null);}}><p>{exportTarget.name}</p><label className="s-field">Pipeline do Unity<select value={pipeline} onChange={e=>setPipeline(e.target.value)}><option>URP</option><option>Built-in</option></select></label><p className="s-muted">O pacote inclui GLB, FBX, OBJ, texturas e materiais, com verificação de exportação.</p><button className="s-primary" disabled={busy||!!exported} onClick={()=>void exportModel()}>Preparar exportação</button><JobProgress job={exported||exportFailure} onJob={onJob}/>{exported?.status==='completed'&&<div className="s-downloads">{[['unity_zip','Pacote para Unity'],['glb','Modelo GLB'],['fbx','Modelo FBX'],['obj','Modelo OBJ']].map(([key,label])=>exported.artifacts[key]&&<a key={key} href={exported.artifacts[key]} download><Download size={15}/>{label}</a>)}</div>}</Modal>}
  </div>;
}
