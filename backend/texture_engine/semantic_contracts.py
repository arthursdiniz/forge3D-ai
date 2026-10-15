import math
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,model_validator
from .semantic_taxonomy import CLASS_IDS,CLASS_NAMES

class Stroke(BaseModel):
    model_config=ConfigDict(extra='forbid')
    points:list[tuple[float,float]]=Field(min_length=1,max_length=2048)
    radius:float=Field(.02,ge=.001,le=.12)
    label:int=Field(0,ge=0,le=len(CLASS_NAMES)-1,strict=True)
    operation:Literal['paint','erase','restore']='paint'
    @model_validator(mode='after')
    def finite(self):
        if not all(math.isfinite(v) and 0<=v<=1 for point in self.points for v in point) or not math.isfinite(self.radius):raise ValueError('Invalid intrinsic mask stroke.')
        return self

class Registration(BaseModel):
    model_config=ConfigDict(extra='forbid')
    source_box:tuple[float,float,float,float]=(0,0,1,1)
    target_box:tuple[float,float,float,float]=(0,0,1,1)
    target_polygon:list[tuple[float,float]]|None=Field(None,min_length=3,max_length=64)
    source_points:list[tuple[float,float]]=Field(default_factory=list,max_length=28)
    target_points:list[tuple[float,float]]=Field(default_factory=list,max_length=28)
    protected:list[list[tuple[float,float]]]=Field(default_factory=list,max_length=32)
    minimum_cosine:float=Field(.65,ge=.5,le=.99)
    accept_unknown_target:bool=False
    @model_validator(mode='after')
    def valid(self):
        for box in [self.source_box,self.target_box]:
            if not all(math.isfinite(v) and 0<=v<=1 for v in box) or box[0]>=box[2] or box[1]>=box[3]:raise ValueError('Invalid reviewed view rectangle.')
        if len(self.source_points)!=len(self.target_points) or (self.source_points and len(self.source_points)<3):raise ValueError('Use3–28corresponding landmarks.')
        for points in [self.source_points,self.target_points,self.target_polygon or [],*self.protected]:
            if not all(math.isfinite(v) and 0<=v<=1 for p in points for v in p):raise ValueError('Invalid normalized alignment/protection coordinates.')
        if any(not 3<=len(p)<=64 for p in self.protected):raise ValueError('Protection polygons need3–64points.')
        if not math.isfinite(self.minimum_cosine):raise ValueError('Invalid projection angle.')
        return self

class SemanticPolygon(BaseModel):
    model_config=ConfigDict(extra='forbid')
    points:list[tuple[float,float]]=Field(min_length=3,max_length=64)
    label:int=Field(ge=0,le=len(CLASS_NAMES)-1,strict=True)
    @model_validator(mode='after')
    def valid(self):
        if not all(math.isfinite(v) and 0<=v<=1 for p in self.points for v in p):raise ValueError('Invalid semantic region polygon.')
        return self

class SemanticView(BaseModel):
    model_config=ConfigDict(extra='forbid')
    profile:Literal['anime','stylized','manual']='anime'
    source_crop:tuple[float,float,float,float]|None=None
    target_crop:tuple[float,float,float,float]|None=None
    source_strokes:list[Stroke]=Field(default_factory=list,max_length=256)
    target_strokes:list[Stroke]=Field(default_factory=list,max_length=256)
    source_polygons:list[SemanticPolygon]=Field(default_factory=list,max_length=32)
    target_polygons:list[SemanticPolygon]=Field(default_factory=list,max_length=32)
    registration:Registration=Field(default_factory=Registration)
    @model_validator(mode='after')
    def bounded(self):
        for box in [self.source_crop,self.target_crop]:
            if box is not None and (not all(math.isfinite(v) and 0<=v<=1 for v in box) or box[0]>=box[2] or box[1]>=box[3]):raise ValueError('Invalid portrait crop.')
        if sum(len(s.points) for s in self.source_strokes+self.target_strokes)>8192:raise ValueError('Stroke point budget exceeded.')
        return self

class SemanticAnalysisOptions(BaseModel):
    model_config=ConfigDict(extra='forbid')
    front_axis:Literal['negative_y','x']='negative_y'
    base_analysis_id:str|None=Field(None,pattern='^[a-f0-9]{32}$')
    views:dict[Literal['front','back','left','right'],SemanticView]=Field(default_factory=lambda:{'front':SemanticView()},min_length=1,max_length=4)

class SemanticPaintOptions(BaseModel):
    model_config=ConfigDict(extra='forbid')
    provider:Literal['semantic_reference']='semantic_reference'
    analysis_id:str=Field(pattern='^[a-f0-9]{32}$')
    front_axis:Literal['negative_y','x']='negative_y'
    classes:list[str]=Field(default_factory=lambda:['hair','face','eyes','mouth','clothes'],min_length=1,max_length=24)
    protected_classes:list[str]=Field(default_factory=list,max_length=24)
    reviewed_alignment:bool=False
    operation:Literal['reference','color_adjust']='reference'
    tint:tuple[float,float,float]=(1,1,1)
    intensity:float=Field(1,ge=.05,le=1)
    feather_pixels:int=Field(0,ge=0,le=16,strict=True)
    surface_fill:bool=False
    fill_radius:float=Field(.01,ge=.001,le=.025)
    seam_correction:bool=True
    completion:Literal['preserve','neural']='preserve'
    prompt:str=Field('',max_length=2000)
    style:Literal['anime','stylized','realistic','free']='anime'
    seed:int=Field(44,ge=0,le=4294967295,strict=True)
    @model_validator(mode='after')
    def scope(self):
        if not self.reviewed_alignment:raise ValueError('Review masks and compatible pose/alignment before semantic painting.')
        if any(name not in CLASS_IDS or name in ['unknown','background'] for name in self.classes+self.protected_classes):raise ValueError('Unknown or unsupported selected semantic category.')
        if any(not math.isfinite(v) or not 0<=v<=2 for v in self.tint):raise ValueError('Invalid regional tint.')
        if not math.isfinite(self.intensity) or not math.isfinite(self.fill_radius):raise ValueError('Nonfinite semantic setting.')
        if self.operation=='color_adjust' and self.completion!='preserve':raise ValueError('Color adjustment is separate from neural completion.')
        return self
