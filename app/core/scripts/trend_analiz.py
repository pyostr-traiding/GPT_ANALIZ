"""
Системный анализ тренда

Задача установка в базе данных значения текущего тренда

Собираются данные по свечам

Анализируется тренд, сила тренда, .....

Далее GPT выдает направление и потенциальные точки разворота

"""
import datetime

from google import genai

from API.gemini.api import send_gpt_data
from API.panel.schemas.settings import SettingsBanSchema
from app.core.accumulation.plotter import plot_market_and_report
from app.core.klines import get_klines
from app.core.mail import send_to_rabbitmq
from app.core.trend.analysis import combine_multitimeframe_analysis, simplify_klines
from app.core.trend.indicators.trend_analysis import analyze_market_current_trend
from app.core.trend.indicators.trend_plot import plot_analysis
from conf.settings import settings


def fetch_klines():
    """Получение свечей для разных таймфреймов"""
    return get_klines()  # kline_1, kline_15, kline_30, kline_60

def analyze_trends(kline_1, kline_15, kline_30, kline_60):
    """Анализ трендов для всех таймфреймов"""
    analysis_1m = analyze_market_current_trend(kline_1)
    analysis_15m = analyze_market_current_trend(kline_15)
    analysis_30m = analyze_market_current_trend(kline_30)
    analysis_60m = analyze_market_current_trend(kline_60)
    analyses = [analysis_1m, analysis_15m, analysis_30m, analysis_60m]
    weights = [1, 2, 3, 4]
    final_signal = combine_multitimeframe_analysis(analyses, weights)
    data = {
        "timeframes": {
            "1m": {"analysis": analysis_1m, "klines": simplify_klines(kline_1)},
            "15m": {"analysis": analysis_15m, "klines": simplify_klines(kline_15)},
            "30m": {"analysis": analysis_30m, "klines": simplify_klines(kline_30)},
            "60m": {"analysis": analysis_60m, "klines": simplify_klines(kline_60)},
        },
        "final_signal": final_signal
    }
    return data

def get_result_from_text(text) -> SettingsBanSchema:
    text_split = text.split('\n')

    trend_value = None
    turn_value = None
    position_value = None
    print('-----------', text)
    for i in text_split:
        print('+++', i)
        if 'Тренд%' in i:
            i = i.replace('Тренд%', '').replace('%', '').replace(' ', '')
            if i in ['ШОРТ', 'ЛОНГ', 'БОКОВОЙ']:
              trend_value = i
        elif 'Разворот%' in i:
            i = i.replace('Разворот%', '').replace('%', '').replace(' ', '')
            turn_value = i
        elif 'Позиция%' in i:
            i = i.replace('Позиция%', '').replace('%', '').replace(' ', '')
            if i in ['ДА', 'НЕТ', 'СОМНИТЕЛЬНО']:
                position_value = i

    return SettingsBanSchema(
        side=trend_value,
        can_open_position=position_value,
        turn_value=float(turn_value) if turn_value else None,
    )

def trend_analiz():
    print('Запуск', datetime.datetime.now())

    kline_1, kline_15, kline_30, kline_60 = fetch_klines()

    data_trend = analyze_trends(kline_1, kline_15, kline_30, kline_60)

    image_trend, data_trend = plot_analysis(data_trend)

    image_zones, report_zones, data_zones = plot_market_and_report(kline_1, kline_15, kline_30, kline_60)
    print('Данные готовы', datetime.datetime.now())
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    chat = client.chats.create(model="gemini-2.5-flash-lite")

    gpt_answer_trend = send_gpt_data(chat=chat, prompt_name='trend_analiz_klines', data=data_trend)
    if not gpt_answer_trend:
        print('Нет ответа GPT тренд', gpt_answer_trend)
        return 'Нет ответа GPT gpt_answer_trend'
    gpt_answer_zone = send_gpt_data(chat=chat, prompt_name='zone_analiz', data=report_zones)
    if not gpt_answer_zone:
        print('Нет ответа GPT зоны', gpt_answer_trend)
        return 'Нет ответа GPT gpt_answer_zone'
    gpt_system_trend = send_gpt_data(chat=chat, prompt_name='system_trend')
    if not gpt_system_trend:
        print('Нет ответа GPT системно', gpt_answer_trend)
        return 'Нет ответа GPT gpt_system_trend'
    print('GPT сводка', datetime.datetime.now())
    result = get_result_from_text(gpt_system_trend)
    send_to_rabbitmq(
        {
            "is_test": True,
            "notification": False,
            "text": str(result)
        }
    )
    return result
