from typing import Optional

from pydantic import BaseModel, Field


class SettingsBanSchema(BaseModel):
    """
    Модель настройки
    """
    side: Optional[str] = None
    can_open_position: Optional[str] = None
    turn_value: Optional[float] = None