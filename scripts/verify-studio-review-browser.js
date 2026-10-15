async (page) => {
  const results=[];
  const ids={a:'a'.repeat(32),b:'b'.repeat(32),c:'c'.repeat(32),export:'d'.repeat(32)};
  const model='/api/files/57a3da2b44d640b8b54c083e64a5ca6b/model.glb';
  const job=(id,name,parent=null,kind='generate')=>({id,name,parent,kind,provider:'triposr',status:'completed',stage:'Pronto',created_at:'2026-10-15',error:null,artifacts:{model},options:{texture_output:'geometry_only'},metadata:{triangles:2,materials:[],render_front_axis:'negative_y'}});
  const a=job(ids.a,'QA Lote'),b=job(ids.b,'QA Candidato 2',ids.a),c=job(ids.c,'QA Versão do candidato 2',ids.b,'transform');
  const exported={...job(ids.export,'QA Export URP',ids.a,'export'),options:{pipeline:'URP'},artifacts:{unity_zip:'/qa-urp.zip'}};
  const failedExport={...job('f'.repeat(32),'QA Failed Built-in',ids.a,'export'),status:'failed',error:'QA deliberate export failure',options:{pipeline:'Built-in'},artifacts:{}};
  const group={id:ids.a,name:'QA Lote',category:'anime',latest_id:ids.c,has_texture:false,status:'completed',warnings:0,versions:[a,b,c].map((j,i)=>({id:j.id,name:j.name,kind:j.kind,created_at:j.created_at,has_texture:false,original_id:i?ids.b:ids.a,candidate_index:i?1:0}))};
  let delayed=null,posts=[],releases=[];
  await page.route('**/api/**',async route=>{
    const url=new URL(route.request().url()),path=url.pathname;
    if(path.startsWith('/api/files/'))return route.continue();
    if(route.request().method()==='POST'){
      posts.push({path,body:route.request().postData()});
      if(delayed==='post')await new Promise(resolve=>releases.push(resolve));
      const kind=path==='/api/models/import'?'import':path.endsWith('/export')?'export':path.endsWith('/texture')?'texture_workflow':'model_workflow';
      return route.fulfill({json:{...job('e'.repeat(32),'QA Pending',path.includes('/texture')?ids.a:null,kind),status:'queued'}});
    }
    if(path==='/api/jobs')return route.fulfill({json:[c,b,a,failedExport,exported]});
    if(path==='/api/library')return route.fulfill({json:[group]});
    if(path==='/api/health')return route.fulfill({json:{gpu:{name:'QA GPU',total_mb:8192,used_mb:0},providers:[],data_directory:'QA',blender:'QA'}});
    if(path==='/api/workflows/capabilities')return route.fulfill({json:{model:[{id:'triposr',name:'TripoSR',available:true}],texture:[{id:'reference_projection',available:true}]}});
    if(path.endsWith('/references'))return route.fulfill({json:{}});
    const id=path.split('/')[3];
    if(delayed===id)await new Promise(resolve=>releases.push(resolve));
    return route.fulfill({json:path.endsWith('/original')?(id===ids.c?b:a):[a,b,c,exported].find(j=>j.id===id)});
  });
  const release=()=>{releases.splice(0).forEach(resolve=>resolve());delayed=null;};
  async function reset(area,session){release();posts=[];await page.goto('http://127.0.0.1:8000/?studio=review-tests#'+area);await page.evaluate(value=>sessionStorage.setItem('forge3d.studio.selection.v1',JSON.stringify(value)),session);await page.reload();await page.waitForFunction(()=>document.querySelector('.s-footer')?.textContent.includes('QA GPU'));}
  async function check(name,action){try{await action();results.push({name,passed:true});}catch(error){results.push({name,passed:false,error:String(error)});}finally{release();}}
  await check('late version selection cannot undo subsequent navigation',async()=>{
    await reset('texturizar',{source:ids.a});delayed=ids.b;
    await page.getByRole('combobox',{name:'Versão do modelo'}).selectOption(ids.b);
    await page.waitForFunction(()=>true);await page.getByRole('link',{name:'Biblioteca',exact:true}).click();
    release();await page.waitForTimeout(400);
    if(new URL(page.url()).hash!=='#biblioteca')throw Error('Late selection navigated away from Biblioteca');
  });
  await check('model submit remains locked across leaving and returning to the area',async()=>{
    await reset('modelar',{});await page.locator('.s-sidebar input[type=file]').first().setInputFiles('C:/Users/arthu/OneDrive/Documentos/Codex/forge3D-ai/data/test-inputs/hinata-shoyo-reference-20261011.png');delayed='post';
    await page.getByRole('button',{name:'Gerar modelo 3D',exact:true}).click();
    await page.getByRole('link',{name:'Biblioteca',exact:true}).click();await page.getByRole('link',{name:'Modelar',exact:true}).click();
    const generate=page.locator('.s-sidebar:visible .s-primary');
    if(await generate.isEnabled()){await generate.click();await page.waitForTimeout(100);throw Error('Second submission allowed, POST count '+posts.length);}
    if(posts.length!==1)throw Error('Expected exactly one POST');
  });
  await check('candidate version compares with its own candidate original',async()=>{
    await reset('biblioteca',{library:ids.c});await page.getByRole('button',{name:'Comparar com original',exact:true}).click();
    await page.waitForTimeout(350);
    const selected=await page.getByRole('combobox',{name:'Versão do modelo'}).inputValue();
    if(selected!==ids.b)throw Error('Comparison selected '+selected+' instead of second candidate '+ids.b);
  });
  await check('late original comparison cannot replace a newer library selection',async()=>{
    await reset('biblioteca',{library:ids.c});delayed=ids.b;
    await page.getByRole('button',{name:'Comparar com original',exact:true}).click();
    await page.getByRole('combobox',{name:'Versão do modelo'}).selectOption(ids.a);
    await page.waitForTimeout(100);release();await page.waitForTimeout(300);
    if(await page.getByRole('combobox',{name:'Versão do modelo'}).inputValue()!==ids.a)throw Error('Stale original replaced selected model');
  });
  await check('texture submit remains locked with its draft across area changes',async()=>{
    await reset('texturizar',{source:ids.a});await page.locator('.s-texture-form input[type=file]').first().setInputFiles('C:/Users/arthu/OneDrive/Documentos/Codex/forge3D-ai/data/test-inputs/hinata-shoyo-reference-20261011.png');delayed='post';
    await page.getByRole('button',{name:'Gerar textura',exact:true}).click();
    await page.getByRole('link',{name:'Biblioteca',exact:true}).click();await page.getByRole('link',{name:'Texturizar',exact:true}).click();
    if(await page.locator('.s-texture-form .s-primary').isEnabled())throw Error('Texture form accepted an overlapping submission');
    if(posts.length!==1)throw Error('Expected one texture POST');
    // Native input is deliberately cleared so re-selecting the same file fires change;
    // the actual File and preview live in the retained React draft.
    if(!(await page.locator('.s-texture-form .s-upload.has-image').first().textContent()).includes('hinata-shoyo-reference-20261011.png'))throw Error('Reference draft lost after navigation');
  });
  await check('late imported model cannot replace a newly chosen texture source',async()=>{
    await reset('texturizar',{source:ids.a,library:ids.c});
    await page.getByRole('button',{name:'Importar modelo existente',exact:true}).click();
    await page.locator('.s-texture-form input[name=model]').setInputFiles('C:/Users/arthu/OneDrive/Documentos/Codex/forge3D-ai/data/assets/57a3da2b44d640b8b54c083e64a5ca6b/model.glb');delayed='post';
    await page.getByRole('button',{name:'Importar modelo',exact:true}).click();
    await page.getByRole('link',{name:'Biblioteca',exact:true}).click();
    await page.getByRole('button',{name:'Texturizar',exact:true}).click();release();await page.waitForTimeout(350);
    const source=await page.evaluate(()=>JSON.parse(sessionStorage.getItem('forge3d.studio.selection.v1')).source);
    if(source!==ids.c)throw Error('Stale import replaced newly chosen source: '+source);
  });
  await check('export pipeline selection recovers only the matching package',async()=>{
    await reset('modelar',{model:ids.a});await page.getByRole('button',{name:'Exportar',exact:true}).click();
    await page.getByRole('combobox',{name:'Pipeline do Unity'}).selectOption('Built-in');
    if(!(await page.getByRole('button',{name:'Preparar exportação',exact:true}).isEnabled()))throw Error('Built-in selection blocked by URP package');
    if(await page.getByRole('link',{name:'Pacote para Unity',exact:true}).count())throw Error('URP download remains under Built-in selection');
    await page.getByRole('button',{name:'Preparar exportação',exact:true}).click();
    if(!posts.some(p=>JSON.parse(p.body).pipeline==='Built-in'))throw Error('Missing Built-in export request');
  });
  await page.unroute('**/api/**');
  return results;
}
