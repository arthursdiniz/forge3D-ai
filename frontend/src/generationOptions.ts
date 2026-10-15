export type Category='humanoid'|'anime'|'cartoon'|'nonhuman'|'custom';
export type Options={quality:'fast'|'balanced'|'quality'|'advanced';remove_background:boolean;foreground_ratio:number;texture_resolution:512|1024|2048|4096|null;texture_output:'legacy'|'geometry_only';crop:number[]|null;background_mode:'auto'|'keep'|'remove'|'preserve_alpha';preparation_preset:'character'|'stylized_character'|'prop'|'hard_surface'|'organic';seed:number|null;reference_texture:'none'|'front';refine_reference:boolean;quality_mode:boolean;candidate_count:1|3|5|null;character_mode:boolean;character_category:Category;analysis_id:string|null;strategy:'generative'|'base_mesh'|'auto'};
export type References=Partial<Record<'left'|'back'|'right',File>>;
export function effectiveGenerationProvider(provider:string,options:Pick<Options,'character_mode'|'strategy'>){
  return options.character_mode&&options.strategy==='base_mesh'?'character_base_mesh':provider;
}
