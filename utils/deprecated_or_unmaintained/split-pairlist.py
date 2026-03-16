import json
import os
import shutil
import commentjson
import argparse

def main():
    script_name = os.path.basename(__file__)

    parser = argparse.ArgumentParser(description="Split pairlist JSON into multiple JSONS for backtesting")
    parser.add_argument("json", type=str, help="pairlit JSON name without .json")
    args = parser.parse_args()
    print(f"{script_name}: json is {args.json}")

    # Configuration
    input_file = f"././user_data/configs_pairlist/unsafe/{args.json}.json"
    output_dir = f"././user_data/cache/{args.json}"
    pairs_per_json = 1  # Number of pairs per JSON
    
    # Ensure the output directory exists
    try:
        shutil.rmtree(output_dir)
    except FileNotFoundError:
        # Directory doesn't exist, no action needed
        pass
    
    os.makedirs(output_dir, exist_ok=True)

    # Read the JSON file
    with open(input_file, "r") as file:
        data = commentjson.load(file)

    # Splitting logic
    pair_whitelist = data["exchange"]["pair_whitelist"]
    chunks = [pair_whitelist[i:i+pairs_per_json] for i in range(0, len(pair_whitelist), pairs_per_json)]

    # Create new JSON files
    for i, chunk in enumerate(chunks):
        new_json = {
            "exchange": {
                "name": data["exchange"]["name"],
                "pair_whitelist": chunk
            },
            "pairlists": data["pairlists"]
        }
        output_file = os.path.join(output_dir, f"{i+1}.json")
        with open(output_file, "w") as file:
            json.dump(new_json, file, indent=4)
        print(f"{script_name}: created {output_file}")

if __name__ == "__main__":
    main()
