import {useState} from 'react';
import {request,type Health} from './api';
export default function ModelSetupPanel({health}:{health:Health|null}) {
  const [path,setPath]=useState(''),[message,setMessage]=useState('');
  async function save(){try{await request('/api/config/blender',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({path})});setMessage('Blender configurado. O estado será atualizado no próximo diagnóstico.');}catch(e){setMessage(String(e));}}
  return <details className="workflow-section"><summary>Modelos e configuração local</summary><p className="control-note">{health?.gpu.name} · {health?.gpu.total_mb} MiB. Uma geração pesada por vez. Offload permanece desativado nos perfis atuais.</p>{health?.providers.map(model=><p className="control-note" key={model.id}><strong>{model.name}</strong>: {model.available?'validado localmente':'indisponível'} — {model.notes}</p>)}<label className="field">Caminho do Blender<input placeholder={health?.blender||'C:\\...\\blender.exe'} value={path} onChange={e=>setPath(e.target.value)}/></label><button onClick={()=>void save()} disabled={!path}>Configurar Blender local</button>{message&&<p role="status" className="control-note">{message}</p>}</details>;
}
