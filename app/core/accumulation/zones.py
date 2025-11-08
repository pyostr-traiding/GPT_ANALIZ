"""
zones.py

Модуль для анализа рыночных данных на предмет зон накопления и распределения.
Содержит функции для поиска этих зон по историческим свечам и расчета статистики по ним.

Функции:
- find_accumulation_and_distribution: определяет зоны накопления и распределения.
- calculate_zone_stats: вычисляет среднюю цену, суммарный объём и прогнозную цену для каждой зоны.
"""

import numpy as np


def find_accumulation_and_distribution(klines, window_size=20, price_std_threshold=0.005,
                                       volume_multiplier=1.2, breakout_multiplier=1.5):
    """
    Поиск зон накопления и распределения на основе исторических данных свечей.

    Параметры:
    - klines: объект с историческими данными свечей
    - window_size: размер окна для вычисления стандартного отклонения цены
    - price_std_threshold: порог относительной волатильности для накопления
    - volume_multiplier: порог увеличенного среднего объема для накопления
    - breakout_multiplier: множитель для определения breakout и зоны распределения

    Возвращает:
    - accumulation_zones: список кортежей (start_idx, end_idx) зон накопления
    - distribution_zones: список кортежей (start_idx, end_idx) зон распределения
    """
    closes = np.array([float(c.data[0].close) for c in klines.history])
    volumes = np.array([float(c.data[0].volume) for c in klines.history])
    avg_volume = np.mean(volumes)

    accumulation_zones = []
    distribution_zones = []

    i = 0
    while i < len(closes) - window_size:
        window = closes[i:i+window_size]
        window_vol = volumes[i:i+window_size]
        std_price = np.std(window) / np.mean(window)
        mean_vol = np.mean(window_vol)

        if std_price < price_std_threshold and mean_vol > avg_volume * volume_multiplier:
            accumulation_zones.append((i, i+window_size))

            # Векторизованный поиск breakout
            future_prices = closes[i+window_size:]
            diffs = np.abs(np.diff(future_prices))
            threshold = np.std(window) * breakout_multiplier
            breakout_idx = np.where(diffs > threshold)[0]
            if len(breakout_idx) > 0:
                distribution_zones.append((i, i+window_size+breakout_idx[0]+1))
                i += window_size + breakout_idx[0] + 1
            else:
                i += window_size
        else:
            i += 1

    return accumulation_zones, distribution_zones


def calculate_zone_stats(closes, volumes, zones):
    """
    Вычисление статистики для каждой зоны: средняя цена, суммарный объем и прогнозная цена.

    Параметры:
    - closes: массив цен закрытия
    - volumes: массив объемов
    - zones: список зон в формате (start_idx, end_idx)

    Возвращает:
    - stats: список словарей с ключами:
        - start_idx, end_idx: индексы начала и конца зоны
        - avg_price: средняя цена зоны
        - sum_volume: суммарный объем зоны
        - forecast_price: прогнозная цена (взвешенное изменение цены внутри зоны)
    """
    stats = []
    for start, end in zones:
        avg_price = np.mean(closes[start:end])
        sum_volume = np.sum(volumes[start:end])
        # Прогноз через взвешенное изменение
        if sum_volume > 0:
            weight = volumes[start:end] / sum_volume
            forecast_price = avg_price + np.sum((closes[start:end] - avg_price) * weight)
        else:
            forecast_price = avg_price
        stats.append({
            "start_idx": start,
            "end_idx": end,
            "avg_price": avg_price,
            "sum_volume": sum_volume,
            "forecast_price": forecast_price
        })
    return stats
