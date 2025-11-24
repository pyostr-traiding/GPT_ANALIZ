import datetime
from conf.settings import settings
from API.ByBit.kline import Klines


def get_klines():
    kline_1 = Klines(
        symbol=settings.SYMBOL,
        interval=1,
        start=int((datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=1000)).timestamp() * 1000),
    )

    klines_15 = Klines(
        symbol=settings.SYMBOL,
        interval=15,
        start=int((datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=15000)).timestamp() * 1000),
    )

    klines_30 = Klines(
        symbol=settings.SYMBOL,
        interval=30,
        start=int((datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=30000)).timestamp() * 1000),
    )

    klines_60 = Klines(
        symbol=settings.SYMBOL,
        interval=60,
        start=int((datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=1000)).timestamp() * 1000),
    )
    return kline_1, klines_15, klines_30, klines_60
