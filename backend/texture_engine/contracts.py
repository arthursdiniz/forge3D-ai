from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
import math

class MaterialOptions(BaseModel):
    model_config=ConfigDict(extra='forbid')
    metallic: float|None=Field(None,ge=0,le=1)
    roughness: float|None=Field(None,ge=0,le=1)

class TextureOptions(BaseModel):
    model_config=ConfigDict(extra='forbid')
    provider: Literal['reference_projection','neural_multiview','advanced_pbr']='reference_projection'
    resolution: Literal[1024,2048,4096]=2048
    uv_mode: Literal['auto','preserve','new']='auto'
    front_axis: Literal['negative_y','x']='negative_y'
    background_mode: Literal['preserve_alpha','remove']='preserve_alpha'
    use_saved_references: bool=False
    conditioning: Literal['image','text']='image'
    prompt: str=Field('',max_length=2000)
    style: Literal['free','anime','stylized','realistic','hand_painted','low_poly']='free'
    seed: int|None=Field(None,ge=0,le=4294967295,strict=True)
    fidelity: float=Field(1,ge=.1,le=2)
    profile: Literal['conservative']='conservative'
    fusion: Literal['winner','robust']='robust'
    materials: dict[str,MaterialOptions]=Field(default_factory=dict,max_length=64)

    @model_validator(mode='after')
    def capabilities(self):
        if self.provider=='reference_projection' and (self.prompt or self.style!='free' or self.seed is not None or self.fidelity!=1 or self.conditioning!='image'):
            raise ValueError('Projection does not support neural prompt/style/seed/fidelity/text controls.')
        if self.provider=='advanced_pbr':raise ValueError('Advanced PBR has no validated local backend.')
        if self.provider=='neural_multiview' and self.conditioning=='text' and not self.prompt.strip():raise ValueError('Text conditioning requires a prompt.')
        if self.conditioning=='text' and self.fidelity!=1:raise ValueError('Text-only conditioning has no reference fidelity parameter.')
        return self

class RegionRefineOptions(BaseModel):
    model_config=ConfigDict(extra='forbid')
    provider: Literal['reference_region']='reference_region'
    source_box: tuple[float,float,float,float]
    target_box: tuple[float,float,float,float]
    source_polygon: list[tuple[float,float]]|None=Field(None,min_length=3,max_length=64)
    target_polygon: list[tuple[float,float]]|None=Field(None,min_length=3,max_length=64)
    protected: list[list[tuple[float,float]]]=Field(default_factory=list,max_length=32)
    source_points: list[tuple[float,float]]=Field(default_factory=list,max_length=28)
    target_points: list[tuple[float,float]]=Field(default_factory=list,max_length=28)
    materials: list[str]=Field(default_factory=list,max_length=64)
    region: Literal['face','hair','eyes','clothing','custom']='face'
    front_axis: Literal['negative_y','x']='negative_y'
    background_mode: Literal['auto','preserve_alpha','remove']='auto'
    intensity: float=Field(1,ge=.1,le=1)
    feather_pixels: int=Field(4,ge=0,le=16,strict=True)
    minimum_cosine: float=Field(.75,ge=.5,le=.99)
    camera_resolution: Literal[512,1024,2048]=1024
    face_resolution: Literal[512,768,1024]=768
    seam_correction: bool=True
    cached_views: bool=False
    reviewed_alignment: bool=False
    @model_validator(mode='after')
    def bounded_reviewed(self):
        for box in [self.source_box,self.target_box]:
            if not all(math.isfinite(v) and 0<=v<=1 for v in box) or box[0]>=box[2] or box[1]>=box[3]:raise ValueError('Invalid normalized region rectangle.')
        for polygon in [self.source_polygon,self.target_polygon,*self.protected,self.source_points,self.target_points]:
            if polygon is None:continue
            if not all(math.isfinite(v) and 0<=v<=1 for point in polygon for v in point):raise ValueError('Region coordinates must be finite in[0,1].')
        if any(not 3<=len(p)<=64 for p in self.protected):raise ValueError('Protection polygons need3–64points.')
        if len(self.source_points)!=len(self.target_points) or (self.source_points and len(self.source_points)<3):raise ValueError('Use at least3 paired alignment landmarks.')
        if not self.reviewed_alignment:raise ValueError('Review alignment before applying regional correction.')
        if not math.isfinite(self.intensity) or not math.isfinite(self.minimum_cosine):raise ValueError('Nonfinite refinement setting.')
        return self
