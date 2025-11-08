from typing import Union

import requests

from API.panel.schemas.settings import SettingsBanSchema
from conf.settings import settings


def get_prompt(
        data: SettingsBanSchema,
) -> Union[bool, None]:
    """
    Получить промпт
    """
    url = f'{settings.BASE_API_URL}/settings/gpt/getPrompt'
    response = requests.post(
        url=url,
        json=data.model_dump(),
    )

    if response.status_code == 200:
        return True

