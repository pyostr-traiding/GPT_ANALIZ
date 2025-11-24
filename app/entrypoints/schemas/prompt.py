from pydantic import BaseModel


class PromptSchema(BaseModel):
    id: int
    title: str
    code: str
    prompt: str
    description: str
