import re
import os
import commentjson
import argparse
from prettytable import PrettyTable
script_name = os.path.basename(__file__)

# python3 ./tools/update-pairlist.py user_data/backtest_logs/pairlist-backtest-static-gateio-futures-usdt/NFIx5-hyperopt-20180101-20241211.txt

def get_json_name(file_path):
    # file_name = os.path.splitext(os.path.basename(file_path))[0]
    # stripped_name = file_name.rsplit('_', 1)[0]
    stripped_name = os.path.basename(os.path.dirname(file_path))
    return stripped_name

def get_table_output_name(file_path):
    file_name, file_extension = os.path.splitext(file_path)
    bad_pair_output_txt = f"{file_name}_bad_pairs.txt"
    good_pair_output_txt = f"{file_name}_good_pairs.txt"
    original_pair_output_txt = f"{file_name}_original_pairs.txt"
    return bad_pair_output_txt, good_pair_output_txt, original_pair_output_txt


def get_bad_pairs(lines,bad_pair_output_txt):
    pairs_with_low_win_rate = []
    pairs_with_low_avg_profit = []
    pairs_longer_than_2hr = []
    worst_trade_pairs = []
    pairs_with_few_trades = []
    pairs_manually_add = []
    pairs_with_low_total_profit = []
    for line in lines:
        match_bad_pair = re.match(
        r'│\s+(\S*USDT\S*)\s+\│\s*(\d+)\s*│\s*([-\d.]+)\s*│\s*([-\d.]+)\s*│\s*([-\d.]+)\s*│\s*([0-9:]+)\s*│\s*(\d+)\s+(\d+)\s+(\d+)\s+([-\d.]+)\s*│',
        line
    )
        if match_bad_pair:
            pair = match_bad_pair.group(1)
            trades = int(match_bad_pair.group(2))
            avg_profit_percent = float(match_bad_pair.group(3))
            total_profit_usdt = float(match_bad_pair.group(4))
            total_profit_percent = float(match_bad_pair.group(5))
            avg_duration = match_bad_pair.group(6)
            wins = int(match_bad_pair.group(7))
            draws = int(match_bad_pair.group(8))
            losses = int(match_bad_pair.group(9))
            win_percentage = float(match_bad_pair.group(10))
            
            """ if "TOMI/USDT:USDT" == pair:
                reason = f"Manually added"
                pairs_manually_add.append((pair, reason, win_percentage)) """

            """ desc = f"{trades} trades & {win_percentage}%"
            if trades >= 20:
                if win_percentage <= 50:
                    reason = f"Trades >= 20 & Win% <= 50"
                    pairs_with_low_win_rate.append((pair, reason, desc))
            elif trades in range(15,20):
                if win_percentage <= 55:
                    reason = f"Trades < 20 & Win% <= 55"
                    pairs_with_low_win_rate.append((pair, reason, desc))
            elif trades in range(10,15):
                if win_percentage <= 65:
                    reason = f"Trades < 15 & Win% <= 65"
                    pairs_with_low_win_rate.append((pair, reason, desc))
            elif trades in range(5,10):
                if win_percentage <= 70:
                    reason = f"Trades < 10 & Win% <= 70"
                    pairs_with_low_win_rate.append((pair, reason, desc))
            elif trades in range(0,5):
                if win_percentage <= 75:
                    reason = f"Trades < 5 & Win% <= 75"                
                    pairs_with_low_win_rate.append((pair, reason, desc)) """

            # if avg_profit_percent < 5:
            #     reason = f"Avg Profit % < 5%"
            #     pairs_with_low_avg_profit.append((pair, reason, avg_profit_percent))

            # tune this
            if total_profit_percent < 5:
                reason = f"Total Profit % < 5%"
                pairs_with_low_total_profit.append((pair, reason, total_profit_percent))
            
            try: 
                hours, minutes, seconds = map(int, avg_duration.split(':'))
                total_duration = hours * 3600 + minutes * 60 + seconds
            except:
                total_duration = 0            
                        
            if total_duration > 60 * 60  or "day" in avg_duration:
                reason = f"Avg Duration > 60 mins"                
                pairs_longer_than_2hr.append((pair, reason, avg_duration))            
                

        """ match_worst_trade = re.search(r"^\│\s*Worst trade\s*\│\s*(\S*USDT\S*)\s+(-?\d+\.\d+%)", line)
        if match_worst_trade:
            pair, percentage = match_worst_trade.groups()
            profit_percentage = float(percentage.strip('%'))
            if profit_percentage <= -10:
                reason = f"Worst Trade <= -10%"
                worst_trade_pairs.append((pair, reason, percentage)) """

    tuple_bad_pairs = pairs_with_low_total_profit +pairs_manually_add + pairs_with_few_trades + pairs_with_low_win_rate + pairs_with_low_avg_profit + worst_trade_pairs + pairs_longer_than_2hr
    table = PrettyTable()
    table.align = "r"
    table.field_names = ["Bad pair", "Reason", "Value"]
    table.add_rows(tuple_bad_pairs)
    display_table = table.get_string(sortby="Bad pair")
    print(display_table)
    
    with open(bad_pair_output_txt, "w") as f:
        f.write(display_table)

    print(f"{script_name}: Saved bad pairs to {bad_pair_output_txt}")
    return tuple_bad_pairs

def analyze_good_pairs(json_filtered_pairlist,good_pair_output_txt):
    tuple_good_pairs = []
    for line in lines:
        match_good_pair = re.match(
        r'│\s+(\S*USDT\S*)\s+\│\s*(\d+)\s*│\s*([-\d.]+)\s*│\s*([-\d.]+)\s*│\s*([-\d.]+)\s*│\s*([0-9:]+)\s*│\s*(\d+)\s+(\d+)\s+(\d+)\s+([-\d.]+)\s*│',
        line
    )
        if match_good_pair:
            pair = match_good_pair.group(1)
            for good_pair in json_filtered_pairlist:
                if good_pair == pair:
                    trades = int(match_good_pair.group(2))
                    avg_profit_percent = float(match_good_pair.group(3))
                    total_profit_usdt = float(match_good_pair.group(4))
                    total_profit_percent = float(match_good_pair.group(5))
                    avg_duration = match_good_pair.group(6)
                    wins = int(match_good_pair.group(7))
                    draws = int(match_good_pair.group(8))
                    losses = int(match_good_pair.group(9))
                    win_percentage = float(match_good_pair.group(10))
                    tuple_good_pairs.append((pair,trades,avg_profit_percent,total_profit_usdt,total_profit_percent,avg_duration,wins,draws,losses,win_percentage))
    
    table = PrettyTable()
    table.align = "r"
    table.field_names = ["Pair", "Trades", "Avg Profit %", "Tot Profit USDT", "Tot Profit %", "Avg Duration","Win" ,"Draw", "Loss", "Win%"]
    table.add_rows(tuple_good_pairs)
    display_table = table.get_string(sortby="Tot Profit USDT",reversesort=True)
    # print(display_table)

    with open(good_pair_output_txt, "w") as f:
        f.write(display_table)

    print(f"{script_name}: Saved good pairs to {good_pair_output_txt}")
    total_trades = sum(item[1] for item in tuple_good_pairs)
    print(f"Total Trades: {total_trades}")

    return tuple_good_pairs 

def analyze_original_pairs(lines,original_pair_output_txt):
    tuple_original_pairs = []
    for line in lines:
        match_original_pair = re.match(
        r'│\s+(\S*USDT\S*)\s+\│\s*(\d+)\s*│\s*([-\d.]+)\s*│\s*([-\d.]+)\s*│\s*([-\d.]+)\s*│\s*([0-9:]+)\s*│\s*(\d+)\s+(\d+)\s+(\d+)\s+([-\d.]+)\s*│',
        line
    )
        if match_original_pair:
            pair = match_original_pair.group(1)
            trades = int(match_original_pair.group(2))
            avg_profit_percent = float(match_original_pair.group(3))
            total_profit_usdt = float(match_original_pair.group(4))
            total_profit_percent = float(match_original_pair.group(5))
            avg_duration = match_original_pair.group(6)
            wins = int(match_original_pair.group(7))
            draws = int(match_original_pair.group(8))
            losses = int(match_original_pair.group(9))
            win_percentage = float(match_original_pair.group(10))
            tuple_original_pairs.append((pair,trades,avg_profit_percent,total_profit_usdt,total_profit_percent,avg_duration,wins,draws,losses,win_percentage))
        
    table = PrettyTable()
    table.align = "r"
    table.field_names = ["Pair", "Trades", "Avg Profit %", "Tot Profit USDT", "Tot Profit %", "Avg Duration","Win" ,"Draw", "Loss", "Win%"]
    table.add_rows(tuple_original_pairs)
    display_table = table.get_string(sortby="Trades",reversesort=True)
    # print(display_table)

    with open(original_pair_output_txt, "w") as f:
        f.write(display_table)

    print(f"{script_name}: Saved original pairs to {original_pair_output_txt}")
    total_trades = sum(item[1] for item in tuple_original_pairs)
    print(f"Total Trades: {total_trades}")

    return tuple_original_pairs 

def load_original_json(json_name):
    input_json = f"././user_data/configs_pairlist/unsafe/{json_name}.json"
    output_json = f"././user_data/configs_pairlist/unsafe/{json_name}-FILTERED.json"
    with open(input_json, "r") as file:
        data = commentjson.load(file)

    original_pairlist = data["exchange"]["pair_whitelist"]
    print(f"Original pairs: {len(original_pairlist)} pairs")
    # print(original_pairlist)
    return original_pairlist, data, output_json

def update_config_pairlist(original_pairlist, data, output_json, tuple_bad_pairs):

    _bad_pairlist = [pair for pair, reason, performance in tuple_bad_pairs]
    bad_pairlist = list(set(_bad_pairlist))
    print(f"Filtered bad pairs: {len(bad_pairlist)} pairs ({len(_bad_pairlist)} matches)")
    # print(bad_pairlist)     

    json_filtered_pairlist = [x for x in original_pairlist if x not in bad_pairlist]    
    print(f"New JSON filtered pairlist: {len(json_filtered_pairlist)} pairs")
    print(json_filtered_pairlist)
    # Replace the pair_whitelist
    data['exchange']['pair_whitelist'] = json_filtered_pairlist

    # Save the updated JSON back to the file
    with open(output_json, 'w') as file:
        commentjson.dump(data, file, indent=4)
    print(f"{script_name}: Updated JSON config_pairlist {output_json}")

    return json_filtered_pairlist

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Filter pairlist JSON with no bad pairs")
    parser.add_argument("backtest_logs_file", type=str, help="backtest_logs_file full_path")
    args = parser.parse_args()

    json_name = get_json_name(args.backtest_logs_file)
    bad_pair_output_txt, good_pair_output_txt, original_pair_output_txt = get_table_output_name(args.backtest_logs_file)

    print(f"{script_name}: backtest_logs_file is {args.backtest_logs_file}")

    with open(args.backtest_logs_file, "r") as file:
        lines = file.readlines()

    tuple_bad_pairs = get_bad_pairs(lines,bad_pair_output_txt)
    original_pairlist, data, output_json = load_original_json(json_name)
    json_filtered_pairlist = update_config_pairlist(original_pairlist, data, output_json,tuple_bad_pairs)
    analyze_good_pairs(json_filtered_pairlist, good_pair_output_txt)
    analyze_original_pairs(lines,original_pair_output_txt)

