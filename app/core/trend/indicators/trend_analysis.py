import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.cluster import KMeans
from scipy.signal import argrelextrema
from API.ByBit.kline import Klines


def analyze_market_current_trend(
        klines: 'Klines',
        window_size: int = 40,
        n_clusters: int = 3,
        slope_threshold: float = 0.5
):
    """
    Определяем текущий тренд по последнему окну свечей.
    Плюс кластеризация истории через KMeans.
    """
    closes = np.array([float(candle.close) for k in klines.history for candle in k.data])
    highs = np.array([float(candle.high) for k in klines.history for candle in k.data])
    lows = np.array([float(candle.low) for k in klines.history for candle in k.data])

    # --- Формирование фичей для кластеризации ---
    features = []
    for start in range(len(closes) - window_size + 1):
        end = start + window_size
        c_window = closes[start:end]
        h_window = highs[start:end]
        l_window = lows[start:end]
        t = np.arange(window_size).reshape(-1, 1)

        lr = LinearRegression().fit(t, c_window)
        slope = lr.coef_[0]
        r2 = lr.score(t, c_window)

        tr = np.maximum(h_window[1:] - l_window[1:],
                        np.maximum(np.abs(h_window[1:] - c_window[:-1]),
                                   np.abs(l_window[1:] - c_window[:-1])))
        atr = np.mean(tr)
        features.append([slope, r2, atr])
    features = np.array(features)

    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    kmeans.fit(features)

    # --- Последнее окно ---
    last_close = closes[-window_size:]
    last_high = highs[-window_size:]
    last_low = lows[-window_size:]

    t_last = np.arange(window_size).reshape(-1, 1)
    lr_last = LinearRegression().fit(t_last, last_close)
    slope_last = lr_last.coef_[0]
    r2_last = lr_last.score(t_last, last_close)

    tr_last = np.maximum(last_high[1:] - last_low[1:],
                         np.maximum(np.abs(last_high[1:] - last_close[:-1]),
                                    np.abs(last_low[1:] - last_close[:-1])))
    atr_last = np.mean(tr_last)

    # --- Определение тренда ---
    if slope_last > slope_threshold:
        trend = 'bull'
    elif slope_last < -slope_threshold:
        trend = 'bear'
    else:
        trend = 'side'

    # --- Локальные экстремумы для уровня разворота ---
    local_max_idx = argrelextrema(last_close, np.greater)[0]
    local_min_idx = argrelextrema(last_close, np.less)[0]

    if trend == "bull":
        reversal_level = last_close[local_min_idx[-1]] - atr_last if len(local_min_idx) > 0 else last_close[-1] - atr_last
    elif trend == "bear":
        reversal_level = last_close[local_max_idx[-1]] + atr_last if len(local_max_idx) > 0 else last_close[-1] + atr_last
    else:
        if len(local_max_idx) > 0 and len(local_min_idx) > 0:
            nearest_extreme = last_close[local_max_idx[-1]] if abs(last_close[-1] - last_close[local_max_idx[-1]]) < abs(last_close[-1] - last_close[local_min_idx[-1]]) else last_close[local_min_idx[-1]]
            reversal_level = nearest_extreme
        else:
            reversal_level = last_close[-1]

    return {
        "trend": trend,
        "strength": r2_last,
        "slope": slope_last,
        "atr": atr_last,
        "reversal_level": reversal_level,
    }


def analyze_market(klines: 'Klines', window_size: int = 40, n_clusters: int = 3):
    """
    Анализ рынка с кластеризацией и уровнем разворота.
    """
    closes = np.array([float(candle.close) for k in klines.history for candle in k.data])
    highs = np.array([float(candle.high) for k in klines.history for candle in k.data])
    lows = np.array([float(candle.low) for k in klines.history for candle in k.data])

    features = []
    for start in range(len(closes) - window_size + 1):
        end = start + window_size
        c_window = closes[start:end]
        h_window = highs[start:end]
        l_window = lows[start:end]
        t = np.arange(window_size).reshape(-1, 1)

        lr = LinearRegression().fit(t, c_window)
        slope = lr.coef_[0]
        r2 = lr.score(t, c_window)

        tr = np.maximum(h_window[1:] - l_window[1:],
                        np.maximum(np.abs(h_window[1:] - c_window[:-1]),
                                   np.abs(l_window[1:] - c_window[:-1])))
        atr = np.mean(tr)

        features.append([slope, r2, atr])

    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    kmeans.fit(np.array(features))
    labels = kmeans.labels_

    last_cluster = labels[-1]
    cluster_centers = kmeans.cluster_centers_
    sorted_clusters = np.argsort(cluster_centers[:, 0])
    if last_cluster == sorted_clusters[-1]:
        trend = "bull"
    elif last_cluster == sorted_clusters[0]:
        trend = "bear"
    else:
        trend = "side"

    # --- Последнее окно ---
    last_close = closes[-window_size:]
    last_high = highs[-window_size:]
    last_low = lows[-window_size:]

    lr_last = LinearRegression().fit(np.arange(window_size).reshape(-1, 1), last_close)
    slope_last = lr_last.coef_[0]

    tr_last = np.maximum(last_high[1:] - last_low[1:],
                         np.maximum(np.abs(last_high[1:] - last_close[:-1]),
                                    np.abs(last_low[1:] - last_close[:-1])))
    atr_last = np.mean(tr_last)

    # --- Локальные экстремумы ---
    local_max_idx = argrelextrema(last_close, np.greater)[0]
    local_min_idx = argrelextrema(last_close, np.less)[0]

    if trend == "bull":
        reversal_level = last_close[local_min_idx[-1]] - atr_last if len(local_min_idx) > 0 else last_close[-1] - atr_last
    elif trend == "bear":
        reversal_level = last_close[local_max_idx[-1]] + atr_last if len(local_max_idx) > 0 else last_close[-1] + atr_last
    else:
        if len(local_max_idx) > 0 and len(local_min_idx) > 0:
            nearest_extreme = last_close[local_max_idx[-1]] if abs(last_close[-1] - last_close[local_max_idx[-1]]) < abs(last_close[-1] - last_close[local_min_idx[-1]]) else last_close[local_min_idx[-1]]
            reversal_level = nearest_extreme
        else:
            reversal_level = last_close[-1]

    return {
        "trend": trend,
        "strength": lr_last.score(np.arange(window_size).reshape(-1, 1), last_close),
        "slope": slope_last,
        "atr": atr_last,
        "reversal_level": reversal_level
    }
