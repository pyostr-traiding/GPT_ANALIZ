from typing import Union

import requests

from API.schemas.settings import SettingsBanSchema
from app.entrypoints.schemas.prompt import PromptSchema
from conf.settings import settings


def get_prompt(
        prompt_code: str,
) -> Union[PromptSchema, None]:
    """
    Получить промпт
    """
    params = {
        'code': prompt_code
    }
    url = f'{settings.BASE_API_URL}/settings/gpt/prompt/'
    response = requests.get(
        url=url,
        params=params,
    )

    if response.status_code == 200:
        return PromptSchema(**response.json())
