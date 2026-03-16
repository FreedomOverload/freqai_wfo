from IPython.display import Markdown, display
from ipywidgets import widgets
import json
import asyncio
import glob
import os
import shutil
import zipfile
import pandas as pd
import petname
import psutil
import pyarrow.feather as feather
from datetime import datetime, timedelta
import time
from itertools import product
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter
stop_event = asyncio.Event()
CONFIG_FILE = "notebook_config.json"

def load_config():
    """Loads configuration settings from the JSON file."""
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            if "backtest_timeranges" in config and isinstance(config["backtest_timeranges"], str):
                # Ensure each item is stripped and filter out empty strings
                config["backtest_timeranges"] = [
                    item.strip() for item in config["backtest_timeranges"].split(',') if item.strip()
                ]
            else:
                # If it's not a string (e.g., already a list from a previous save), ensure it's a list of strings
                if not isinstance(config.get("backtest_timeranges"), list):
                    config["backtest_timeranges"] = []
            return config
    except FileNotFoundError:
        return {} # Return an empty dictionary if the file doesn't exist

def save_config(config_data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config_data, f, indent=4) # Use indent for pretty printing

def on_save_clicked(b):
    timeranges_list = [
        item.strip() for item in backtest_timeranges_input.value.split(',') if item.strip()
    ]
    config = {        
        "concurrency": concurrency_input.value,
        "backtest_timeranges": timeranges_list, # Save as list
        "backtest_split_days": backtest_split_days_input.value,
        "download_data": download_data_box.value,
        "test_run_mode": test_run_mode_box.value,
        # meta model
        "meta_model_test_size": meta_model_test_size_input.value,
        # base model        
        "base_model": base_model_input.value,
        "base_model_config": base_model_config_input.value,
        "base_model_test_size": base_model_test_size_input.value,
        "base_model_backtest_period_days": base_model_backtest_period_days_input.value,
        "generate_train_period_days_min": generate_train_period_days_min_input.value,
        "generate_train_period_days_max": generate_train_period_days_max_input.value,
        "generate_train_period_days_step": generate_train_period_days_step_input.value,            
        # strategy options
        "leverage": leverage_input.value,
        "timeframe": timeframe_input.value,
        "target_shifted_candles": target_shifted_candles_input.value
    }
    save_config(config)
    print("✅ Configuration saved successfully!")

async def update_resource_status():
    start_time = time.time()
    cpu_header = widgets.Text(
        value=None,
        layout=widgets.Layout(height="auto",width="auto", flex='1'),
        disabled=True
    )
    mem_header = widgets.Text(
        value=None,
        layout=widgets.Layout(height="auto",width="auto", flex='1'),
        disabled=True
    )
    disk_header = widgets.Text(
        value=None,
        layout=widgets.Layout(height="auto",width="auto", flex='1'),
        disabled=True
    )
    time_header = widgets.Text(
        value=None,
        layout=widgets.Layout(height="auto",width="auto", flex='1'),
        disabled=True
    )
    hbox_resource = widgets.HBox(
        [cpu_header,mem_header,disk_header,time_header],
        layout=widgets.Layout(visibility='visible')
    )

    display(hbox_resource)
    stop_event.clear()
    while not stop_event.is_set():
        mem = psutil.virtual_memory()
        cpu = psutil.cpu_percent()
        disk = psutil.disk_usage('/')
        total_threads = psutil.cpu_count()
        used_threads = total_threads * cpu / 100
    
        used_mem_gb = mem.used / (1024 ** 3)
        total_mem_gb = mem.total / (1024 ** 3)
        
        used_disk_gb = disk.used / (1024 ** 3)
        total_disk_gb = disk.total / (1024 ** 3)

        current_time = time.time()
        elapsed_time = current_time - start_time
        
        cpu_header.value = f"Processor Usage: {used_threads:.1f}/{total_threads} CPUs ({cpu:.0f}%)"
        mem_header.value = f"Memory Usage: {used_mem_gb:.1f}/{total_mem_gb:.1f} GB ({mem.percent:.0f}%)"
        disk_header.value = f"Disk Usage: {used_disk_gb:.1f}/{total_disk_gb:.1f} GB ({disk.percent:.0f}%)"
        time_header.value = f"Elapsed Time: {time.strftime('%H:%M:%S', time.gmtime(elapsed_time))}"
        await asyncio.sleep(1)
    hbox_resource.layout.display = 'none'
    
async def run_command_with_progress(command: str, raise_error: bool = True, clean_after_completed: bool = False):
    def highlight_html(text):
        formatter = HtmlFormatter(full=True, style='default') # You can choose different styles
        highlighted_text = highlight(text, PythonLexer(), formatter)
        return highlighted_text
    
    output_text = widgets.HTML(
        value=highlight_html(command),
        layout=widgets.Layout(height="auto",width="auto", flex='1'),
    )
    hbox = widgets.HBox(
        [output_text],
        layout=widgets.Layout(visibility='visible',height="auto",width="auto", flex='1')
    )
    display(hbox)    
    async def read_stream(stream, prefix, collector):
        while True:
            line = await stream.readline()
            if not line:
                break
            decoded_line = line.decode().strip()
            output_text.value = highlight_html(f"{command}\n{decoded_line}")
            collector.append(decoded_line)

    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout_lines, stderr_lines = [], []

    stdout_task = asyncio.create_task(read_stream(process.stdout,"stdout",stdout_lines))
    stderr_task = asyncio.create_task(read_stream(process.stderr,"stderr",stderr_lines))

    await asyncio.gather(stdout_task, stderr_task, process.wait())
    full_logs = "\n".join(stdout_lines + stderr_lines)
    if process.returncode != 0:
        if raise_error:
            hbox.layout.display = 'none'
            raise RuntimeError(full_logs)
    if clean_after_completed:
        hbox.layout.display = 'none'

    return full_logs

def get_choosen_members(chosen, options):
    if chosen not in options:
        return f"'{chosen}' is not in the options list."
    
    index = options.index(chosen)
    return options[index:index+4]
    
async def download_data(timerange):
    async def run_process_file(file_path):
        try:
            feather.read_feather(file_path)
        except Exception as e:
            os.remove(file_path)
            print(f"Removed bad {file_path}.")

    timeframe_members = get_choosen_members(timeframe_input.value, timeframe_input.options)
    
    docker_command_1 = (
        f"sudo docker compose --file docker/docker-compose.yml --project-directory . run --rm "
        f"freqtrade_freqai download-data "
        f"--timerange {timerange} --config {base_model_config_input.value} "
        f"--timeframe {' '.join(timeframe_members)} "
    )
    # prepend to make sure no holes
    docker_command_2 = (
        f"sudo docker compose --file docker/docker-compose.yml --project-directory . run --rm "
        f"freqtrade_freqai download-data "
        f"--timerange {timerange} --config {base_model_config_input.value} "
        f"--timeframe {' '.join(timeframe_members)} "
        f"--prepend "
    )
    await run_command_with_progress(command=docker_command_1,raise_error=True)
    await run_command_with_progress(command=docker_command_2,raise_error=True)
    
    # Collect all Feather file paths and remove bad files
    feather_folder_path = "././user_data/data/"
    file_paths = []
    for dirpath, _, filenames in os.walk(feather_folder_path):
        for file_name in filenames:
            if file_name.endswith(".feather"): # Check for Feather file extension
                file_paths.append(os.path.join(dirpath, file_name))

    for file_path in file_paths:
        await run_process_file(file_path)

       
def remove_folders(folder_paths):
    for folder_path in folder_paths:
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            shutil.rmtree(folder_path)
    print(f"✅ Removed {folder_paths}.")

async def kill_docker():
    # kill/stop all but don't clean up    
    await run_command_with_progress(
        command="sudo docker ps -q | xargs -r sudo docker kill",
        raise_error=True,
    )
    print("✅ Stopped all containters.")

async def clean_docker():
    await run_command_with_progress(
        command="sudo docker system prune --force",
        raise_error=True
    )
    print("✅ Removed all unused containers.")
    remove_folders(
        ["./user_data/backtest_results", "./user_data/hyperopt_results",
        "./user_data/models", 
        "./user_data/configs/generated", "./user_data/strategies/generated"]
    )

async def run_backtest(progress_bar, train_period_days, backtest_timerange, sem):
    async with sem:
        if progress_bar is not None:
            progress_bar.value += 1
            progress_bar.description = f"⏳ {progress_bar.value}/{progress_bar.max}"
        
        container_name = f"{petname.Generate(2, separator='-')}-{petname.Generate(1)}"
        
        with open(base_model_config_input.value, "r") as file:
            data = json.load(file)
        data["freqai"]["identifier"] = container_name
        data["freqai"]["backtest_period_days"] = base_model_backtest_period_days_input.value
        data["freqai"]["train_period_days"] = train_period_days
        data["freqai"]["data_split_parameters"]["test_size"] = base_model_test_size_input.value
        data["freqai"]["save_backtest_models"] = False
        data["freqai"]["feature_parameters"]["include_timeframes"] = get_choosen_members(timeframe_input.value, timeframe_input.options)
        generated_config_dir = f"user_data/configs/generated/{container_name}"
        os.makedirs(generated_config_dir, exist_ok=True)
        generated_config_json = f"{generated_config_dir}/config.json"
        with open(generated_config_json, "w") as file:
            json.dump(data, file, indent=2)
        # Run Docker
        backtest_results_dir = f"user_data/backtest_results/{container_name}"
        os.makedirs(backtest_results_dir, exist_ok=True)
        docker_command = (
            f"sudo docker --log-level ERROR compose --file docker/docker-compose.yml --project-directory . run "
            f"--env FT_LEVERAGE={leverage_input.value} "
            f"--env FT_MODEL={base_model_input.value} "
            f"--env FT_TIMEFRAME={timeframe_input.value} "
            f"--env FT_TARGET_SHIFTED_CANDLES={target_shifted_candles_input.value} "
            f"--name {container_name} freqtrade_freqai backtesting "
            f"--config {generated_config_json} "
            f"--breakdown month --freqaimodel {base_model_input.value} "
            f"--backtest-directory={backtest_results_dir} "
            f"--export=signals "
            f"--timerange {backtest_timerange} "
        )
        try: 
            await run_command_with_progress(command=docker_command,raise_error=True,clean_after_completed=True)
        except Exception as e:
            return None
        # Extract Results
        zip_files = glob.glob(os.path.join(backtest_results_dir, "backtest-result-*.zip"))
        if not zip_files:
            return None
    
        # Extract first zip
        with zipfile.ZipFile(zip_files[0], "r") as zip_ref:
            zip_ref.extractall(backtest_results_dir)
    
        # Find main JSON (ignore config/meta files)
        json_files = glob.glob(os.path.join(backtest_results_dir, "backtest-result-*.json"))
        main_json_files = [
            f for f in json_files
            if not (f.endswith("_config.json") or f.endswith(".meta.json"))
        ]
        if not main_json_files:
            return None
    
        with open(main_json_files[0], "r") as file:
            json_data = json.load(file)
    
        metadata = {
            "container_name" : container_name,
            "train_period_days": train_period_days,
            "backtest_timerange": backtest_timerange,
            "backtest_period_days": base_model_backtest_period_days_input.value,
            "test_size": base_model_test_size_input.value,
            "timeframe": timeframe_input.value,
            "leverage": leverage_input.value,
            "target_shifted_candles": target_shifted_candles_input.value
        }
    
        strategy_entry = json_data["strategy_comparison"][0]
        enhanced_entry = {**metadata, **strategy_entry}
        df = pd.DataFrame([enhanced_entry])
        # print(df)
    
        return df

async def generate_base_model_results():
    async def run_base_model_backtests(combined_df_filename):        
        def generate_train_period_days(min_val=generate_train_period_days_min_input.value,
                                        max_val=generate_train_period_days_max_input.value,
                                        step=generate_train_period_days_step_input.value):
            return list(range(min_val, max_val + 1, step))
    
        # def generate_backtest_period_days(min_val=generate_backtest_period_days_min_input.value,
        #                                    max_val=generate_backtest_period_days_max_input.value,
        #                                    step=generate_backtest_period_days_step_input.value):
        #    return list(range(min_val, max_val + 1, step))
    
        # def generate_test_sizes(min_val=generate_test_sizes_min_input.value,
        #                        max_val=generate_test_sizes_max_input.value,
        #                        step=generate_test_sizes_step_input.value):
        #    vals = []
        #    current = min_val
        #    while current <= max_val:
        #        vals.append(round(current, 2))
        #        current += step
        #    return vals
    
        # def generate_param_grid():
        #    gen_train_days = generate_train_period_days()
        #    gen_backtest_days = generate_backtest_period_days()
        #    gen_test_sizes = generate_test_sizes()
    
        #    combos = [
        #        {
        #            "backtest_period_days": bd,
        #            "train_period_days": td,
        #            "test_size": ts
        #        }
        #        for bd, td, ts in product(gen_backtest_days, gen_train_days, gen_test_sizes)
        #    ]
        #    return combos   
        
        # param_grid = generate_param_grid()
        train_period_days_grid = generate_train_period_days()
        print(train_period_days_grid)
        
        all_timeranges = [
            item.strip() for item in backtest_timeranges_input.value.split(',') if item.strip()
        ]
        
        daily_ranges = []
        
        for timerange in all_timeranges:
            daily_range = split_timerange_from_string(timerange, period_days=backtest_split_days_input.value)
            daily_ranges = daily_ranges + daily_range

        # print(daily_ranges)
        # --- Create the semaphore ONE time ---
        sem = asyncio.Semaphore(concurrency_input.value)
        progress_bar = widgets.IntProgress(
            value=0,
            min=0,
            max=100,
            description="Running backtests... ",
            bar_style='info',
            style={'description_width': 'auto'},
            layout=widgets.Layout(width='auto',flex='1'),
            description_allow_html=True
        )
        if test_run_mode_box.value:
            train_period_days_grid = train_period_days_grid[:2]
            daily_ranges = daily_ranges[:2]
            print("✅ Limited combinations in Test Run Mode.")
        # Now create all the tasks and pass the semaphore to each one
        tasks = [
            asyncio.create_task(
                run_backtest(progress_bar, train_period_days, timerange, sem)
            )
            for train_period_days in train_period_days_grid
            for timerange in daily_ranges
        ]
        # --- NEW LOGIC: Limit tasks for test run mode ---
        progress_bar.max=len(tasks)
        display(widgets.VBox([progress_bar]))
        try:
            results = await asyncio.gather(*tasks)
        except Exception as e:
            print(f"Exception caught: {e}")
            for task in tasks:
                task.cancel()
            results = await asyncio.gather(*tasks, return_exceptions=True)  # Handle cancellations
        
        stop_event.set()
        successful_results = [r for r in results if isinstance(r, pd.DataFrame)]
        if not successful_results:
            print("No successful backtest results from any runs.")
            
        else:
            combined_df = pd.concat(successful_results, ignore_index=True)
            # Rearrange columns
            combined_df = combined_df[[
                'backtest_timerange','profit_total_abs','train_period_days',
                'backtest_period_days','test_size', 'timeframe', 'leverage', 'target_shifted_candles',
                'container_name','key','trades','profit_mean','profit_mean_pct','profit_total','profit_total_pct',
                'duration_avg','wins','draws','losses','winrate','cagr','expectancy','expectancy_ratio','sortino','sharpe','calmar',
                'sqn','profit_factor','max_drawdown_account','max_drawdown_abs']]
            os.makedirs(os.path.dirname(combined_df_filename), exist_ok=True)
            combined_df = combined_df.sort_values("backtest_timerange")
            combined_df.to_csv(combined_df_filename, index=False)
            
            print("🎉 All backtests completed!")
            print(f"✅ Saved {len(successful_results)} results to {combined_df_filename}.")
    try:
        display(Markdown("**Setting up Docker**"))
        await kill_docker()
        await clean_docker()

        # Pull image
        await run_command_with_progress(
            command="sudo docker compose --file docker/docker-compose.yml --project-directory . pull freqtrade_freqai && sudo docker compose --file docker/docker-compose.yml --project-directory . run --rm freqtrade_freqai --version",
            raise_error=True
        )
        print("✅ Pulled the latest 'freqtrade_freqai' Docker image.")
        
        # Download backtest data
        if download_data_box.value:
            display(Markdown("---"))
            display(Markdown("**Downloading data (2018 to now)**"))            
            await download_data("20180101-")
            text = await run_command_with_progress(
                command=f"sudo docker compose --file docker/docker-compose.yml --project-directory . run --rm freqtrade_freqai list-data --show-timerange --config {base_model_config_input.value} ",
                raise_error=True
            )
            print(f"✅ Downloaded backtest data from 2018:\n{text}")

       
        current_timestamp = datetime.now().strftime("%d%m%Y-%H%M")
        csv_filename = f"./output/wfo-{current_timestamp}.csv"
        display(Markdown("---"))
        display(Markdown("**Generating Base Model Results**"))
        await asyncio.gather(run_base_model_backtests(csv_filename), update_resource_status())        
        return csv_filename
    except asyncio.CancelledError:
        display(Markdown("---"))
        print("⛔ User interrupted.")
    except Exception as e:
        raise # Re-raises the caught exception
    finally:
        stop_event.set()
        await kill_docker()

def split_timerange_from_string(timerange_str, period_days):
    date_format = '%Y%m%d'
    try:
        start_date_str, end_date_str = timerange_str.split('-')
    except ValueError:
        return "Invalid input format. Please use 'YYYYMMDD-YYYYMMDD'."
    
    try:
        start_date = datetime.strptime(start_date_str, date_format).date()
        end_date = datetime.strptime(end_date_str, date_format).date()
    except ValueError:
        return "Invalid date format. Please use 'YYYYMMDD'."

    if start_date > end_date:
        return "Start date cannot be after end date."

    ranges = []
    current_start_date = start_date

    while current_start_date <= end_date:
        current_end_date = current_start_date + timedelta(days=period_days - 1)
        if current_end_date > end_date:
            current_end_date = end_date
        
        ranges.append(f"{current_start_date.strftime(date_format)}-{current_end_date.strftime(date_format)}")
        current_start_date += timedelta(days=period_days)

    return ranges

async def generate_meta_model_results(csv_filename, future_timerange, model_type):
    def generate_train_period_days(min_val=generate_train_period_days_min_input.value,
                                        max_val=generate_train_period_days_max_input.value,
                                        step=generate_train_period_days_step_input.value):
        return list(range(min_val, max_val + 1, step))  
    
    # Feature engineering
    def add_date_features(df: pd.DataFrame, date_col: str) -> pd.DataFrame:
        # --- Trend features ---
        df[f"{date_col}_year"] = df[date_col].dt.year
        df[f"{date_col}_dayofyear"] = df[date_col].dt.dayofyear
    
        # --- Cyclical encodings ---
        # Day of month (normalize by actual number of days in the month)
        days_in_month = df[date_col].dt.days_in_month
        df[f"{date_col}_sin_dom"] = np.sin(2 * np.pi * df[date_col].dt.day / days_in_month)
        df[f"{date_col}_cos_dom"] = np.cos(2 * np.pi * df[date_col].dt.day / days_in_month)
    
        # Month of year
        df[f"{date_col}_sin_month"] = np.sin(2 * np.pi * df[date_col].dt.month / 12)
        df[f"{date_col}_cos_month"] = np.cos(2 * np.pi * df[date_col].dt.month / 12)
    
        # Day of week
        df[f"{date_col}_sin_dow"] = np.sin(2 * np.pi * df[date_col].dt.dayofweek / 7)
        df[f"{date_col}_cos_dow"] = np.cos(2 * np.pi * df[date_col].dt.dayofweek / 7)

        # Drop raw datetime columns (CatBoost cannot handle datetime)
        df = df.drop(columns=[date_col])
        return df

    from catboost import CatBoostRegressor
    from ngboost import NGBRegressor
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_squared_error
    import numpy as np
    
    def train_meta_model(filtered_data):
        # Copy input once to avoid modifying original dataframe
        data = filtered_data.copy()        
        # Parse dates
        data[['start_date', 'end_date']] = data['backtest_timerange'].str.split('-', expand=True)
        data['start_date'] = pd.to_datetime(data['start_date'], format='%Y%m%d')
        data['end_date'] = pd.to_datetime(data['end_date'], format='%Y%m%d')
        data['duration_days'] = (data['end_date'] - data['start_date']).dt.days + 1
        
        X = data[['start_date', 'end_date', 'duration_days', 'train_period_days'
                  # 'profit_total','profit_mean',
                  # 'expectancy_ratio','winrate',
                  # 'sharpe','calmar','sqn','cagr',
                  # 'max_drawdown_account'
                 ]].copy()
        y = data['profit_total_abs']        
        # Apply feature engineering
        X = add_date_features(X, 'start_date')
        X = add_date_features(X, 'end_date')        
        print(f"Total model features: {X.shape[1]}")
        # display(Markdown(X.head(1).to_markdown(index=True)))   
 
        if model_type == "CatBoostRegressor":                
            best_model = CatBoostRegressor(
                     depth=16, learning_rate=0.05, iterations=1000, 
                     verbose=100, random_seed=42
                )
            best_model.fit(X, y)
            print(best_model.get_all_params())
                
        elif model_type == "NGBRegressor":
            best_model = NGBRegressor(
                     learning_rate=0.05, n_estimators=5000, 
                     verbose=100
                )
            best_model.fit(X, y)
            print(best_model)
            
        return best_model
    
    def predict_meta_model(model, target_timerange, train_period_days):        
        # Prepare new data for prediction
        start_date_str, end_date_str = target_timerange.split('-')
        start_date = datetime.strptime(start_date_str, "%Y%m%d")
        end_date = datetime.strptime(end_date_str, "%Y%m%d")
        duration_days = (end_date - start_date).days + 1
    
        new_data = pd.DataFrame({
            'start_date': [start_date],
            'end_date': [end_date],
            'duration_days': [duration_days],
            'train_period_days': train_period_days,
        })
    
        # Apply same feature engineering
        new_data = add_date_features(new_data, 'start_date')
        new_data = add_date_features(new_data, 'end_date')
    
        # Predict using NGBoost
        if model_type == "NGBRegressor":
            dist = model.pred_dist(new_data)
            pred_mean = dist.loc[0]
            pred_std = dist.scale[0]
        else:
            pred_mean = model.predict(new_data)[0]
            pred_std = None
    
        # Result DataFrame
        pred_df = pd.DataFrame({
            'backtest_timerange': [target_timerange],
            'profit_total_abs': [pred_mean],
            'train_period_days': train_period_days,
            'duration_days': [duration_days],
        })
    
        if model_type == "NGBRegressor":
            pred_df['pred_std'] = pred_std
    
        return pred_df

    async def run_meta_model_backtests(dfs):
        # --- Create the semaphore ONE time ---
        sem = asyncio.Semaphore(concurrency_input.value)
        progress_bar = widgets.IntProgress(
            value=0,
            min=0,
            max=100,
            description="Running backtests... ",
            bar_style='info',
            style={'description_width': 'auto'},
            layout=widgets.Layout(width='auto',flex='1'),
            description_allow_html=True
        ) 
            
        tasks = [
            asyncio.create_task(
                run_backtest(
                    progress_bar, 
                    int(round(row["train_period_days"])), row["backtest_timerange"], 
                    sem)
            )
            for index, row in dfs.iterrows()
        ]
        progress_bar.max=len(tasks)
        display(widgets.VBox([progress_bar]))
        try:
            results = await asyncio.gather(*tasks)
        except Exception as e:
            print(f"Exception caught: {e}")
            for task in tasks:
                task.cancel()
            results = await asyncio.gather(*tasks, return_exceptions=True)  # Handle cancellations
        
        stop_event.set()
        successful_results = [r for r in results if isinstance(r, pd.DataFrame)]
        if not successful_results:
            print("No successful backtest results from any runs.")
            return None
        else:
            combined_df = pd.concat(successful_results, ignore_index=True)
            # Rearrange columns
            combined_df = combined_df[[
                'backtest_timerange','profit_total_abs','train_period_days',
                # 'backtest_period_days','test_size',
                'container_name','key','trades','profit_mean','profit_mean_pct','profit_total','profit_total_pct',
                'duration_avg','wins','draws','losses','winrate','cagr','expectancy','expectancy_ratio','sortino','sharpe','calmar',
                'sqn','profit_factor','max_drawdown_account','max_drawdown_abs']]            
            print("🎉 All backtests completed!")
            
            return combined_df    
    
    def show_comparision(df_1,df_2):
        df_1_new = df_1[['backtest_timerange', 'train_period_days', 'profit_total_abs']].rename(columns={
        'profit_total_abs': 'actual_profit_total_abs',
        #'train_period_days': 'original_train_period_days'
        })
        
        df_2_new = df_2[['backtest_timerange', 'train_period_days', 'profit_total_abs']].rename(columns={
            'profit_total_abs': 'predicted_profit_total_abs',
            #'train_period_days': 'predicted_train_period_days'
        })
        df_combined = pd.merge(df_1_new, df_2_new, on=['backtest_timerange','train_period_days'], how='inner')
        display(Markdown(df_combined.to_markdown(index=True)))
        
    try:
        # main
        print(f"Reading dataset from {csv_filename}")
        data = pd.read_csv(csv_filename)
        
        # data = data[data['profit_total_abs'] > 0].copy()
        # only keep best results
        filtered_data = (
            data.sort_values("profit_total_abs", ascending=False)
              # .drop_duplicates(subset=["backtest_timerange"], keep="first")
              .sort_values("backtest_timerange")
              .reset_index(drop=True)
        )
        
        display(Markdown(filtered_data.head(10).to_markdown(index=True)))
        # Train model on filtered_data
        display(Markdown("---"))
        display(Markdown(f"**Training {model_type} Meta Model**"))
        model = train_meta_model(filtered_data)
        print(f"✅ Trained a new meta model based on the current dataset.")
    
        display(Markdown("---"))
        display(Markdown(f"**Predicting using {model_type} Meta Model**"))
        # Prepare predictions for trained data and test/future data
        all_timeranges = [
            item.strip() for item in backtest_timeranges_input.value.split(',') if item.strip()
        ]
        train_period_days_grid = generate_train_period_days()
        # Re-predict Trained data
        
        daily_ranges = []    
        for timerange in all_timeranges:
            daily_range = split_timerange_from_string(timerange, period_days=backtest_split_days_input.value)
            daily_ranges = daily_ranges + daily_range
        
        dfs_trained = pd.DataFrame()    
        for target_timerange in daily_ranges:
            for train_period_days in train_period_days_grid:
                df = predict_meta_model(model, target_timerange, train_period_days)
                dfs_trained = pd.concat([dfs_trained, df], ignore_index=True)
        
        # display(Markdown("---"))
        # display(Markdown(f"**Trained timerange: original vs prediction**"))
        print(f"Actual vs Prediction on Trained Data:")
        show_comparision(filtered_data,dfs_trained)
    
        # Predict Test/Future data
        dfs_future = pd.DataFrame()
        daily_future_ranges = split_timerange_from_string(future_timerange, period_days=generate_train_period_days_max_input.value)
        for target_timerange in daily_future_ranges:
            for train_period_days in train_period_days_grid:
                df = predict_meta_model(model, target_timerange, train_period_days)
                dfs_future = pd.concat([dfs_future, df], ignore_index=True)
        
        # display(Markdown("---"))
        # display(Markdown(dfs_future.to_markdown(index=True)))  
        display(Markdown("---"))
        display(Markdown("**Setting up Docker**"))
        await kill_docker()
        await clean_docker()
        display(Markdown("---"))
        display(Markdown("**Backtesting futures timerange**"))
        # result_trained = await run_meta_model_backtests(dfs_trained)
        result_future = await run_meta_model_backtests(dfs_future)
        print(f"Actual vs Prediction on Future Data:")
        show_comparision(result_future,dfs_future)
        print(f"Detailed Prediction on Future Data:")
        display(Markdown(result_future.to_markdown(index=True)))
    except asyncio.CancelledError:
        display(Markdown("---"))
        print("⛔ User interrupted.")
    except Exception as e:
        raise # Re-raises the caught exception
    finally:
        stop_event.set()
        await kill_docker()

def configure_base_model_parameters():
    display(
        Markdown("---"),
        Markdown("**General**"),        
        widgets.HBox([concurrency_input, download_data_box, test_run_mode_box]),
        backtest_timeranges_input,
        timeframe_input, backtest_split_days_input, leverage_input, target_shifted_candles_input,
        Markdown("---"),
        Markdown("**Base Model (FreqAI)**"),
        widgets.HBox([base_model_config_input,base_model_input]),
        widgets.VBox([base_model_backtest_period_days_input,generate_train_period_days_min_input, generate_train_period_days_max_input,generate_train_period_days_step_input,base_model_test_size_input]),
        Markdown("---"),
        Markdown("**Meta Model**"),
        meta_model_test_size_input, save_button,
    )


# -----------
config = load_config()
base_model_config_input = widgets.Text(
    value=config.get("base_model_config", "user_data/configs/gateio-futures_AwesomeMacdFreqAi.json"),
    description="Base Model Config:",
    style={"description_width": "initial"},
    layout=widgets.Layout(width='auto', flex='1')
)
base_model_input = widgets.Text(
    value=config.get("base_model", "CatboostClassifier"),
    description="Base Model (FreqAI):",
    style={"description_width": "initial"},
    layout=widgets.Layout(width='auto', flex='1')
)

backtest_timeranges_value = ", ".join(config.get("backtest_timeranges", []))
backtest_timeranges_input = widgets.Text(
    value=backtest_timeranges_value,
    description="Walk-Forward Backtest Ranges (comma-separated):",
    placeholder="20210101-20220101, 20230101-20240101",
    style={"description_width": "initial"},
    layout=widgets.Layout(width='auto', flex='1')
)

concurrency_input = widgets.IntSlider(
    value=config.get("concurrency", 2),
    min=1, max=16, step=1,
    description="Concurrency (Workers):",
    style={"description_width": "initial"},
    layout=widgets.Layout(width='auto', flex='1')
)
generate_train_period_days_min_input = widgets.IntSlider(
    value=config.get("generate_train_period_days_min", 1),
    min=1, max=365, step=1,
    description="Train Period Min (days):",
    style={"description_width": "initial"},
    layout=widgets.Layout(width='auto', flex='1')
)
backtest_split_days_input = widgets.IntSlider(
    value=config.get("backtest_split_days", 30),
    min=1, max=365, step=1,
    description="Backtest Split Days:",
    style={"description_width": "initial"},
    layout=widgets.Layout(width='auto', flex='1')
)
generate_train_period_days_max_input = widgets.IntSlider(
    value=config.get("generate_train_period_days_max", 5),
    min=1, max=365, step=1,
    description="Train Period Max (days):",
    style={"description_width": "initial"},
    layout=widgets.Layout(width='auto', flex='1')
)
generate_train_period_days_step_input = widgets.IntSlider(
    value=config.get("generate_train_period_days_step", 1),
    min=1, max=365, step=1,
    description="Train Period Step (days):",
    style={"description_width": "initial"},
    layout=widgets.Layout(width='auto', flex='1')
)
base_model_backtest_period_days_input = widgets.IntSlider(
    value=config.get("base_model_backtest_period_days", 30),
    min=1, max=365, step=1,
    description="Backtest Period (days):",
    style={"description_width": "initial"},
    layout=widgets.Layout(width='auto', flex='1')
)
base_model_test_size_input = widgets.FloatSlider(
    value=config.get("base_model_test_size", 0.3),
    min=0, max=1, step=0.01,
    description="Base Model Test Size:",
    style={"description_width": "initial"},
    layout=widgets.Layout(width='auto', flex='1')
)
leverage_input = widgets.IntSlider(
    value=config.get("leverage", 20),
    min=1, max=20, step=1,
    description="Leverage:",
    style={"description_width": "initial"},
    layout=widgets.Layout(width='auto', flex='1')
)
target_shifted_candles_input = widgets.IntSlider(
    value=config.get("target_shifted_candles", 10),
    min=1, max=100, step=1,
    description="Target Shifted Candles:",
    style={"description_width": "initial"},
    layout=widgets.Layout(width='auto', flex='1')
)
timeframe_input = widgets.Dropdown(
    options=['10s', '1m', '5m', '15m', '30m', '1h', '2h', '4h', '8h', '1d', '7d', '1w'],
    value=config.get("timeframe", '1h'),
    description='Timeframe:',
    disabled=False,
    style={"description_width": "initial"},
    layout=widgets.Layout(width='auto', flex='1')
)
meta_model_test_size_input = widgets.FloatSlider(
    value=config.get("meta_model_test_size", 0.3),
    min=0, max=1, step=0.01,
    description="Meta Model Test Size:",
    style={"description_width": "initial"},
    layout=widgets.Layout(width='auto', flex='1')
)
save_button = widgets.Button(
    description=f"💾 Save Settings to {CONFIG_FILE}",
    button_style='info', # 'primary', 'success', 'info', 'warning', 'danger'
    tooltip="Save current configuration to file",
    layout=widgets.Layout(width="auto", flex='1') # Make it stretch if in a row
)
save_button.on_click(on_save_clicked)
download_data_box = widgets.Checkbox(
    value=config.get("download_data", True),
    description="Download Backtest Data",
    indent=False,
    style={"description_width": "initial"},
    layout=widgets.Layout(width="auto", flex='1') # Make it stretch if in a row
)
test_run_mode_box = widgets.Checkbox(
    value=config.get("test_run_mode", False),
    description="Test Run Mode",
    indent=False,
    style={"description_width": "initial"},
    layout=widgets.Layout(width="auto", flex='1')
)