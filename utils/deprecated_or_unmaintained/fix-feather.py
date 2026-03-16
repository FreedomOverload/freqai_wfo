import os
import pyarrow.feather as feather
import pandas as pd
import argparse
import concurrent.futures
import multiprocessing
script_name = os.path.basename(__file__)

def process_file(file_path):
    """Read the Feather file and remove it if corrupted."""
    script_name = os.path.basename(__file__)
    try:
        df = feather.read_feather(file_path)
        # You can add additional processing for df here if needed
    except Exception as e:
        try:
            os.remove(file_path)  # Remove the Feather file
            print(f"{script_name}: removed corrupted: {file_path}")
        except Exception as remove_error:
            print(f"{script_name}: error removing {file_path}: {remove_error}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fix pairlist feather")
    parser.add_argument("exchange", type=str, help="exchange name")
    args = parser.parse_args()
    print(f"{script_name}: exchange is {args.exchange}")
    folder_path = f"././user_data/data/{args.exchange}"

    # Collect all Feather file paths
    file_paths = []
    for dirpath, _, filenames in os.walk(folder_path):
        for file_name in filenames:
            if file_name.endswith(".feather"):  # Check for Feather file extension
                file_paths.append(os.path.join(dirpath, file_name))

    # Use ThreadPoolExecutor to process files in parallel
    with concurrent.futures.ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
        executor.map(process_file, file_paths)