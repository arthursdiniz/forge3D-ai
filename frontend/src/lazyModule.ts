import { lazy, type ComponentType } from 'react';

// An open tab may reference a hashed chunk removed by a local rebuild.
// Reload once to obtain the current entry point; never loop indefinitely.
export function lazyModule<T extends ComponentType<any>>(load:()=>Promise<{default:T}>){
  return lazy(async()=>{
    try{return await load();}
    catch(error){
      const message=String(error);
      if(/dynamically imported module|Importing a module script|error loading dynamically/i.test(message)){
        const key='forge3d-chunk-reload',now=Date.now(),last=Number(sessionStorage.getItem(key)||0);
        if(now-last>60000){sessionStorage.setItem(key,String(now));window.location.reload();return new Promise<{default:T}>(()=>{});}
      }
      throw error;
    }
  });
}
