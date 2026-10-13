from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

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
    materials: dict[str,MaterialOptions]=Field(default_factory=dict,max_length=64)

    @model_validator(mode='after')
    def capabilities(self):
        if self.provider=='reference_projection' and (self.prompt or self.style!='free' or self.seed is not None or self.fidelity!=1 or self.conditioning!='image'):
            raise ValueError('Projection does not support neural prompt/style/seed/fidelity/text controls.')
        if self.provider=='advanced_pbr':raise ValueError('Advanced PBR has no validated local backend.')
        if self.provider=='neural_multiview' and self.conditioning=='text' and not self.prompt.strip():raise ValueError('Text conditioning requires a prompt.')
        if self.conditioning=='text' and self.fidelity!=1:raise ValueError('Text-only conditioning has no reference fidelity parameter.')
        return self
