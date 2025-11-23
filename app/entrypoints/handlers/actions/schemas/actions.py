from typing import Optional

from pydantic import BaseModel

class ExtraData(BaseModel):
    class Config:
        from_attributes = True
    uuid: str
    text: str
    code: str
    context: int

class ActionSchema(BaseModel):
    class Config:
        from_attributes = True
    action: str
    tg_id: str
    created_on: str
    extra: Optional[ExtraData] = None