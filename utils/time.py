import datetime


def ms_to_dt(ms):
    ms =  ms / 1000
    dt = datetime.datetime.fromtimestamp(ms, datetime.UTC)
    return dt.strftime('%Y-%m-%d %H:%M:%S')

def ms_to_dt_obj(ms: int) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(ms / 1000, datetime.UTC)


def parse_time_str(t: str) -> datetime:
    """Разбираем строку 'timestamp | YYYY-MM-DD HH:MM:SS' → datetime."""
    if "|" in t:
        ts_str, dt_str = t.split("|", 1)
        return datetime.datetime.strptime(dt_str.strip(), "%Y-%m-%d %H:%M:%S")
    else:
        # fallback: если вдруг только timestamp
        return datetime.datetime.fromtimestamp(int(t) / 1000, datetime.UTC)
