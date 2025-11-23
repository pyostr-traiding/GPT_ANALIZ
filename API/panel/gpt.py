import requests

from typing import Union

from conf.settings import settings

from API.panel.schemas.gpt import SettingsPromptSchema


def get_prompt(
        code: str,
) -> Union[SettingsPromptSchema, None]:
    """
    Получить промпт
    """
    url = f'{settings.BASE_API_URL}/settings'
    params = {
        'code': code,
    }
    response = requests.get(
        url=url,
        params=params,
    )

    if response.status_code == 200:
        return SettingsPromptSchema(**response.json())
