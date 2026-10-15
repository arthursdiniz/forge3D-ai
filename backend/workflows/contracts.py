from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class ModelWorkflowOptions(BaseModel):
    model_config = ConfigDict(extra='forbid')
    category: Literal['character', 'anime', 'object'] = 'object'
    quality: Literal['fast', 'balanced', 'quality'] = 'balanced'
    provider: Literal['auto', 'triposr', 'triposg', 'hunyuan_mini', 'hunyuan_mv'] = 'auto'
    background_mode: Literal['auto', 'remove', 'preserve_alpha', 'keep'] = 'auto'
    seed: int = Field(42, ge=0, le=4294967295, strict=True)
    request_key: str | None = Field(None, min_length=8, max_length=100, pattern=r'^[a-zA-Z0-9_-]+$')


class TextureWorkflowOptions(BaseModel):
    model_config = ConfigDict(extra='forbid')
    goal: Literal['reference', 'anime', 'stylized', 'realistic', 'hand_painted', 'low_poly'] = 'reference'
    quality: Literal['fast', 'balanced', 'quality'] = 'balanced'
    provider: Literal['auto', 'neural_multiview', 'reference_projection'] = 'auto'
    use_saved_references: bool = True
    background_mode: Literal['remove', 'preserve_alpha'] = 'remove'
    front_axis: Literal['negative_y', 'x'] | None = None
    seed: int = Field(44, ge=0, le=4294967295, strict=True)
    prompt: str = Field('', max_length=2000)
    request_key: str | None = Field(None, min_length=8, max_length=100, pattern=r'^[a-zA-Z0-9_-]+$')
