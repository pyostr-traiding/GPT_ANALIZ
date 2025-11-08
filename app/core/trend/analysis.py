import numpy as np


def combine_multitimeframe_analysis(analyses: list, weights: list = None):
    """
    Объединяет анализ нескольких таймфреймов в один финальный сигнал.
    """
    n = len(analyses)
    if weights is None:
        weights = [1] * n

    trend_scores = {'bull': 0, 'bear': 0, 'side': 0}
    for analysis, w in zip(analyses, weights):
        trend_scores[analysis['trend']] += w
    combined_trend = max(trend_scores, key=trend_scores.get)

    combined_strength = np.average([a['strength'] for a in analyses], weights=weights)

    reversal_levels = [a['reversal_level'] for a in analyses]
    if combined_trend == 'bull':
        combined_reversal = min(reversal_levels)
    elif combined_trend == 'bear':
        combined_reversal = max(reversal_levels)
    else:
        combined_reversal = np.average(reversal_levels, weights=weights)

    return {
        "trend": combined_trend,
        "strength": combined_strength,
        "reversal_level": combined_reversal
    }


def simplify_klines(klines, max_len=50):
    shortened = klines.history[-max_len:]
    simplified = [
        {
            "time": k.data[0].start_str,
            "open": k.data[0].open,
            "high": k.data[0].high,
            "low": k.data[0].low,
            "close": k.data[0].close,
            "volume": k.data[0].volume,
        }
        for k in shortened
    ]
    return simplified
