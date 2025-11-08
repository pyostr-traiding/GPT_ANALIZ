import time
from uuid import uuid4

from google import genai
from telebot import types
from telebot.types import Message

from API.gemini.api import send_gpt_data
from API.panel.gpt import get_prompt
from app.core.accumulation.plotter import plot_market_and_report
from app.core.scripts.ulils.s_redis import add_message
from app.core.trend.analysis import combine_multitimeframe_analysis, simplify_klines
from app.core.klines import get_klines
from app.core.trend.indicators.trend_analysis import analyze_market_current_trend
from app.core.trend.indicators.trend_plot import plot_analysis
from conf.settings import settings
from utils.s3 import upload_image


# ---------------------- Вспомогательные функции ---------------------- #

def send_updates(message: Message, text: str):
    """Редактирует сообщение в Telegram с небольшой задержкой"""
    time.sleep(0.1)
    return settings.tg_client.edit_message_text(
        chat_id=message.chat.id,
        message_id=message.message_id,
        text=message.text + text
    )


def log_step(message: Message, chat_uuid: str, text: str):
    """Обновляет сообщение и логирует действие"""
    message = send_updates(message, f"\n{text}")
    add_message(
        chat_uuid=chat_uuid,
        action='general_analysis',
        message_type='text',
        message=text.strip(),
        role='assistant'
    )
    return message


def analyze_trends(kline_1, kline_15, kline_30, kline_60):
    """Анализ трендов для всех таймфреймов"""
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
    """Построение зон и получение отчета по ним"""
    return plot_market_and_report(kline_1, kline_15, kline_30, kline_60)


def gpt_step(chat, prompt_key: str, data, message: Message, chat_uuid: str, title: str):
    """Выполняет шаг GPT анализа с логированием"""
    message = log_step(message, chat_uuid, f"- Обработка {title}")
    prompt = get_prompt(prompt_key)

    # Промпт — пользователь
    add_message(
        chat_uuid=chat_uuid,
        action='general_analysis',
        message_type='text',
        message=prompt.prompt,
        role='user'
    )

    result = send_gpt_data(chat=chat, prompt=prompt.prompt, data=data)
    if not result:
        log_step(message, chat_uuid, f"- ❌ Ошибка обработки {title}. Прервано.")
        return None

    # Ответ — ассистент
    add_message(
        chat_uuid=chat_uuid,
        action='general_analysis',
        message_type='text',
        message=result,
        role='assistant'
    )
    return result


def send_final_report(message: Message, gpt_text: str, image_trend, image_zones, chat_uuid: str):
    """Отправка финального отчёта и изображений в Telegram"""
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
        log_step(message, chat_uuid, f"- ❌ Ошибка отправки: {e}")
        try:
            settings.tg_client.send_media_group(
                chat_id=message.chat.id,
                media=[
                    types.InputMediaPhoto(media=image_trend),
                    types.InputMediaPhoto(media=image_zones),
                ]
            )
            for i in range(0, len(gpt_text), 1000):
                settings.tg_client.send_message(chat_id=message.chat.id, text=gpt_text[i:i + 1000])
            return True
        except:
            return False


# ---------------------- Основной сценарий ---------------------- #

def general_script(message: Message, tg_id: str):
    chat_uuid = str(uuid4())  # единый UUID на весь цикл

    # --- Сбор данных ---
    message = log_step(message, chat_uuid, "\n\n- 📊 Сбор и подготовка данных")
    kline_1, kline_15, kline_30, kline_60 = get_klines()
    message = log_step(message, chat_uuid, "- Свечи получены")

    # --- Анализ трендов ---
    data_trend = analyze_trends(kline_1, kline_15, kline_30, kline_60)
    message = log_step(message, chat_uuid, "- Тренды обработаны")

    image_trend, data_trend = plot_analysis(data_trend)
    message = log_step(message, chat_uuid, "- Анализ тренда завершён")

    # --- Зоны ---
    image_zones, report_zones, data_zones = plot_zones(kline_1, kline_15, kline_30, kline_60)
    message = log_step(message, chat_uuid, "- Зоны построены")

    # --- Загрузка изображений ---
    img_zones = upload_image(f"image_zones-{chat_uuid}", image_zones)
    img_trend = upload_image(f"image_trend-{chat_uuid}", image_trend)

    add_message(chat_uuid, 'general_analysis', 'img_url', img_zones, role='assistant')
    add_message(chat_uuid, 'general_analysis', 'img_url', img_trend, role='assistant')

    # --- GPT обработка ---
    message = log_step(message, chat_uuid, "\n\n- 🤖 GPT обработка")
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    chat = client.chats.create(model="gemini-2.5-flash")

    # Анализ тренда
    gpt_trend = gpt_step(chat, 'trend_analiz_klines', data_trend, message, chat_uuid, 'тренда')
    if not gpt_trend:
        return True

    # Анализ зон
    gpt_zone = gpt_step(chat, 'zone_analiz', report_zones, message, chat_uuid, 'зон')
    if not gpt_zone:
        return True

    # Финальное сведение
    message = log_step(message, chat_uuid, "- Сведение информации")
    prompt_final = get_prompt('zone_analiz_final')

    add_message(chat_uuid, 'general_analysis', 'text', prompt_final.prompt, role='user')
    gpt_final = send_gpt_data(chat=chat, prompt='zone_analiz_final')

    if not gpt_final:
        log_step(message, chat_uuid, "- ❌ Ошибка финальной обработки. Прервано.")
        return True

    add_message(chat_uuid, 'general_analysis', 'text', gpt_final, role='assistant')

    # --- Отправка результатов ---
    image_trend.seek(0)
    image_zones.seek(0)
    return send_final_report(message, gpt_final, image_trend, image_zones, chat_uuid)
