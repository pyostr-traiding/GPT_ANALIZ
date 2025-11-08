import numpy as np
from matplotlib import pyplot as plt, patches
import matplotlib.dates as mdates
from io import BytesIO

from app.core.accumulation.zones import find_accumulation_and_distribution, calculate_zone_stats
from utils.time import ms_to_dt_obj

def plot_market_and_report(kline_1, kline_15, kline_30, kline_60, window_size=20, forecast_multiplier=0.5):
    """
    Формирует графики зон накопления и распределения, но не выводит их на экран.
    Возвращает изображение в буфере, текстовый отчет и данные по зонам.

    Параметры:
    - kline_1, kline_15, kline_30, kline_60: данные свечей для разных таймфреймов
    - window_size: размер окна для определения зон
    - forecast_multiplier: длина прогноза зоны относительно длины самой зоны

    Возвращает:
    - img_buffer: BytesIO с изображением
    - report_lines: список строк с текстовым отчетом
    - all_zones_data: словарь с данными по зонам для каждого таймфрейма
    """
    timeframes = {"1m": kline_1, "15m": kline_15, "30m": kline_30, "60m": kline_60}
    report_lines = []
    all_zones_data = {}

    fig, axes = plt.subplots(4, 2, figsize=(18, 20), gridspec_kw={'width_ratios':[3,1]})

    for i, (tf, klines) in enumerate(timeframes.items()):
        closes = np.array([float(c.data[0].close) for c in klines.history])
        volumes = np.array([float(c.data[0].volume) for c in klines.history])
        times = [ms_to_dt_obj(c.data[0].start) for c in klines.history]

        acc_zones, dist_zones = find_accumulation_and_distribution(klines, window_size=window_size)
        acc_stats = calculate_zone_stats(closes, volumes, acc_zones)
        dist_stats = calculate_zone_stats(closes, volumes, dist_zones)

        all_zones_data[tf] = {
            "accumulation": acc_stats,
            "distribution": dist_stats
        }

        # Текущий статус
        if acc_zones and dist_zones:
            current_status = "Сейчас идет распределение после накопления"
        elif acc_zones:
            current_status = "Сейчас идет накопление"
        elif dist_zones:
            current_status = "Сейчас идет распределение"
        else:
            current_status = "Нет значимых зон"

        report_lines.append(f"{tf} — {current_status}, накопление зон: {len(acc_zones)}, распределение зон: {len(dist_zones)}")

        for idx, stat in enumerate(acc_stats):
            report_lines.append(
                f"  Накопление {idx+1}: {times[stat['start_idx']]} → {times[stat['end_idx']-1]}, "
                f"средняя цена {stat['avg_price']:.2f}, суммарный объем {stat['sum_volume']:.2f}, "
                f"прогноз конца зоны: {stat['forecast_price']:.2f}"
            )
        for idx, stat in enumerate(dist_stats):
            report_lines.append(
                f"  Распределение {idx+1}: {times[stat['start_idx']]} → {times[stat['end_idx']-1]}, "
                f"средняя цена {stat['avg_price']:.2f}, суммарный объем {stat['sum_volume']:.2f}, "
                f"прогноз конца зоны: {stat['forecast_price']:.2f}"
            )

        # Графики (цена и зоны)
        ax_price = axes[i,0]
        ax_vol = axes[i,1]

        ax_price.plot(times, closes, color='black', label='Цена')

        for stat, color in zip(acc_stats, ['green']*len(acc_stats)):
            start, end = stat['start_idx'], stat['end_idx']
            rect = patches.Rectangle(
                (mdates.date2num(times[start]), min(closes[start:end])),
                mdates.date2num(times[end-1]) - mdates.date2num(times[start]),
                max(closes[start:end]) - min(closes[start:end]),
                facecolor=color, alpha=0.3
            )
            ax_price.add_patch(rect)

            forecast_len = int((end-start) * forecast_multiplier)
            if end + forecast_len < len(times):
                ax_price.plot(
                    times[end:end+forecast_len],
                    [stat['forecast_price']]*forecast_len,
                    linestyle='--', color=color, alpha=0.7
                )

        for stat, color in zip(dist_stats, ['blue']*len(dist_stats)):
            start, end = stat['start_idx'], stat['end_idx']
            rect = patches.Rectangle(
                (mdates.date2num(times[start]), min(closes[start:end])),
                mdates.date2num(times[end-1]) - mdates.date2num(times[start]),
                max(closes[start:end]) - min(closes[start:end]),
                facecolor=color, alpha=0.3
            )
            ax_price.add_patch(rect)

            forecast_len = int((end-start) * forecast_multiplier)
            if end + forecast_len < len(times):
                ax_price.plot(
                    times[end:end+forecast_len],
                    [stat['forecast_price']]*forecast_len,
                    linestyle='--', color=color, alpha=0.7
                )

        ax_price.set_title(f'{tf} — Цена + зоны')
        ax_price.grid(True)
        ax_price.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax_price.legend(loc='upper left')

        width = (mdates.date2num(times[1]) - mdates.date2num(times[0])) * 0.8 if len(times) > 1 else 0.0005
        ax_vol.bar(times, volumes, color='gray', width=width)
        ax_vol.set_title(f'{tf} — Объемы')
        ax_vol.grid(True)
        ax_vol.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

    plt.tight_layout()

    # Сохраняем изображение в буфер
    img_buffer = BytesIO()
    fig.savefig(img_buffer, format='png', dpi=150)
    plt.close(fig)
    img_buffer.seek(0)

    return img_buffer, report_lines, all_zones_data
