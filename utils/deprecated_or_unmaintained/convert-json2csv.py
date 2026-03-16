# To use with chronos-forecasting

import csv
import datetime
import json

def json_to_csv(input_file, output_file):
    try:
        with open(input_file, 'r') as f:
            json_data = json.load(f)

        if not isinstance(json_data, list) or not json_data or not all(isinstance(item, list) for item in json_data):
            raise ValueError("The JSON file should contain a list of lists.")

        header = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']

        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)

            if header:
                writer.writerow(header)

            for row in json_data:
                # Convert the timestamp and format the date
                formatted_date = datetime.datetime.fromtimestamp(row[0] / 1000).strftime('%Y-%m-%d %H:%M:%S')
                modified_row = [formatted_date] + row[1:]
                writer.writerow(modified_row)
                #original_row = row[0:]
                #writer.writerow(original_row)

        print(f"Successfully converted '{input_file}' to '{output_file}'.")

    except FileNotFoundError:
        print(f"Error: The file '{input_file}' was not found.")
    except json.JSONDecodeError:
        print(f"Error: The file '{input_file}' is not a valid JSON file.")
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

json_to_csv('user_data/data/kucoin/BTC_USDT-5m.json', 'user_data/data/kucoin/BTC_USDT-5m.csv')
