import pandas as pd
pd.set_option('display.float_format', '{:.6f}'.format)


def read_feather(file_path):
    
    df = pd.read_feather(file_path)
    print(df)

pair = "DOGS_USDT_USDT"

exchange = "gateio"
pair_funding_rate = f"user_data/data/{exchange}/futures/{pair}-8h-funding_rate.feather"
pair_futures = f"user_data/data/{exchange}/futures/{pair}-5m-futures.feather"

read_feather(pair_funding_rate)
read_feather(pair_futures)