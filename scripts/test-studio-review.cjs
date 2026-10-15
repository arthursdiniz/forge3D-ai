const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const ts=require('../frontend/node_modules/typescript');
function load(path){const exports={};vm.runInNewContext(ts.transpileModule(fs.readFileSync(path,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,{exports,crypto:require('node:crypto').webcrypto});return exports;}
test('assisted body submits its CPU provider; other strategies preserve the chosen provider',()=>{
  const {effectiveGenerationProvider}=load('frontend/src/generationOptions.ts');
  assert.equal(effectiveGenerationProvider('hunyuan_mini',{character_mode:true,strategy:'base_mesh'}),'character_base_mesh');
  assert.equal(effectiveGenerationProvider('triposg',{character_mode:true,strategy:'generative'}),'triposg');
  assert.equal(effectiveGenerationProvider('triposr',{character_mode:false,strategy:'base_mesh'}),'triposr');
});
