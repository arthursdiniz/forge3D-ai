import { Component, useEffect, useRef, useState, Suspense, type ReactNode } from 'react';
import { Canvas, useThree } from '@react-three/fiber';
import { OrbitControls, Grid, Bounds, useBounds, Html } from '@react-three/drei';
import { GLTFLoader, type GLTF } from 'three/addons/loaders/GLTFLoader.js';
import { Box, Grid2X2, Scan, RotateCcw, Image as ImageIcon } from 'lucide-react';
import * as THREE from 'three';

function dispose(scene:THREE.Object3D) {
  const materials=new Set<THREE.Material>(),textures=new Set<THREE.Texture>();
  scene.traverse(object=>{if(object instanceof THREE.Mesh){object.geometry.dispose();for(const material of Array.isArray(object.material)?object.material:[object.material]){materials.add(material);for(const value of Object.values(material)){if(value instanceof THREE.Texture)textures.add(value);}}}});
  materials.forEach(material=>{if(material.userData.originalMap instanceof THREE.Texture)textures.add(material.userData.originalMap);});
  const bitmaps=new Set<ImageBitmap>();
  textures.forEach(texture=>{const data=texture.image;for(const image of Array.isArray(data)?data:[data]){if(typeof ImageBitmap!=='undefined'&&image instanceof ImageBitmap)bitmaps.add(image);}texture.dispose();});
  bitmaps.forEach(bitmap=>bitmap.close());materials.forEach(material=>material.dispose());
}

function Asset({url,wireframe,textures,onLoad}:{url:string;wireframe:boolean;textures:boolean;onLoad:()=>void}) {
  const [asset,setAsset]=useState<GLTF|null>(null),[error,setError]=useState('');
  const bounds=useBounds();
  const {invalidate}=useThree();
  useEffect(()=>{
    let alive=true,loaded:GLTF|null=null;
    const abort=new AbortController();setAsset(null);setError('');
    fetch(url,{signal:abort.signal}).then(response=>{if(!response.ok)throw new Error('Arquivo 3D indisponível');return response.arrayBuffer();}).then(buffer=>new GLTFLoader().parseAsync(buffer,'')).then(result=>{loaded=result;if(alive){setAsset(result);onLoad();invalidate();}else dispose(result.scene);}).catch(error=>{if(alive)setError(String(error));});
    return ()=>{alive=false;abort.abort();if(loaded)dispose(loaded.scene);};
  },[url]);
  useEffect(()=>{if(asset){bounds.refresh(asset.scene).clip().fit();invalidate();}},[asset,bounds]);
  useEffect(()=>{asset?.scene.traverse(object=>{if(object instanceof THREE.Mesh){for(const material of Array.isArray(object.material)?object.material:[object.material]){if(material instanceof THREE.MeshStandardMaterial){material.wireframe=wireframe;if(!('originalMap' in material.userData)){material.userData.originalMap=material.map;material.userData.originalColor=material.color.clone();}material.map=textures?material.userData.originalMap:null;if(textures)material.color.copy(material.userData.originalColor);else material.color.setRGB(.5,.5,.5,THREE.LinearSRGBColorSpace);material.needsUpdate=true;}}}});invalidate();},[asset,wireframe,textures,invalidate]);
  if(error)return <Html center><div className="viewer-error">Não foi possível abrir o modelo.<br/>{error}</div></Html>;
  return asset?<primitive object={asset.scene} dispose={null}/>:<Html center><div className="loader"/>Carregando modelo 3D…</Html>;
}
function Reframe({tick,ready}:{tick:number;ready:boolean}){const bounds=useBounds();useEffect(()=>{if(tick>0&&ready)bounds.refresh().clip().fit();},[tick,ready]);return null;}
class CanvasBoundary extends Component<{children:ReactNode},{error:boolean}> {state={error:false};static getDerivedStateFromError(){return {error:true};}render(){return this.state.error?<div className="empty-view"><Box size={40}/><h2>Visualizador indisponível</h2><p>Ative WebGL no navegador e recarregue a página.</p></div>:this.props.children;}}

export default function Viewer({url,name,stage,height=1,hasTextures=true}:{url?:string;name?:string;stage?:string;height?:number;hasTextures?:boolean}) {
  const [grid,setGrid]=useState(true),[wireframe,setWireframe]=useState(false),[textures,setTextures]=useState(true),[rotate,setRotate]=useState(false),[frame,setFrame]=useState(0),[loaded,setLoaded]=useState(false),[light,setLight]=useState(1.5);
  const onLoad=useRef(()=>setLoaded(true));
  useEffect(()=>setLoaded(false),[url]);
  return <section className="viewport panel"><div className="viewport-header"><h2>{name||'Visualizador 3D'}</h2><div className="toolbar"><button className={grid?'active':''} aria-pressed={grid} onClick={()=>setGrid(!grid)}><Grid2X2 size={15}/>Grid</button><button className={wireframe?'active':''} aria-pressed={wireframe} onClick={()=>setWireframe(!wireframe)}><Box size={15}/>Wireframe</button><button className={textures&&hasTextures?'active':''} aria-pressed={textures&&hasTextures} disabled={!hasTextures} title={hasTextures?'Mostrar textura':'Este modelo contém geometria e material neutro, sem textura gerada'} onClick={()=>setTextures(!textures)}><ImageIcon size={15}/>Texturas</button><button className={rotate?'active':''} aria-pressed={rotate} onClick={()=>setRotate(!rotate)}><RotateCcw size={15}/>Girar</button><button onClick={()=>setFrame(frame+1)} disabled={!url}><Scan size={15}/>Enquadrar</button></div></div>
    <div className="canvas-wrap" data-model-loaded={loaded}>
      <CanvasBoundary key={url}><Canvas camera={{position:[3,2.2,3],fov:40}} dpr={[1,1.5]} frameloop={rotate?'always':'demand'} gl={{antialias:true,alpha:true}}><ambientLight intensity={light}/><directionalLight position={[4,6,4]} intensity={light*1.5}/><directionalLight position={[-3,2,-4]} intensity={light*0.7}/>{grid&&<Grid position={[0,url?-height/2-0.005:0,0]} args={[20,20]} cellSize={0.5} cellThickness={0.5} cellColor="#333c43" sectionSize={2.5} sectionThickness={0.8} sectionColor="#434d54" fadeDistance={20} infiniteGrid/>}<OrbitControls makeDefault autoRotate={rotate} autoRotateSpeed={1} minDistance={0.1} maxDistance={50}/>{url&&<Bounds margin={1.4}><Suspense fallback={null}><Asset key={url} url={url} wireframe={wireframe} textures={textures&&hasTextures} onLoad={onLoad.current}/></Suspense><Reframe tick={frame} ready={loaded}/></Bounds>}</Canvas></CanvasBoundary>
      {!url&&<div className="empty-view"><Box size={54} strokeWidth={1.2}/><h2>{stage||'Sua próxima criação começa aqui'}</h2><p>{stage?'O resultado aparecerá assim que o processamento terminar.':'Envie uma referência e gere seu primeiro modelo 3D.'}</p></div>}
      <label className="light-control">Luz <input aria-label="Intensidade da iluminação" type="range" min="0.3" max="3" step="0.1" value={light} onChange={event=>setLight(Number(event.target.value))}/></label>
      <span className="viewer-help">Arraste para girar · Scroll para zoom · Botão direito para pan</span>
    </div></section>;
}
