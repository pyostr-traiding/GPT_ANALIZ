import io
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import argrelextrema


def plot_market_analysis(klines, analysis: dict, window_size: int = 40):
    """
    Визуализация тренда, уровня разворота и экстремумов.
    """
    closes = np.array([float(candle.close) for k in klines.history for candle in k.data])
    last_close = closes[-window_size:]
    x = np.arange(len(last_close))

    slope = analysis['slope']
    intercept = last_close[0]
    trend_line = intercept + slope * x
    reversal = np.full_like(x, analysis['reversal_level'])

    local_max_idx = argrelextrema(last_close, np.greater)[0]
    local_min_idx = argrelextrema(last_close, np.less)[0]

    plt.figure(figsize=(12, 6))
    plt.plot(x, last_close, label='Закрытие', marker='o')
    plt.plot(x, trend_line, label='Линия тренда', color='orange')
    plt.plot(x, reversal, label='Разворот', color='red', linestyle='--')
    plt.fill_between(x, trend_line - analysis['atr'], trend_line + analysis['atr'],
                     color='orange', alpha=0.1, label='Диапазон ATR')

    plt.scatter(local_max_idx, last_close[local_max_idx], color='green', marker='^', s=100)
    plt.scatter(local_min_idx, last_close[local_min_idx], color='blue', marker='v', s=100)

    plt.title(f"Анализ тренда: {analysis['trend']}, Сила={analysis['strength']:.2f}")
    plt.grid(True)
    plt.show()


def plot_single_axis(ax, closes, analysis, window_size=40):
    """
    Отрисовка одного графика на переданном ax.
    """
    last_close = closes[-window_size:]
    x = np.arange(len(last_close))

    slope = analysis['slope']
    intercept = last_close[0]
    trend_line = intercept + slope * x
    reversal = np.full_like(x, analysis['reversal_level'])

    local_max_idx = argrelextrema(last_close, np.greater)[0]
    local_min_idx = argrelextrema(last_close, np.less)[0]

    line_close, = ax.plot(x, last_close, label='Закрытие', marker='o')
    line_trend, = ax.plot(x, trend_line, label='Линия тренда', color='orange')
    line_reversal, = ax.plot(x, reversal, label='Разворот', color='red', linestyle='--')
    ax.fill_between(x, trend_line - analysis['atr'], trend_line + analysis['atr'],
                    color='orange', alpha=0.1, label='Диапазон ATR')

    ax.scatter(local_max_idx, last_close[local_max_idx], color='green', marker='^', s=80)
    ax.scatter(local_min_idx, last_close[local_min_idx], color='blue', marker='v', s=80)

    ax.set_title(f"Тренд: {analysis['trend']}, Сила={analysis['strength']:.2f}")
    ax.grid(True)

    return [line_close, line_trend, line_reversal]


def plot_analysis(data: dict, window_size: int = 40) -> [io.BytesIO, dict]:
    """
    Построение 4 графиков + общая легенда.
    """
    timeframes = ["1m", "15m", "30m", "60m"]
    fig, axes = plt.subplots(4, 1, figsize=(14, 12), sharex=False)

    handles = []
    labels = []

    for i, tf in enumerate(timeframes):
        tf_data = data["timeframes"][tf]
        closes = np.array([float(k["close"]) for k in tf_data["klines"]])
        analysis = tf_data["analysis"]

        h = plot_single_axis(axes[i], closes, analysis, window_size)
        axes[i].set_ylabel(tf)

        if not handles:
            handles = h
            labels = [obj.get_label() for obj in h]

    fig.legend(handles, labels, loc='upper center', ncol=4, frameon=False)
    fig.text(0.5, 0.01,
             "ATR — средний диапазон свечей (волатильность).\n"
             "Сила тренда — R² линии регрессии (0-1).",
             ha='center', fontsize=10, bbox=dict(facecolor='white', alpha=0.8))

    plt.tight_layout(rect=[0, 0.05, 1, 0.95])

    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    return buf, data
