import sys
import optionstools.api as api
import optionstools.cli as cli
import pandas as pd

def historical_vol(symbol):
    """
    calculate annualized historical volatility of a stock ticker
    
    Parameters:
    -----------
    symbol: string
        stock ticker
    
    Returns:
    --------
    annualized volatility : double
    
    """
    prices = pd.DataFrame(api.historical_prices(symbol)).iloc[:,1]
    
    returns = prices.ffill().pct_change()
    
    vol = returns.std(axis=0, skipna=True)
    print(vol)
    return vol*(252**(1/2))
