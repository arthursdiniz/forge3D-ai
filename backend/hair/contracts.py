import math
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,model_validator
from .presets import PRESETS

class HairAttributes(BaseModel):
    model_config=ConfigDict(extra='forbid')
    volume:float|None=Field(None,ge=0,le=.6)
    lateral_volume:float|None=Field(None,ge=0,le=.6)
    back_volume:float|None=Field(None,ge=0,le=.6)
    top_height:float|None=Field(None,ge=0,le=.6)
    spikes:float|None=Field(None,ge=0,le=1)
    thickness:float|None=Field(None,ge=.008,le=.3)
    fringe:float|None=Field(None,ge=0,le=1)
    length:float|None=Field(None,ge=.01,le=1.5)
    curvature:float|None=Field(None,ge=0,le=1)
    asymmetry:float|None=Field(None,ge=0,le=1)
    @model_validator(mode='after')
    def finite(self):
        if any(not math.isfinite(v) for v in self.model_dump().values() if v is not None):raise ValueError('Nonfinite hair attribute.')
        return self

class HairAnalysisOptions(BaseModel):
    model_config=ConfigDict(extra='forbid')
    front_axis:Literal['negative_y','x']='negative_y'
    style:Literal['anime','stylized','realistic']='anime'
    preset:str='auto'
    reference_analysis_id:str|None=Field(None,pattern=r'^[a-f0-9]{32}$')
    source_face:tuple[float,float,float,float]|None=None
    target_face:tuple[float,float,float,float]|None=None
    head_box:tuple[float,float,float,float]|None=None
    hair_polygon:list[tuple[float,float]]|None=Field(None,min_length=3,max_length=64)
    protected_polygons:list[list[tuple[float,float]]]=Field(default_factory=list,max_length=24)
    extra_scalp_boxes:dict[Literal['side','back'],tuple[float,float,float,float]]=Field(default_factory=dict)
    @model_validator(mode='after')
    def bounds(self):
        if self.preset not in PRESETS:raise ValueError('Unknown hair preset.')
        for box in [self.source_face,self.target_face,self.head_box,*self.extra_scalp_boxes.values()]:
            if box and (not all(math.isfinite(v) and 0<=v<=1 for v in box) or box[0]>=box[2] or box[1]>=box[3]):raise ValueError('Invalid face/head bounds.')
        for polygon in [self.hair_polygon,*self.protected_polygons]:
            if polygon is not None and (not 3<=len(polygon)<=64 or not all(math.isfinite(v) and 0<=v<=1 for p in polygon for v in p)):raise ValueError('Invalid hair/protection polygon.')
        return self

class HairRefineOptions(BaseModel):
    model_config=ConfigDict(extra='forbid')
    analysis_id:str=Field(pattern=r'^[a-f0-9]{32}$')
    front_axis:Literal['negative_y','x']='negative_y'
    preset:str='auto'
    attributes:HairAttributes=Field(default_factory=HairAttributes)
    reviewed:bool=False
    @model_validator(mode='after')
    def reviewed_mask(self):
        if not self.reviewed:raise ValueError('Review hair mask/scalp/alignment before reconstruction.')
        if self.preset not in PRESETS:raise ValueError('Unknown hair preset.')
        return self
