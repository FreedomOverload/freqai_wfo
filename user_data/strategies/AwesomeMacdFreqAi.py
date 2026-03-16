# --- Do not remove these libs ---
from freqtrade.strategy import (  # type: ignore
    timeframe_to_minutes,
    IStrategy,
    BooleanParameter,
    CategoricalParameter,
    DecimalParameter,
    IntParameter,
    informative
)
from freqtrade.enums import TradingMode
import numpy as np  # noqa
import pandas as pd  # noqa
from pandas import DataFrame

import talib.abstract as ta  # type: ignore
import pandas_ta as pandas_ta  # type: ignore
import freqtrade.vendor.qtpylib.indicators as qtpylib  # type: ignore

import os, datetime, random
from freqtrade.optimize.space import Categorical, Dimension, Integer, SKDecimal  # type: ignore
from freqtrade.exchange import timeframe_to_minutes


# Anna Coulling - A Complete Guide to Volume Price Analysis
# --------------------------------------------------------
# General rules:
# - Volume confirms price: healthy trend = price + volume move together
# - Volume precedes price: spikes or drops in vol often warn of reversals/breakouts
# - Always compare volume relative to recent history (not absolute numbers)
#
# Trend analysis:
# - Price ↑ + Vol ↑  -> strong uptrend, valid move
# - Price ↑ + Vol ↓  -> weak uptrend, likely exhaustion
# - Price ↓ + Vol ↑  -> strong selling, bearish conviction
# - Price ↓ + Vol ↓  -> weak decline, possible bounce
#
# Consolidation / ranges:
# - Low vol in range = true indecision
# - High/uneven vol in range = accumulation or distribution (smart money)
#
# Breakouts & extremes:
# - Breakout with high vol = more reliable
# - Breakout with low vol = likely false
# - Very high vol at tops/bottoms = climactic, often reversal point
#
# Pullbacks:
# - Rising vol on pullback = possible trend reversal
# - Falling vol on pullback = trend intact

# James F. Dalton - Mind Over Markets (Market Profile concepts)
# -------------------------------------------------------------
# Core idea:
# - Market = auction process, price moves to find balance between buyers/sellers
# - Volume distribution over time reveals "value areas" where market accepts price
#
# Key concepts:
# - Value Area (VA): ~70% of volume traded, shows fair price range
# - Point of Control (POC): price with highest volume, strongest reference level
# - Initial Balance (IB): first hour’s range, sets tone for the day
#
# Market conditions:
# - Balanced market: bell-curve profile, price oscillates around POC (range trading)
# - Imbalanced market: profile shifts up/down, price trends until new balance found
#
# Trading implications:
# - Acceptance (high vol at level) = strong S/R, market likely to stay there
# - Rejection (low vol, single prints) = weak area, price moves away quickly
# - Break from balance w/ high vol = trend start
# - Return to value area = fade/reversion trade
#
# Summary:
# - Market Profile = structure of auction
# - Volume shows acceptance vs rejection
# - Combine POC, VA, IB with volume to judge if market is trending or ranging


class AwesomeMacdFreqAi(IStrategy):
    def __init__(self, config: dict) -> None:
        super().__init__(config)
        # print(self.config)  # full config dictionary
    
    INTERFACE_VERSION: int = 3
    stoploss = -1
    timeframe = str(os.environ["FT_TIMEFRAME"])
    _target_shifted_candles = int(os.environ["FT_TARGET_SHIFTED_CANDLES"])
    _current_leverage = float(os.environ["FT_LEVERAGE"])
    try:
        _current_model = str(os.environ["FT_MODEL"])
    except:
        _current_model = "CatboostClassifier"

    # ROI table:
    _timeframe_mins = timeframe_to_minutes(timeframe)
    minimal_roi = {
        "0": 1, 
        str(_timeframe_mins * _target_shifted_candles): -1
    }
    
    use_exit_signal = False
    # process_only_new_candles = True  # what is this
    startup_candle_count: int = 400  # what is this
    can_short = True  # default, we'll override per-config in __init__    

    def __init__(self, config: dict) -> None:
        super().__init__(config)          # sets self.config
        tm = self.config.get('trading_mode')

        # tm might be an enum (e.g. TradingMode.SPOT) or a string
        if tm == TradingMode.SPOT or 'spot' in str(tm).lower():
            self.can_short = False
        else:
            self.can_short = True       
    

    def feature_engineering_expand_all(self, dataframe: DataFrame, period: int, metadata: dict, **kwargs) -> DataFrame:
        """
        *Only functional with FreqAI enabled strategies*
        This function will automatically expand the defined features on the config defined
        indicator_periods_candles, include_timeframes, include_shifted_candles, and
        include_corr_pairs. In other words, a single feature defined in this function
        will automatically expand to a total of
        indicator_periods_candles * include_timeframes * include_shifted_candles *
        include_corr_pairs numbers of features added to the model.

        All features must be prepended with % to be recognized by FreqAI internals.

        More details on how these config defined parameters accelerate feature engineering
        in the documentation at:

        https://www.freqtrade.io/en/latest/freqai-parameter-table/#feature-parameters

        https://www.freqtrade.io/en/latest/freqai-feature-engineering/#defining-the-features

        :param dataframe: strategy dataframe which will receive the features
        :param period: period of the indicator - usage example:
        :param metadata: metadata of current pair
        dataframe["%-ema-period"] = ta.EMA(dataframe, timeperiod=period)
        """
        macd_fast = ta.MACD(dataframe, fastperiod=period)
        macd_slow = ta.MACD(dataframe, slowperiod=period)
        dataframe["%-macd-fast"] = macd_fast["macd"]
        dataframe["%-macd-slow"] = macd_slow["macd"]
        if len(dataframe) >= period: 
            dataframe["%-ao-fast"] = qtpylib.awesome_oscillator(dataframe, fast=period)
            dataframe["%-ao-slow"] = qtpylib.awesome_oscillator(dataframe, slow=period)
        else:
            dataframe["%-ao-fast"] = np.nan
            dataframe["%-ao-slow"] = np.nan
        dataframe["%-relative_volume-period"] = (
            dataframe["volume"] / dataframe["volume"].rolling(period).mean()
        )
        
        return dataframe

    def feature_engineering_expand_basic(self, dataframe: DataFrame, metadata: dict, **kwargs) -> DataFrame:
        """
        *Only functional with FreqAI enabled strategies*
        This function will automatically expand the defined features on the config defined
        `include_timeframes`, `include_shifted_candles`, and `include_corr_pairs`.
        In other words, a single feature defined in this function
        will automatically expand to a total of
        `include_timeframes` * `include_shifted_candles` * `include_corr_pairs`
        numbers of features added to the model.

        Features defined here will *not* be automatically duplicated on user defined
        `indicator_periods_candles`

        All features must be prepended with `%` to be recognized by FreqAI internals.

        More details on how these config defined parameters accelerate feature engineering
        in the documentation at:

        https://www.freqtrade.io/en/latest/freqai-parameter-table/#feature-parameters

        https://www.freqtrade.io/en/latest/freqai-feature-engineering/#defining-the-features

        :param dataframe: strategy dataframe which will receive the features
        :param metadata: metadata of current pair
        dataframe["%-pct-change"] = dataframe["close"].pct_change()
        dataframe["%-ema-200"] = ta.EMA(dataframe, timeperiod=200)
        """
        dataframe["%-pct-change"] = dataframe["close"].pct_change()
        dataframe["%-raw_volume"] = dataframe["volume"]
        dataframe["%-raw_price"] = dataframe["close"]
        return dataframe

    def feature_engineering_standard(self, dataframe: DataFrame, metadata: dict, **kwargs) -> DataFrame:
        """
        *Only functional with FreqAI enabled strategies*
        This optional function will be called once with the dataframe of the base timeframe.
        This is the final function to be called, which means that the dataframe entering this
        function will contain all the features and columns created by all other
        freqai_feature_engineering_* functions.

        This function is a good place to do custom exotic feature extractions (e.g. tsfresh).
        This function is a good place for any feature that should not be auto-expanded upon
        (e.g. day of the week).

        All features must be prepended with `%` to be recognized by FreqAI internals.

        More details about feature engineering available:

        https://www.freqtrade.io/en/latest/freqai-feature-engineering

        :param dataframe: strategy dataframe which will receive the features
        :param metadata: metadata of current pair
        usage example: dataframe["%-day_of_week"] = (dataframe["date"].dt.dayofweek + 1) / 7
        """
        # dataframe["%-day_of_year"] = dataframe["date"].dt.dayofyear
        # if 'open_8h' in dataframe.columns:
        #     dataframe["%-funding"] = dataframe['open_8h']
        # else:
        #     dataframe["%-funding"] = np.nan  # Fallback
        
        return dataframe

    def set_freqai_targets(self, dataframe: DataFrame, metadata: dict, **kwargs) -> DataFrame:
        """
        *Only functional with FreqAI enabled strategies*
        Required function to set the targets for the model.
        All targets must be prepended with `&` to be recognized by the FreqAI internals.

        More details about feature engineering available:

        https://www.freqtrade.io/en/latest/freqai-feature-engineering

        :param dataframe: strategy dataframe which will receive the targets
        :param metadata: metadata of current pair
        usage example: dataframe["&-target"] = dataframe["close"].shift(-1) / dataframe["close"]
        """
        if self._current_model in ("LightGBMClassifier","CatboostClassifier"):
            # original: only up & down
            self.freqai.class_names = ["down", "up"]
            dataframe["&s-up_or_down"] = np.where(dataframe["close"].shift(-self._target_shifted_candles) > dataframe["close"], "up", "down")

            # up, down, unsure: targets
            # self.freqai.class_names = ["down", "unsure", "up"]
            # dataframe["future_return"] = (dataframe["close"].shift(-20) - dataframe["close"]) / dataframe["close"]            
            # Apply thresholds
            # up_thresh = 0.01
            # down_thresh = -0.01            
            # dataframe["&s-up_or_down"] = np.select(
            #    [
            #        dataframe["future_return"] > up_thresh,
            #        dataframe["future_return"] < down_thresh
            #    ],
            #    ["up", "down"],
            #    default="unsure"
            # )
            
        elif self._current_model in ("CustomCatboostRegressor","CatboostRegressor"):
            dataframe["&s-close_price"] = dataframe["close"].shift(-self._target_shifted_candles)

        return dataframe

    # @informative('8h', candle_type='funding_rate')
    # def populate_indicators_funding_rate(self, dataframe: DataFrame, metadata: dict) -> DataFrame:        
    #    return dataframe
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:  # noqa: C901      
        # dataframe.to_csv("/freqtrade/user_data/df.csv")
        # print("Saved original dataframe to /freqtrade/user_data/df.csv")
        dataframe = self.freqai.start(dataframe, metadata, self)       
        # --- Step 1: add relative volume (VPA helper) ---
        dataframe['vol_sma'] = dataframe['volume'].rolling(20).mean()
        dataframe['rvol'] = dataframe['volume'] / dataframe['vol_sma']        
        # Optional: add VWAP
        dataframe['vwap'] = (dataframe['close'] * dataframe['volume']).cumsum() / dataframe['volume'].cumsum()
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        long_filter = (
            (dataframe['do_predict'] == 1) &            
            (dataframe['rvol'] > 1.0) &               # volume above average
            (dataframe['close'] > dataframe['vwap'])  # price above VWAP
        )        
        short_filter = (
            (dataframe['do_predict'] == 1) &
            (dataframe['rvol'] > 1.0) &               # volume above average
            (dataframe['close'] < dataframe['vwap'])  # price below VWAP
        )   
        if self._current_model in ("LightGBMClassifier","CatboostClassifier"):
            long_filter = long_filter & (dataframe['&s-up_or_down'] == "up")
            short_filter = short_filter & (dataframe['&s-up_or_down'] == "down")                
        elif self._current_model in ("CustomCatboostRegressor","CatboostRegressor"):
            long_filter = long_filter & (dataframe["&s-close_price"] > dataframe["close"])
            short_filter = short_filter & (dataframe["&s-close_price"] < dataframe["close"])

        # --- Step 3: assign entries with tags ---
        dataframe.loc[long_filter, ["enter_long", "enter_tag"]] = (1, "long_vpa_vwap")
        dataframe.loc[short_filter, ["enter_short", "enter_tag"]] = (1, "short_vpa_vwap")
        
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        
        return dataframe

    def leverage(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_leverage: float,
        max_leverage: float,
        side: str,
        **kwargs,
    ) -> float:
        """
        Customize leverage for each new trade. This method is only called in futures mode.

        :param pair: Pair that's currently analyzed
        :param current_time: datetime object, containing the current datetime
        :param current_rate: Rate, calculated based on pricing settings in exit_pricing.
        :param proposed_leverage: A leverage proposed by the bot.
        :param max_leverage: Max leverage allowed on this pair
        :param entry_long_tag: Optional entry_long_tag (buy_tag) if provided with the buy signal.
        :param side: 'long' or 'short' - indicating the direction of the proposed trade
        :return: A leverage amount, which is between 1.0 and max_leverage.
        """

        return self._current_leverage

    _strategy_info = f"timeframe: {timeframe}, _current_leverage: {_current_leverage}, stoploss: {stoploss}"

    def version(self) -> str:
        
        return self._strategy_info
