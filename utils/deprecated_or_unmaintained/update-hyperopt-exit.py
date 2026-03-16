import re
import os
import json
import argparse
script_name = os.path.basename(__file__)

def extract_pairs_and_params(filename):
    pairlist = []
    with open(filename, 'r') as file:
        content = file.read()
        
        # Regex to find pairs
        pairs = re.findall(r"Using pairs \['(.+?)'\]", content)
        print(pairs)
        # Regex to find sell parameters
        sell_params_matches = re.findall(r"# Sell hyperspace params:\s*sell_params = {\s*(.+?)\s*}", content, re.DOTALL)
        
        for pair, params in zip(pairs, sell_params_matches):
            # Extracting parameters
            
            blind_exit_mins = int(re.search(r'"blind_exit_mins": (\d+)', params).group(1))
            negative_profit_magic = float(re.search(r'"negative_profit_magic": ([\-0-9.]+)', params).group(1))
            positive_profit_magic = float(re.search(r'"positive_profit_magic": ([\-0-9.]+)', params).group(1))
            
            # Append to pairlist
            pairlist.append({
                "name": pair,
                "blind_exit_mins": blind_exit_mins,
                "negative_profit_magic": negative_profit_magic,
                "positive_profit_magic": positive_profit_magic
            })
    
    return pairlist

def write_to_config(pairlist, filename):
    with open(filename, 'w') as file:
        file.write("# Auto-generated configuration file\n")
        file.write("hyperopt_pairlist = ")
        file.write(json.dumps(pairlist, indent=4))
        file.write("\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update cuty_exit with hyperopts param")
    parser.add_argument("hyperopt_logs_file", type=str, help="hyperopt_logs_file full_path")
    args = parser.parse_args()

    hyperopt_pairlist = extract_pairs_and_params(args.hyperopt_logs_file)
    write_to_config(hyperopt_pairlist,"user_data/strategies/hyperopt_exit_config.py")
