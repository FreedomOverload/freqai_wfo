import json
import os
import shutil
import commentjson
import argparse
script_name = os.path.basename(__file__)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare pairlist from JSON for bash script (main_backtest.sh)")
    parser.add_argument("json", type=str, help="pairlit JSON name without .json")
    args = parser.parse_args()
    # print(f"{script_name}: json is {args.json}")

    # Configuration
    input_file = f"././user_data/configs_pairlist/unsafe/{args.json}.json"
    
    # Read the JSON file
    with open(input_file, "r") as file:
        data = commentjson.load(file)

    pair_whitelist = data["exchange"]["pair_whitelist"]

    # print(pair_whitelist)
    # Prepare the array for Bash
    pair_whitelist_for_bash = 'pair_whitelist=("' + '" "'.join(pair_whitelist) + '")'

    # Print the Bash array definition
    print(pair_whitelist_for_bash)
