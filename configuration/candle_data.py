from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd


def search_kite_symbol(kite, exchange, symbol):
    try:
        instrument = f"{exchange.upper()}:{symbol.upper()}"
        data = kite.ltp(instrument)
        if instrument in data:
            return data[instrument]["instrument_token"]
    except Exception as e:
        print(f"Search failed for {symbol}: {e}")
    return None


def interval_minutes(timeframe):
    if timeframe == "minute":
        return 1
    if timeframe.endswith("minute"):
        return int(timeframe.replace("minute", ""))
    if timeframe == "day":
        return 24 * 60
    raise ValueError(f"Unsupported timeframe: {timeframe}")


def last_closed_candle_time(timeframe):
    now = datetime.now(ZoneInfo("Asia/Kolkata")).replace(second=0, microsecond=0)
    interval = interval_minutes(timeframe)
    midnight = now.replace(hour=0, minute=0)
    elapsed_minutes = int((now - midnight).total_seconds() // 60)
    bucket = (elapsed_minutes // interval) * interval
    return midnight + timedelta(minutes=bucket)


def fetch_symbol_candles(kite, token, days, timeframe):
    to_date   = last_closed_candle_time(timeframe)
    from_date = to_date - timedelta(days=days)
    rows = []

    while True:
        if from_date.date() >= (datetime.now().date() - timedelta(days=100)):
            chunk = kite.historical_data(token, from_date, datetime.now(), timeframe)
            if chunk:
                rows.extend(chunk)
            break
        current_to = from_date + timedelta(days=100)
        chunk = kite.historical_data(token, from_date, current_to, timeframe)
        if chunk:
            rows.extend(chunk)
        from_date = current_to

    return rows

def calculate_candle_color(df):
    if df.empty: return df
    df["candle_color"] = "DOJI"
    df.loc[df["close"] > df["open"], "candle_color"] = "GREEN"
    df.loc[df["close"] < df["open"], "candle_color"] = "RED"
    return df


def build_symbol_dataframe(records):
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"], utc=True).dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
    df = df.sort_values("date").drop_duplicates(subset=["date"], keep="last")
    df = calculate_candle_color(df)
    return df


def update_symbol_dataframe_cache(cache, symbol, df, rows=200):
    if df.empty:
        return cache.get(symbol, pd.DataFrame())
    if symbol in cache and not cache[symbol].empty:
        merged = pd.concat([cache[symbol], df], ignore_index=True)
        merged = merged.drop_duplicates(subset=["date"], keep="last").sort_values("date").reset_index(drop=True)
        cache[symbol] = merged.tail(rows)
    else:
        cache[symbol] = df.tail(rows).reset_index(drop=True)
    return cache[symbol]

def get_smart_sleep_seconds(timeframe, buffer_sec=3):
    """Calculate seconds to sleep until the current candle closes, using IST timezone."""
    # Market operates in IST
    ist = ZoneInfo("Asia/Kolkata")
    now = datetime.now(ist)
    
    interval = interval_minutes(timeframe)
    
    # Total minutes from beginning of day in IST
    minutes_now = now.hour * 60 + now.minute
    
    # In Indian market, candles are usually synced to 00:00 (e.g. 09:15, 09:20 for 5m)
    # minutes_now % interval gives how many minutes passed in the CURRENT candle
    minutes_into_candle = minutes_now % interval
    seconds_now = now.second
    
    total_sec_into_candle = (minutes_into_candle * 60) + seconds_now
    total_sec_in_interval = interval * 60
    
    remaining = total_sec_in_interval - total_sec_into_candle
    
    # Safety: If we are exactly at the boundary, wait for the full next interval
    if remaining <= 0:
        remaining = total_sec_in_interval
        
    # We add a buffer to ensure the broker has finalized the candle data
    return int(remaining + buffer_sec)
