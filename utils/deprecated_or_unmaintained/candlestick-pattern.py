import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=Warning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# IMPORTS
import multiprocessing as mp
import os
import pandas as pd
import numpy as np

import time
import math
import os.path

# from tqdm import tnrange, notebook
from tqdm.notebook import tqdm

from datetime import timedelta, datetime
from dateutil import parser

# Import the plotting library
import matplotlib.pyplot as plt
# %matplotlib inline

import matplotlib.dates as mdates
from matplotlib.dates import DateFormatter
from matplotlib.dates import MonthLocator

import seaborn as sns
sns.set()

plt.rcParams.update({'figure.figsize':(15,7), 'figure.dpi':120})
# plt.style.use('ggplot')

# crypto = pd.read_csv('user_data/data/kucoin/BTC_USDT-5m.csv', parse_dates=True)

def cleanPx(prices, freq='1H'):
    prices = prices.iloc[prices.Date.drop_duplicates(keep='last').index]
    prices.Date = pd.to_datetime(prices.Date)
    prices.set_index('Date', inplace=True)

    prices_ohlc = prices[['Open','High','Low','Close']]
    prices_vol = prices[['Volume']]

    prices_ohlc = prices_ohlc.resample(freq).agg({'Open': 'first', 
                                 'High': 'max', 
                                 'Low': 'min', 
                                 'Close': 'last'})
    prices_vol = prices_vol.resample(freq).sum()

    prices = pd.concat([prices_ohlc, prices_vol], axis=1)
    prices.index = prices.index.tz_localize('UTC').tz_convert('Asia/Singapore')

    return prices.dropna()

# Function to save a chunk of DataFrame to CSV
def process_chunk(chunk):
    # print(f"Processing chunk number {chunk_index}")
    chunk.reset_index(inplace=True)
    # print(chunk)
    crypto = cleanPx(chunk, '1H') # change timeframe here
    crypto.reset_index(inplace=True)
    crypto.columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
    crypto.set_index('Date', inplace=True)

    #crypto
    import talib
    candle_names = talib.get_function_groups()['Pattern Recognition']
    removed = ['CDLCOUNTERATTACK', 'CDLLONGLINE', 'CDLSHORTLINE', 
            'CDLSTALLEDPATTERN', 'CDLKICKINGBYLENGTH']
    candle_names = [name for name in candle_names if name not in removed]

    ', '.join(candle_names)

    crypto.reset_index(inplace=True)
    crypto = crypto[['Date', 'Open', 'High', 'Low', 'Close']]
    crypto.columns = ['Date', 'Open', 'High', 'Low', 'Close']

    candle_rankings = {
            "CDL3LINESTRIKE_Bull": 1,
            "CDL3LINESTRIKE_Bear": 2,
            "CDL3BLACKCROWS_Bull": 3,
            "CDL3BLACKCROWS_Bear": 3,
            "CDLEVENINGSTAR_Bull": 4,
            "CDLEVENINGSTAR_Bear": 4,
            "CDLTASUKIGAP_Bull": 5,
            "CDLTASUKIGAP_Bear": 5,
            "CDLINVERTEDHAMMER_Bull": 6,
            "CDLINVERTEDHAMMER_Bear": 6,
            "CDLMATCHINGLOW_Bull": 7,
            "CDLMATCHINGLOW_Bear": 7,
            "CDLABANDONEDBABY_Bull": 8,
            "CDLABANDONEDBABY_Bear": 8,
            "CDLBREAKAWAY_Bull": 10,
            "CDLBREAKAWAY_Bear": 10,
            "CDLMORNINGSTAR_Bull": 12,
            "CDLMORNINGSTAR_Bear": 12,
            "CDLPIERCING_Bull": 13,
            "CDLPIERCING_Bear": 13,
            "CDLSTICKSANDWICH_Bull": 14,
            "CDLSTICKSANDWICH_Bear": 14,
            "CDLTHRUSTING_Bull": 15,
            "CDLTHRUSTING_Bear": 15,
            "CDLINNECK_Bull": 17,
            "CDLINNECK_Bear": 17,
            "CDL3INSIDE_Bull": 20,
            "CDL3INSIDE_Bear": 56,
            "CDLHOMINGPIGEON_Bull": 21,
            "CDLHOMINGPIGEON_Bear": 21,
            "CDLDARKCLOUDCOVER_Bull": 22,
            "CDLDARKCLOUDCOVER_Bear": 22,
            "CDLIDENTICAL3CROWS_Bull": 24,
            "CDLIDENTICAL3CROWS_Bear": 24,
            "CDLMORNINGDOJISTAR_Bull": 25,
            "CDLMORNINGDOJISTAR_Bear": 25,
            "CDLXSIDEGAP3METHODS_Bull": 27,
            "CDLXSIDEGAP3METHODS_Bear": 26,
            "CDLTRISTAR_Bull": 28,
            "CDLTRISTAR_Bear": 76,
            "CDLGAPSIDESIDEWHITE_Bull": 46,
            "CDLGAPSIDESIDEWHITE_Bear": 29,
            "CDLEVENINGDOJISTAR_Bull": 30,
            "CDLEVENINGDOJISTAR_Bear": 30,
            "CDL3WHITESOLDIERS_Bull": 32,
            "CDL3WHITESOLDIERS_Bear": 32,
            "CDLONNECK_Bull": 33,
            "CDLONNECK_Bear": 33,
            "CDL3OUTSIDE_Bull": 34,
            "CDL3OUTSIDE_Bear": 39,
            "CDLRICKSHAWMAN_Bull": 35,
            "CDLRICKSHAWMAN_Bear": 35,
            "CDLSEPARATINGLINES_Bull": 36,
            "CDLSEPARATINGLINES_Bear": 40,
            "CDLLONGLEGGEDDOJI_Bull": 37,
            "CDLLONGLEGGEDDOJI_Bear": 37,
            "CDLHARAMI_Bull": 38,
            "CDLHARAMI_Bear": 72,
            "CDLLADDERBOTTOM_Bull": 41,
            "CDLLADDERBOTTOM_Bear": 41,
            "CDLCLOSINGMARUBOZU_Bull": 70,
            "CDLCLOSINGMARUBOZU_Bear": 43,
            "CDLTAKURI_Bull": 47,
            "CDLTAKURI_Bear": 47,
            "CDLDOJISTAR_Bull": 49,
            "CDLDOJISTAR_Bear": 51,
            "CDLHARAMICROSS_Bull": 50,
            "CDLHARAMICROSS_Bear": 80,
            "CDLADVANCEBLOCK_Bull": 54,
            "CDLADVANCEBLOCK_Bear": 54,
            "CDLSHOOTINGSTAR_Bull": 55,
            "CDLSHOOTINGSTAR_Bear": 55,
            "CDLMARUBOZU_Bull": 71,
            "CDLMARUBOZU_Bear": 57,
            "CDLUNIQUE3RIVER_Bull": 60,
            "CDLUNIQUE3RIVER_Bear": 60,
            "CDL2CROWS_Bull": 61,
            "CDL2CROWS_Bear": 61,
            "CDLBELTHOLD_Bull": 62,
            "CDLBELTHOLD_Bear": 63,
            "CDLHAMMER_Bull": 65,
            "CDLHAMMER_Bear": 65,
            "CDLHIGHWAVE_Bull": 67,
            "CDLHIGHWAVE_Bear": 67,
            "CDLSPINNINGTOP_Bull": 69,
            "CDLSPINNINGTOP_Bear": 73,
            "CDLUPSIDEGAP2CROWS_Bull": 74,
            "CDLUPSIDEGAP2CROWS_Bear": 74,
            "CDLGRAVESTONEDOJI_Bull": 77,
            "CDLGRAVESTONEDOJI_Bear": 77,
            "CDLHIKKAKEMOD_Bull": 82,
            "CDLHIKKAKEMOD_Bear": 81,
            "CDLHIKKAKE_Bull": 85,
            "CDLHIKKAKE_Bear": 83,
            "CDLENGULFING_Bull": 84,
            "CDLENGULFING_Bear": 91,
            "CDLMATHOLD_Bull": 86,
            "CDLMATHOLD_Bear": 86,
            "CDLHANGINGMAN_Bull": 87,
            "CDLHANGINGMAN_Bear": 87,
            "CDLRISEFALL3METHODS_Bull": 94,
            "CDLRISEFALL3METHODS_Bear": 89,
            "CDLKICKING_Bull": 96,
            "CDLKICKING_Bear": 102,
            "CDLDRAGONFLYDOJI_Bull": 98,
            "CDLDRAGONFLYDOJI_Bear": 98,
            "CDLCONCEALBABYSWALL_Bull": 101,
            "CDLCONCEALBABYSWALL_Bear": 101,
            "CDL3STARSINSOUTH_Bull": 103,
            "CDL3STARSINSOUTH_Bear": 103,
            "CDLDOJI_Bull": 104,
            "CDLDOJI_Bear": 104
        }

    # extract OHLC 
    op = crypto['Open']
    hi = crypto['High']
    lo = crypto['Low']
    cl = crypto['Close']

    # create columns for each pattern
    for candle in candle_names:
        # below is same as;
        # df["CDL3LINESTRIKE"] = talib.CDL3LINESTRIKE(op, hi, lo, cl)
        crypto[candle] = getattr(talib, candle)(op, hi, lo, cl)


    from itertools import compress

    crypto['candlestick_pattern'] = np.nan
    crypto['candlestick_match_count'] = np.nan

    for index, row in crypto.iterrows():

        # no pattern found
        if len(row[candle_names]) - sum(row[candle_names] == 0) == 0:
            crypto.loc[index,'candlestick_pattern'] = "NO_PATTERN"
            crypto.loc[index, 'candlestick_match_count'] = 0
        # single pattern found
        elif len(row[candle_names]) - sum(row[candle_names] == 0) == 1:
            # bull pattern 100 or 200
            if any(row[candle_names].values > 0):
                pattern = list(compress(row[candle_names].keys(), row[candle_names].values != 0))[0] + '_Bull'
                crypto.loc[index, 'candlestick_pattern'] = pattern
                crypto.loc[index, 'candlestick_match_count'] = 1
            # bear pattern -100 or -200
            else:
                pattern = list(compress(row[candle_names].keys(), row[candle_names].values != 0))[0] + '_Bear'
                crypto.loc[index, 'candlestick_pattern'] = pattern
                crypto.loc[index, 'candlestick_match_count'] = 1
        # multiple patterns matched -- select best performance
        else:
            # filter out pattern names from bool list of values
            patterns = list(compress(row[candle_names].keys(), row[candle_names].values != 0))
            container = []
            for pattern in patterns:
                if row[pattern] > 0:
                    container.append(pattern + '_Bull')
                else:
                    container.append(pattern + '_Bear')
            rank_list = [candle_rankings[p] for p in container]
            if len(rank_list) == len(container):
                rank_index_best = rank_list.index(min(rank_list))
                crypto.loc[index, 'candlestick_pattern'] = container[rank_index_best]
                crypto.loc[index, 'candlestick_match_count'] = len(container)


    # clean up candle columns
    try:
        crypto.drop(candle_names, axis = 1, inplace = True)
    except:
        pass

    crypto.loc[crypto.candlestick_pattern == 'NO_PATTERN', 'candlestick_pattern'] = ''
    crypto.candlestick_pattern = crypto.candlestick_pattern.apply(lambda x: x[3:])

    # crypto.to_csv(os.path.join(output_folder, f'batch_{chunk_index}.csv'), index=False)
    return crypto   

if __name__ == '__main__':
    # Read the CSV file
    df = pd.read_csv('user_data/data/kucoin/BTC_USDT-5m.csv', parse_dates=True)

    # Output folder
    output_folder = 'user_data/test_output/'
    os.makedirs(output_folder, exist_ok=True)

    # Number of chunks
    num_chunks = 4  # Adjust based on how many chunks you want

    # Split DataFrame into chunks
    chunk_size = len(df) // num_chunks
    chunks = [df.iloc[i:i + chunk_size] for i in range(0, len(df), chunk_size)]     
    
    
    # Create a pool of workers
    # with mp.Pool(processes=num_chunks) as pool:
        # Map the chunks to the save function
    #    pool.starmap(save_chunk, [(chunk, output_folder, i) for i, chunk in enumerate(chunks)])


    with mp.Pool(processes=num_chunks) as pool:
        processed_chunks = pool.map(process_chunk, chunks)

    # Merge processed chunks into a single DataFrame
    merged_df = pd.concat(processed_chunks, ignore_index=True)

    # Save the combined DataFrame to a CSV file
    merged_df.to_csv(os.path.join(output_folder, 'combined_output.csv'), index=False)
