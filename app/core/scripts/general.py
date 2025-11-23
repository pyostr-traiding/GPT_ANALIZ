import time
import json
import requests
from uuid import uuid4
from telebot import types
from telebot.types import Message

from app.core.scripts.ulils.s_redis import add_message
from app.core.accumulation.plotter import plot_market_and_report
from app.core.trend.analysis import combine_multitimeframe_analysis, simplify_klines
from app.core.klines import get_klines
from app.core.trend.indicators.trend_analysis import analyze_market_current_trend
from app.core.trend.indicators.trend_plot import plot_analysis
from app.entrypoints.handlers.actions.schemas.actions import ActionSchema
from conf.settings import settings
from utils.s3 import upload_image
from app.entrypoints.decorators import action_handler

HEADERS_API = {
    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",  # ключ в settings
}
API_URL = 'https://openrouter.ai/api/v1/chat/completions'


# ---------------------- Вспомогательные функции ---------------------- #

def send_updates(message: Message, text: str):
    time.sleep(0.1)
    return settings.tg_client.edit_message_text(
        chat_id=message.chat.id,
        message_id=message.message_id,
        text=message.text + text
    )


def log_step(message: Message, chat_uuid: str, text: str, data: ActionSchema):
    message = send_updates(message, f"\n{text}")
    add_message(
        chat_uuid=chat_uuid,
        action='general_analysis',
        message_type='text',
        message=text.strip(),
        role='assistant',
        context=data.extra.context,
        code=data.extra.code,
    )
    return message


def analyze_trends(kline_1, kline_15, kline_30, kline_60):
    analyses = [
        analyze_market_current_trend(kline_1),
        analyze_market_current_trend(kline_15),
        analyze_market_current_trend(kline_30),
        analyze_market_current_trend(kline_60)
    ]
    weights = [1, 2, 3, 4]
    final_signal = combine_multitimeframe_analysis(analyses, weights)
    return {
        "timeframes": {
            "1m": {"analysis": analyses[0], "klines": simplify_klines(kline_1)},
            "15m": {"analysis": analyses[1], "klines": simplify_klines(kline_15)},
            "30m": {"analysis": analyses[2], "klines": simplify_klines(kline_30)},
            "60m": {"analysis": analyses[3], "klines": simplify_klines(kline_60)},
        },
        "final_signal": final_signal
    }


def plot_zones(kline_1, kline_15, kline_30, kline_60):
    return plot_market_and_report(kline_1, kline_15, kline_30, kline_60)


def gpt_step(chat_uuid: str, prompt_text: str, message: Message, title: str, data: ActionSchema):
    message = log_step(message, chat_uuid, f"- Обработка {title}", data=data)

    # Записываем пользовательский промпт
    add_message(chat_uuid, 'general_analysis', 'text', prompt_text, role='user', code=data.extra.code, context=data.extra.context)

    payload = {
        "model": data.extra.code,
        "messages": [{"role": "user", "content": prompt_text}],
        "temperature": 0.7,
        "max_tokens": 4096
    }

    try:
        response = requests.post(API_URL, headers=HEADERS_API, json=payload, timeout=60)
        response.raise_for_status()
        resp_json = response.json()
        gpt_result = resp_json['choices'][0]['message']['content']

        add_message(chat_uuid, 'general_analysis', 'text', gpt_result, role='assistant', code=data.extra.code, context=data.extra.context)
        return gpt_result

    except Exception as e:
        error_text = f"Ошибка GPT {title}: {str(e)}"
        add_message(chat_uuid, 'general_analysis', 'text', error_text, role='assistant', code=data.extra.code, context=data.extra.context)
        log_step(message, chat_uuid, f"- ❌ {error_text}", data=data)
        return None


def send_final_report(message: Message, gpt_text: str, image_trend, image_zones, chat_uuid: str, data: ActionSchema ):
    try:
        MAX_CAPTION_LEN = 1000
        caption = gpt_text[:MAX_CAPTION_LEN]
        rest = gpt_text[MAX_CAPTION_LEN:]

        settings.tg_client.send_media_group(
            chat_id=message.chat.id,
            media=[
                types.InputMediaPhoto(media=image_trend, caption=caption),
                types.InputMediaPhoto(media=image_zones),
            ]
        )

        for i in range(0, len(rest), 1000):
            settings.tg_client.send_message(chat_id=message.chat.id, text=rest[i:i + 1000])

        return True
    except Exception as e:
        log_step(message, chat_uuid, f"- ❌ Ошибка отправки: {e}", data=data)
        return False


# ---------------------- Основной сценарий ---------------------- #

@action_handler(['general_analysis'])
def general_script(message: Message, data: ActionSchema):
    chat_uuid = str(uuid4())

    message = log_step(message, chat_uuid, "\n\n- 📊 Сбор и подготовка данных", data=data)
    kline_1, kline_15, kline_30, kline_60 = get_klines()
    message = log_step(message, chat_uuid, "- Свечи получены", data=data)

    data_trend = analyze_trends(kline_1, kline_15, kline_30, kline_60)
    message = log_step(message, chat_uuid, "- Тренды обработаны", data=data)

    image_trend, data_trend = plot_analysis(data_trend)
    message = log_step(message, chat_uuid, "- Анализ тренда завершён", data=data)

    image_zones, report_zones, data_zones = plot_zones(kline_1, kline_15, kline_30, kline_60)
    message = log_step(message, chat_uuid, "- Зоны построены", data=data)

    img_zones = upload_image(f"image_zones-{chat_uuid}", image_zones)
    img_trend = upload_image(f"image_trend-{chat_uuid}", image_trend)
    add_message(chat_uuid, 'general_analysis', 'img_url', img_zones, role='assistant', context=data.extra.context, code=data.extra.code)
    add_message(chat_uuid, 'general_analysis', 'img_url', img_trend, role='assistant', context=data.extra.context, code=data.extra.code)

    message = log_step(message, chat_uuid, "\n\n- 🤖 GPT обработка", data=data)

    # GPT анализ тренда
    gpt_trend = gpt_step(chat_uuid, json.dumps(data_trend), message, 'тренда', data=data)
    if not gpt_trend:
        return True

    # GPT анализ зон
    gpt_zone = gpt_step(chat_uuid, json.dumps(report_zones), message, 'зон', data=data)
    if not gpt_zone:
        return True

    # Финальное сведение
    message = log_step(message, chat_uuid, "- Сведение информации", data=data)
    prompt_final = "Объедини анализ тренда и зон в краткий финальный отчет"
    gpt_final = gpt_step(chat_uuid, prompt_final, message, 'финальный отчет', data=data)
    if not gpt_final:
        return True

    image_trend.seek(0)
    image_zones.seek(0)
    return send_final_report(message, gpt_final, image_trend, image_zones, chat_uuid, data=data)
