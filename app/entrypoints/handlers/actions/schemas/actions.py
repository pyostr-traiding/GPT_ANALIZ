from typing import Optional

from pydantic import BaseModel

class ExtraData(BaseModel):
    uuid: str
    text: str

class ActionSchema(BaseModel):

    action: str
    tg_id: str
    created_on: str
    extra: Optional[ExtraData] = None