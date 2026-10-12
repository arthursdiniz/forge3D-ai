from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

class GenerationOptions(BaseModel):
    model_config = ConfigDict(extra='forbid')
    quality: Literal['fast','balanced','quality','advanced','draft','high'] = 'balanced'
    remove_background: bool = False
    foreground_ratio: float | None = Field(default=None, ge=0.5, le=0.95)
    crop: tuple[float,float,float,float] | None = None
    texture_resolution: Literal[512,1024,2048,4096] | None = None
    background_mode: Literal['auto','keep','remove','preserve_alpha'] | None = None
    preparation_preset: Literal['character','stylized_character','prop','hard_surface','organic'] = 'prop'
    seed: int | None = Field(default=None,ge=0,le=4294967295,strict=True)
    reference_texture: Literal['none','front'] = 'none'
    refine_reference: bool = False
    quality_mode: bool = False
    candidate_count: Literal[1,3,5] | None = None
    character_mode: bool = False
    character_category: Literal['humanoid','anime','cartoon','nonhuman','custom'] = 'humanoid'
    analysis_id: str | None = Field(default=None,pattern=r'^[a-f0-9]{32}$')
    strategy: Literal['generative','base_mesh','auto'] = 'generative'

    @model_validator(mode='after')
    def validate_workflow(self):
        if self.candidate_count is not None and not self.quality_mode:raise ValueError('Quantidade de candidatos exige Quality Mode.')
        if self.strategy=='base_mesh' and (not self.character_mode or self.analysis_id is None):raise ValueError('Base mesh exige Character Mode e interpretação revisada.')
        return self

class Operation(BaseModel):
    model_config = ConfigDict(extra='forbid')
    operation: Literal['decimate','recalculate_normals','center','apply_transforms','fix_scale','triangulate','validate','inspect_materials','cleanup','refine_silhouette','symmetry','sculpt_refine','game_ready','analyze_character','project_texture']
    ratio: float = Field(default=0.5, ge=0.01, le=1)
    height: float = Field(default=1, ge=0.001, le=1000)
    max_fragment_faces: int = Field(default=32,ge=0,le=32,strict=True)
    max_fragment_extent: float = Field(default=0.006,ge=0,le=0.006)
    refinement_strength: float = Field(default=0.65,ge=0,le=1)
    max_displacement_ratio: float = Field(default=0.03,ge=0,le=0.03)
    symmetry_mode: Literal['off','soft','strong','custom'] = 'off'
    symmetry_regions: list[str] = Field(default_factory=list,max_length=16)
    symmetry_confirmed: bool = False
    symmetry_strength: float = Field(default=0.2,ge=0,le=1)
    plane_yaw_degrees: float = Field(default=0,ge=-180,le=180)
    plane_offset_ratio: float = Field(default=0,ge=-.2,le=.2)
    region_bounds: tuple[float,float,float,float] | None = None
    protected_bounds: list[tuple[float,float,float,float]] = Field(default_factory=list,max_length=16)
    sculpt_strength: float = Field(default=.1,ge=0,le=.25)
    sculpt_iterations: int = Field(default=2,ge=1,le=5,strict=True)
    target_triangles: int = Field(default=20000,ge=100,le=1000000,strict=True)
    bake_normal: bool = False
    texture_resolution: Literal[1024,2048,4096] = 1024
    texture_views: Literal['front','available'] = 'front'

    @model_validator(mode='after')
    def validate_correction(self):
        if self.operation=='symmetry' and self.symmetry_mode!='off' and (not self.symmetry_confirmed or not self.symmetry_regions):raise ValueError('Confirme pose/plano e selecione regiões antes de aplicar simetria.')
        for box in ([self.region_bounds] if self.region_bounds else [])+self.protected_bounds:
            left,bottom,right,top=box
            if not (0<=left<right<=1 and 0<=bottom<top<=1):raise ValueError('Região deve usar coordenadas normalizadas válidas.')
        return self

class ExportOptions(BaseModel):
    pipeline: Literal['URP','Built-in'] = 'URP'
    include_obj: bool = True
    include_glb: bool = True

class QualityReview(BaseModel):
    model_config = ConfigDict(extra='forbid')
    category: Literal['prop','stylized_character','detailed_scene','character_user','hinata']
    variant: Literal['baseline','fast','balanced','quality','triposg','triposg_quality','triposg_refined','baseline_triposr','triposr_corrected','triposg_quality42','advanced42','advanced43']
    ratings: dict[Literal['fidelity','silhouette','proportions','details','textures','rear_geometry','unity'],Annotated[int,Field(strict=True,ge=1,le=5)]]
    notes: str = Field(default='',max_length=4000)
