"""
Системный анализ тренда через OpenRouter API с логированием действий и GPT перепиской
"""
import datetime
import json
import requests

from API.settings import get_prompt
from app.core.accumulation.plotter import plot_market_and_report
from app.core.klines import get_klines
from app.entrypoints.mail import send_to_rabbitmq
from app.core.trend.analysis import combine_multitimeframe_analysis, simplify_klines
from app.core.trend.indicators.trend_analysis import analyze_market_current_trend
from app.core.trend.indicators.trend_plot import plot_analysis
from app.entrypoints.schemas.actions import ActionSchema
from app.entrypoints.s_redis import add_message
from API.schemas.settings import SettingsBanSchema
from conf.settings import settings

API_URL = 'https://openrouter.ai/api/v1/chat/completions'
HEADERS_API = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}


def fetch_klines(chat_uuid: str):
    klines = get_klines()
    return klines


def analyze_trends(kline_1, kline_15, kline_30, kline_60):
    analysis_1m = analyze_market_current_trend(kline_1)
    analysis_15m = analyze_market_current_trend(kline_15)
    analysis_30m = analyze_market_current_trend(kline_30)
    analysis_60m = analyze_market_current_trend(kline_60)
    analyses = [analysis_1m, analysis_15m, analysis_30m, analysis_60m]
    weights = [1, 2, 3, 4]
    final_signal = combine_multitimeframe_analysis(analyses, weights)

    return {
        "timeframes": {
            "1m": {"analysis": analysis_1m, "klines": simplify_klines(kline_1)},
            "15m": {"analysis": analysis_15m, "klines": simplify_klines(kline_15)},
            "30m": {"analysis": analysis_30m, "klines": simplify_klines(kline_30)},
            "60m": {"analysis": analysis_60m, "klines": simplify_klines(kline_60)},
        },
        "final_signal": final_signal
    }


def gpt_request(chat_uuid: str, prompt_name: str, data, action_data: ActionSchema):
    prompt = get_prompt(prompt_code=prompt_name)
    if not prompt:
        add_message(chat_uuid, 'trend_analysis', 'text', 'Ошибка получения промпта', role='system', code=action_data.extra.code, context=action_data.extra.context)
        return
    """Отправка запроса GPT через OpenRouter API с логированием промпта и ответа"""
    prompt_text = f"{str(data)} \n {prompt.prompt}"

    # Логируем отправку запроса
    add_message(chat_uuid, 'trend_analysis', 'text', prompt_text, role='user', code=action_data.extra.code, context=action_data.extra.context)

    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt_text}],
        "temperature": 0.7,
        "max_tokens": 4096
    }

    try:
        resp = requests.post(API_URL, headers=HEADERS_API, json=payload, timeout=60)
        resp.raise_for_status()
        resp_json = resp.json()
        result = resp_json['choices'][0]['message']['content']

        # Логируем ответ GPT
        add_message(chat_uuid, 'trend_analysis', 'text', result, role='assistant', code=action_data.extra.code, context=action_data.extra.context)
        return result
    except Exception as e:
        error_text = f"Ошибка GPT ({prompt_name}): {e}"
        add_message(chat_uuid, 'trend_analysis', 'text', error_text, role='system', code=action_data.extra.code, context=action_data.extra.context)
        print(error_text)
        return None


def get_result_from_text(text: str) -> SettingsBanSchema:
    trend_value = None
    turn_value = None
    position_value = None

    for line in text.split('\n'):
        line = line.replace(' ', '')
        if 'Тренд%' in line:
            val = line.replace('Тренд%', '').replace('%', '')
            if val in ['ШОРТ', 'ЛОНГ', 'БОКОВОЙ']:
                trend_value = val
        elif 'Разворот%' in line:
            val = line.replace('Разворот%', '').replace('%', '')
            turn_value = val
        elif 'Позиция%' in line:
            val = line.replace('Позиция%', '').replace('%', '')
            if val in ['ДА', 'НЕТ', 'СОМНИТЕЛЬНО']:
                position_value = val

    return SettingsBanSchema(
        side=trend_value,
        can_open_position=position_value,
        turn_value=float(turn_value) if turn_value else None,
    )


def handle_trend_analiz(data: ActionSchema):
    chat_uuid = str(datetime.datetime.now().timestamp())
    add_message(chat_uuid, 'trend_analysis', 'text', 'Запуск анализа тренда', role='assistant', code=data.extra.code, context=data.extra.context)

    kline_1, kline_15, kline_30, kline_60 = fetch_klines(chat_uuid)
    add_message(chat_uuid, 'trend_analysis', 'text', 'Свечи получены', role='assistant', code=data.extra.code, context=data.extra.context)

    data_trend = analyze_trends(kline_1, kline_15, kline_30, kline_60)
    add_message(chat_uuid, 'trend_analysis', 'text', 'Тренды обработаны', role='assistant', code=data.extra.code, context=data.extra.context)

    image_trend, _ = plot_analysis(data_trend)
    image_zones, report_zones, _ = plot_market_and_report(kline_1, kline_15, kline_30, kline_60)
    add_message(chat_uuid, 'trend_analysis', 'text', 'Графики построены', role='assistant', code=data.extra.code, context=data.extra.context)

    gpt_answer_trend = gpt_request(chat_uuid, 'trend_analiz_klines', data_trend, action_data=data)
    if not gpt_answer_trend:
        return None

    gpt_answer_zone = gpt_request(chat_uuid, 'zone_analiz', report_zones, action_data=data)
    if not gpt_answer_zone:
        return None

    gpt_system_trend = gpt_request(chat_uuid, 'system_trend', None, action_data=data)
    if not gpt_system_trend:
        return None

    add_message(chat_uuid, 'trend_analysis', 'text', 'GPT сводка готова', role='assistant', code=data.extra.code, context=data.extra.context)

    result = get_result_from_text(gpt_system_trend)
    add_message(chat_uuid, 'trend_analysis', 'text', f'Результат анализа: {result}', role='assistant', code=data.extra.code, context=data.extra.context)

    send_to_rabbitmq({
        "is_test": True,
        "notification": False,
        "text": str(result)
    })

    return result
