from typing import List

from pybit.unified_trading import HTTP

from app.entrypoints.schemas.kline import KlineSchema, CandleSchema
from conf.settings import settings
from utils.time import ms_to_dt


def list_to_schema(
        interval,
        symbol,
        data,
):
    """
    Преобразовать список свечей в список схем
    """
    return [
        KlineSchema(
            topic=f'kline.{interval}.{symbol}',
            symbol=symbol,
            interval=interval,
            data=[
                CandleSchema(
                    start=k[0],
                    end=k[0],
                    interval=interval,
                    open=k[1],
                    close=k[4],
                    high=k[2],
                    low=k[3],
                    volume=k[5],
                    turnover=k[6],
                    confirm=True,
                )
            ],
        )
        for k in reversed(data)
    ]

class _KlinesBase:
    max_length: int
    history: List[KlineSchema]
    interval: int
    start: int
    end: int
    symbol: str
    length: int

    last_kline: CandleSchema

    def __init__(
            self,
            symbol: str,
            interval: int,
            start: int,
            end: int = None,
            max_length: int = 1000,
    ):
        self.max_length = max_length
        self.symbol = symbol
        self.interval = interval
        self.start = start
        self.end = end

        if settings.PRINT_INFO:
            print(f'[{symbol} {interval}] Загрузка актуальных данный')
        self.history = self._get_history(
            symbol=symbol,
            interval=interval,
            start=start,
            end=end,
        )
        if settings.PRINT_INFO:
            print(f'[{symbol} {interval}] История загружена [{len(self.history)} свечей]')
        self.length = len(self.history)
        self.last_kline = self.history[-1].data[0]

    @property
    def start_str(self) -> str:
        """
        Возвращает start в формате: timestamp | дата-время
        """
        dt = ms_to_dt(self.start)
        return f"{self.start} | {dt}"

    @property
    def end_str(self) -> str:
        """
        Возвращает end в формате: timestamp | дата-время
        """
        if self.end is None:
            return self.history[-1].data[0].start_str
        dt = ms_to_dt(self.end)
        return f"{self.end} | {dt}"


    @staticmethod
    def _get_history(
            symbol: str,
            interval: int,
            start: int,
            end: int = None,
            limit: int = 1000,
    ) -> List[KlineSchema]:
        """
        Возвращает список свечей в порядке старая -> новая
        """
        session = HTTP(testnet=settings.TEST_NET)
        response = session.get_kline(
            category=settings.CATEGORY_KLINE,
            symbol=symbol,
            interval=interval,
            start=start,
            end=end,
            limit=limit,
        )

        klines = response.get("result", {}).get("list", [])

        return list_to_schema(
            interval=interval,
            symbol=symbol,
            data=klines
        )

class Klines(_KlinesBase):
    """"""