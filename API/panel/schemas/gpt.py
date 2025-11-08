from pydantic import BaseModel, Field


class SettingsPromptSchema(BaseModel):
    """
    Модель промпта
    """
    code: str
    prompt: str
