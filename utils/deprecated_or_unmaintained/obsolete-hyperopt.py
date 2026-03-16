from datetime import datetime, timedelta
import concurrent.futures
from multiprocessing import Pool
import subprocess
import fileinput
import os
import json
import pandas as pd
import glob
import subprocess
import csv
import re
import sys
import platform
import random
import string
import psutil
import time
cpu_arch = platform.uname().machine
script_path = os.path.abspath(__file__)
script_folder = os.path.dirname(script_path)
freqtrade_workers = 8
docker = False

def get_num_cpu_threads():
    """Get the number of CPU threads (i.e., logical cores) on the system."""
    num_cpu_threads = psutil.cpu_count(logical=True)    
    # Return the number of CPU threads
    return num_cpu_threads

def generate_random_string():
    """Generate a random string of 6 lowercase letters."""
    # Define the set of characters to choose from
    characters = string.ascii_lowercase
    # Generate a random string of 6 characters
    random_string = ''.join(random.choice(characters) for _ in range(6))
    # Return the random string
    return random_string
    
def do_execute(command, output_file):    
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    stdout, stderr = process.communicate()
    output = stdout.decode("utf-8")
    error = stderr.decode("utf-8")
    if output_file:
        # Write the output to a new file
        with open(output_file, "w") as f:
            f.write(error)
            f.write(output)
    
    print(error)
    print(output)

def hyperopt_process(strategy, start_date_str, end_date_str, timeframe):
    hyperopt_period_start_date = datetime.strptime(start_date_str, "%Y%m%d")
    hyperopt_period_end_date = datetime.strptime(end_date_str, "%Y%m%d")
    hyperopt_period_start_date_str = hyperopt_period_start_date.strftime("%Y%m%d")
    hyperopt_period_end_date_str = hyperopt_period_end_date.strftime("%Y%m%d")    

    if docker:
        json_command = "mv user_data/strategies/{}.json temp/hyperopt_json/{}-{}-{}-{}.json".format(strategy, strategy, hyperopt_period_start_date_str, hyperopt_period_end_date_str, timeframe)
        hyperopt_command = "sudo docker compose run --rm freqtrade_hyperopt -c \"freqtrade hyperopt --config user_data/config.json --hyperopt-loss ProfitDrawDownHyperOptLoss --strategy {}  --timerange {}-{} --timeframe {} -e 100 --spaces buy sell --random-state 290194 -j 1 && {}\"".format(strategy, hyperopt_period_start_date_str, hyperopt_period_end_date_str, timeframe, json_command)
    else:
        isolation_folder = "temp/" + generate_random_string()
        isolation_command = "mkdir -p {}/user_data/strategies && cd {} && ln -s ../../../user_data/config.json user_data/config.json && ln -s ../../../user_data/data user_data/data && ln -s ../../../../user_data/strategies/{}.py user_data/strategies/{}.py && ln -s ../../../../user_data/strategies/{}Params.py user_data/strategies/{}Params.py".format(isolation_folder,isolation_folder,strategy,strategy,strategy,strategy)
        json_command = "mv user_data/strategies/{}.json ../../temp/hyperopt_json/{}-{}-{}-{}.json".format(strategy, strategy, hyperopt_period_start_date_str, hyperopt_period_end_date_str, timeframe)
        hyperopt_command = "{} && freqtrade hyperopt --config user_data/config.json --hyperopt-loss ProfitDrawDownHyperOptLoss --strategy {}  --timerange {}-{} --timeframe {} -e 100 --spaces buy sell --random-state 290194 -j 1 && {}".format(isolation_command,strategy, hyperopt_period_start_date_str, hyperopt_period_end_date_str, timeframe, json_command)
        
    print(hyperopt_command)
    do_execute(hyperopt_command, "temp/hyperopt/{}-{}-{}-{}.txt".format(strategy, hyperopt_period_start_date_str, hyperopt_period_end_date_str, timeframe))
    

def do_hyperopt_multi(start_date_str, end_date_str, pattern_days, timeframe, strategy):
    start_date = datetime.strptime(start_date_str, "%Y%m%d")
    end_date = datetime.strptime(end_date_str, "%Y%m%d")
    num_days = (end_date - start_date).days
    num_periods = (num_days // pattern_days) + 1

    print("Timerange is {}-{} ({} days), pattern days is {}, timeframe is {}".format(start_date_str, end_date_str, num_days, pattern_days, timeframe))
    #do_execute("rm -v temp/backtesting/*.txt; rm -v temp/hyperopt/*.txt; rm -v temp/hyperopt_json/*.json", False)

    with concurrent.futures.ThreadPoolExecutor(max_workers=freqtrade_workers) as executor:
        futures = []
        for i in range(num_periods):
            hyperopt_period_start_date = start_date + timedelta(days=(i) * pattern_days)
            hyperopt_period_end_date = start_date + timedelta(days=(i + 1) * pattern_days)
            hyperopt_period_start_date_str = hyperopt_period_start_date.strftime("%Y%m%d")
            hyperopt_period_end_date_str = hyperopt_period_end_date.strftime("%Y%m%d")

            future = executor.submit(hyperopt_process, strategy, hyperopt_period_start_date_str, hyperopt_period_end_date_str, timeframe)
            futures.append(future)

        # Wait for all futures to complete
        for future in concurrent.futures.as_completed(futures):
            future.result()

def backtest_process(strategy, start_date_str, end_date_str, timeframe):
    #do_execute("cp temp/hyperopt_json/{}-{}-{}-{}.json user_data/strategies/{}.json".format(strategy,start_date_str,end_date_str,timeframe,strategy),False)
    if docker:
        backtesting_command="sudo docker compose run --rm freqtrade backtesting --enable-protections --config user_data/config.json --strategy {} --timerange {}-{} --timeframe {} --cache none".format(strategy,start_date_str,end_date_str,timeframe)
    else:
        backtesting_command="freqtrade backtesting --enable-protections --config user_data/config.json --strategy {} --timerange {}-{} --timeframe {} --cache none".format(strategy,start_date_str,end_date_str,timeframe)
        
    print(backtesting_command)
    do_execute(backtesting_command,"temp/backtesting/{}-{}-{}-{}.txt".format(strategy,start_date_str,end_date_str,timeframe))

def do_backtest_multi(start_date_str, end_date_str, pattern_days, timeframe, strategy):
    start_date = datetime.strptime(start_date_str, "%Y%m%d")
    end_date = datetime.strptime(end_date_str, "%Y%m%d")
    num_days = (end_date - start_date).days
    num_periods = (num_days // pattern_days) + 1

    print("Timerange is {}-{} ({} days), pattern days is {}, timeframe is {}".format(start_date_str,end_date_str,num_days,pattern_days,timeframe))
    #do_execute("rm -v temp/backtesting/*.txt",False)    
    with concurrent.futures.ThreadPoolExecutor(max_workers=freqtrade_workers) as executor:
        futures = []
        for i in range(num_periods):
            hyperopt_period_start_date = start_date + timedelta(days=(i)*pattern_days)
            hyperopt_period_end_date = start_date + timedelta(days=(i+1)*pattern_days)
            hyperopt_period_start_date_str = hyperopt_period_start_date.strftime("%Y%m%d")
            hyperopt_period_end_date_str = hyperopt_period_end_date.strftime("%Y%m%d")
            # backtesting_period_start_date = hyperopt_period_start_date + timedelta(days=pattern_days)
            # backtesting_period_end_date = hyperopt_period_end_date + timedelta(days=pattern_days)
            backtesting_period_start_date = hyperopt_period_start_date
            backtesting_period_end_date = hyperopt_period_end_date
            backtesting_period_start_date_str = backtesting_period_start_date.strftime("%Y%m%d")
            backtesting_period_end_date_str = backtesting_period_end_date.strftime("%Y%m%d")


            future = executor.submit(backtest_process, strategy, backtesting_period_start_date_str, backtesting_period_end_date_str, timeframe)
            futures.append(future)

        # Wait for all futures to complete
        for future in concurrent.futures.as_completed(futures):
            future.result()

def do_hyperopt_csv(strategy):
    json_files = glob.glob("temp/hyperopt_json/*.json")
    dataframes = []
    for file in json_files:
        with open(file, "r") as json_file:
            data = json.load(json_file)
        filename = os.path.basename(file)
        date = filename.split("-")[1]
        entry_long_macd = data["params"]["buy"]["entry_long_macd"]
        exit_long_macd = data["params"]["sell"]["exit_long_macd"]
        exit_long_stoploss = data["params"]["sell"]["exit_long_stoploss"]
        entry_short_macd = data["params"]["buy"]["entry_short_macd"]
        exit_short_macd = data["params"]["sell"]["exit_short_macd"]
        exit_short_stoploss = data["params"]["sell"]["exit_short_stoploss"]
        roi = data["params"]["roi"]["0"]
        df = pd.DataFrame({
            "Time": [date],
            "entry_long_macd": [entry_long_macd],
            "exit_long_macd": [exit_long_macd],
            "exit_long_stoploss": [exit_long_stoploss],
            "entry_short_macd": [entry_short_macd],
            "exit_short_macd": [exit_short_macd],
            "exit_short_stoploss": [exit_short_stoploss],
        })
        dataframes.append(df)

    result = pd.concat(dataframes, ignore_index=True)
    result["Time"] = pd.to_datetime(result["Time"], format="%Y%m%d")
    result.sort_values("Time").to_csv("combined.csv", index=False)

    # Generate new combined.txt
    do_execute("cd temp/hyperopt ; grep 'Total profit' *.txt | awk '{print $1,$18}'", "combined.txt")

    # Put profit to csv
    with open("combined.txt", "r") as f:
        lines = f.readlines()

    profit_values = [float(re.search(r"(-?\d+\.\d+)%", line).group(1)) / 100 for line in lines]
    df = pd.read_csv("combined.csv")
    df["actual_profit"] = profit_values
    df.to_csv("combined.csv", index=False)

    # save list of strategies
    df = pd.read_csv("combined.csv")

    # Drop unnecessary columns
    df = df.drop('Time', axis=1)
    df = df.drop('actual_profit', axis=1)

    # Identify duplicated rows that appear at least 5 times
    duplicated_counts = df[df.duplicated(keep=False)].groupby(list(df.columns)).size()
    duplicated_at_least_5_times = duplicated_counts[duplicated_counts >= 5].reset_index().drop(0, axis=1)

    # Print duplicated rows that appear at least 5 times
    print(duplicated_at_least_5_times)

    # Initialize lists for strategies
    long_strategies = []
    short_strategies = []

    # Iterate over the rows that are duplicated at least 5 times
    for _, row in duplicated_at_least_5_times.iterrows():
        long_strategy = {
            'entry_long_macd': row['entry_long_macd'],
            'exit_long_macd': row['exit_long_macd'],
            'exit_long_stoploss': row['exit_long_stoploss']
        }
        long_strategies.append(long_strategy)

        short_strategy = {
            'entry_short_macd': row['entry_short_macd'],
            'exit_short_macd': row['exit_short_macd'],
            'exit_short_stoploss': row['exit_short_stoploss']
        }
        short_strategies.append(short_strategy)

    # Print the results
    print("long_strategies = [")
    for strategy in long_strategies:
        print("    {},".format(strategy))
    print("]")

    print("short_strategies = [")
    for strategy in short_strategies:
        print("    {},".format(strategy))
    print("]")
    
    # Convert the variable to a JSON-formatted string
    long_strategies_json = json.dumps(long_strategies)
    short_strategies_json = json.dumps(short_strategies)

    # Write the string to a file
    with open("user_data/strategies/{}Long.json".format(strategy), 'w') as file:
        file.write(long_strategies_json)
    with open("user_data/strategies/{}Short.json".format(strategy), 'w') as file:
        file.write(short_strategies_json)

def main_backtest(strategy,duration):
    # Backtest
    global freqtrade_workers
    freqtrade_workers = get_num_cpu_threads() / 2
    print("Backtesting with {} CPU threads...".format(freqtrade_workers))
    final_strategy = strategy + "Final"
    if duration == "Full":
        do_backtest_multi(start_date_str="20230101",end_date_str="20240401",pattern_days=465,timeframe="5m",strategy=final_strategy)
    else:
        do_backtest_multi(start_date_str="20230101",end_date_str="20230130",pattern_days=30,timeframe="5m",strategy=final_strategy)
    
def main_hyperopt(strategy,duration):
    # Hyperopt
    global freqtrade_workers
    freqtrade_workers = 10
    print("Hyperopt with {} CPU threads...".format(freqtrade_workers))
    if duration == "Full":
        do_hyperopt_multi(start_date_str="20230101",end_date_str="20240401",pattern_days=1,timeframe="5m",strategy=strategy)
    else:
        do_hyperopt_multi(start_date_str="20230101",end_date_str="20230130",pattern_days=1,timeframe="5m",strategy=strategy)
    
def main_hyperopt_benchmark(strategy):
    global freqtrade_workers
    # Hyperopt Single-Threaded
    freqtrade_workers = 1
    print("Benchmarking Hyperopt with {} CPU threads...".format(freqtrade_workers))
    start_time = time.time()
    do_hyperopt_multi(start_date_str="20230101",end_date_str="20230102",pattern_days=1,timeframe="5m",strategy=strategy)
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f'Hyperopt Single-Threaded Benchmark finished in  {elapsed_time:.3f} seconds')
    
    # Hyperopt Multi-Threaded    
    # freqtrade_workers = get_num_cpu_threads() - 1
    # print("Benchmarking Hyperopt with {} CPU threads...".format(freqtrade_workers))
    # start_time = time.time()
    # do_hyperopt_multi(start_date_str="20230101",end_date_str="20230116",pattern_days=1,timeframe="5m",strategy="DA01Strategy")
    # end_time = time.time()
    # elapsed_time = end_time - start_time
    # print(f'Hyperopt Multi-Threaded Benchmark finished in  {elapsed_time:.3f} seconds')

def main_startup():
    
    if docker:
        print("Cleaning up docker containers...")
        do_execute("sudo docker rm -f $(sudo docker ps -a -q --filter name=freqtrade)",False)
        print("Downloading market data...")
        do_execute("sudo docker compose run --rm freqtrade download-data --config user_data/config.json --timeframe 5m 15m 1h --timerange 20230101-20240401",False)
    else:
        print("Cleaning up isolation folders...")
        do_execute("killall -r freqtrade$; rm -r temp",False)
        print("Downloading market data...")
        do_execute("freqtrade download-data --config user_data/config.json --timeframe 5m 15m 1h --timerange 20230101-20240401",False)
    # prepare folders
    do_execute("mkdir -p temp/hyperopt_json",False)
    do_execute("mkdir -p temp/hyperopt",False)
    do_execute("mkdir -p temp/backtesting",False)

if __name__ == "__main__":    
    main_startup()
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    if arg == "backtest":        
        main_backtest("DA01Strategy","Full")
    elif arg == "hyperopt":
        main_hyperopt("DA01Strategy","Full")
        do_hyperopt_csv("DA01Strategy")
        main_backtest("DA01Strategy","Full")
    elif arg == "hyperopt_benchmark":
        main_hyperopt_benchmark("DA01Strategy")
    elif arg == "hyperopt_csv":
        do_hyperopt_csv("DA01Strategy")
    else:
        print("Invalid argument. Use 'backtest','hyperopt', 'hyperopt_csv' or 'hyperopt_benchmark'")    

    # Specify the class name of the hyperopt loss function
    # Hyperopt-loss-functions are:
    # ShortTradeDurHyperOptLoss, OnlyProfitHyperOptLoss,
    # SharpeHyperOptLoss, SharpeHyperOptLossDaily,
    # SortinoHyperOptLoss, SortinoHyperOptLossDaily,
    # CalmarHyperOptLoss, MaxDrawDownHyperOptLoss,
    # MaxDrawDownRelativeHyperOptLoss,
    # ProfitDrawDownHyperOptLoss
