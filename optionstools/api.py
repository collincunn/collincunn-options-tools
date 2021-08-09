import sys
import requests
import time
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

# api connection details
url = "https://finnhub.io/api/v1/stock/"
apiKey = "token=brgo217rh5r8gtvevvt0"


def to_unix_timestamp(convert_datetime):
    """
    Convert datetime to unix timestamp for API
    """
    return str(int(time.mktime(convert_datetime.timetuple())))


def api_error():
    """
    Print error message and stop running
    """
    print("The API did not return data. Check your API connection or stock symbol.")
    sys.exit()


def stock_options(symbol):
    """
    Lists all available call and put options for a given stock

    Parameters:
    -----------
    symbol : str
        stock symbol

    Returns:
    --------
    options : {'CALL':{days_to_expiration:[strike prices]}, 'PUT':{days_to_expiration:[strike prices]}}
        dictionary of 'CALL' and 'PUT' keys, with dictionary values that contain days to expiration keys
        and lists of strike prices as values
    """
    response = requests.get(url + "option-chain?" + apiKey + "&symbol=" + symbol)

    try:
        res = response.json()['data']
    except:
        api_error()

    options = {'CALL': {}, 'PUT': {}}

    for s in res:
        expiration = (date.fromisoformat(s['expirationDate']) - datetime.now().date()).days
        for opt in s['options']:
            options[opt][expiration] = []
            for details in s['options'][opt]:
                options[opt][expiration].append(details['strike'])

    return options


def continuous_prices(price, days=365, multiplier=4):
    """
    Returns a continuous output of potential call and put options for a given stock

    Parameters:
    -----------
    price : float
        current price of stock option
    days : int
        how many days in the future to provide potential strike prices for
    multiplier : int
        how much to multiply the current price by as an upper bound for potential stock option strike prices

    Returns:
    --------
    options : {'CALL':{days_to_expiration:[strike prices]}, 'PUT':{days_to_expiration:[strike prices]}}
        dictionary of 'CALL' and 'PUT' keys, with dictionary values that contain days to expiration keys
        and lists of strike prices as values
    """
    options_grid = {}
    for day in range(1, days + 1):
        options_grid[day] = [float(strike) for strike in range(0, (price * multiplier) + 1, 5)]

    options = {'CALL': options_grid, 'PUT': options_grid}

    return options


def stock_candles(symbol, date_start, date_end):
    """
    Returns stock candles from API, or stops running if response isn't valid

    Parameters:
    -----------
    symbol : str
        stock symbol
    date_start : datetime
    date_end : datetime

    Returns:
    --------
    response : dict[lists]
        dictionary keys stand for:
        "o": list of open prices,
        "c": list of closing prices,
        "h": list of high prices,
        "l": list of low prices,
        "t": list of timestamps,
        "v": list of volumes,
        "s": status, either "ok" or "no_data"
    """
    response = requests.get(url + "candle?resolution=D&" + apiKey + "&symbol=" + symbol +
                            "&from=" + to_unix_timestamp(date_start) + "&to=" + to_unix_timestamp(date_end))

    no_data = ({'s': 'no_data'}, {'error': 'Symbol not supported.'})

    if response.json() in no_data:
        api_error()
    else:
        return response.json()


def current_price(symbol):
    """
    Returns the most recent closing price

    Parameters:
    -----------
    symbol : str
        stock symbol

    Returns:
    --------
    price : float
        most recent closing price
    """
    today = datetime.now().date()
    yesterday = today - timedelta(days=5)

    api_response = stock_candles(symbol, yesterday, today)

    return round(api_response['c'][-1], 2)


def historical_prices(symbol):
    """
    Lists all closing prices for the last 5 years for a given stock.
    Some candles can be missing.

    Returns:
    --------
    closing_prices : list[tuples]
        list of date, closing price tuples
    """
    today = datetime.now().date()
    five_years_ago = today + relativedelta(years=-5)

    api_response = stock_candles(symbol, five_years_ago, today)

    return [(datetime.utcfromtimestamp(t).date(), c) for t, c in zip(api_response['t'], api_response['c'])]
