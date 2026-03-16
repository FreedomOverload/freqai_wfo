import os
import ast
import csv


def extract_buy_params(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    start = content.find("buy_params = ")
    if start == -1:
        return None

    end = content.find("\n\n", start)
    if end == -1:
        end = len(content)

    buy_params_str = content[start + len("buy_params = ") : end].strip()
    try:
        buy_params = ast.literal_eval(buy_params_str)
        return buy_params
    except (SyntaxError, ValueError):
        return None


def process_files(folder_path, output_csv):
    data = []

    for filename in os.listdir(folder_path):
        if filename.endswith(".txt"):
            file_path = os.path.join(folder_path, filename)
            buy_params = extract_buy_params(file_path)
            if buy_params:
                data.append([filename, buy_params])

    with open(output_csv, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["filename", "buy_params"])
        writer.writerows(data)


# Example usage:
folder_path = "baseline_results/to_process"  # Change to your actual folder path
output_csv = "buy_params.csv"
process_files(folder_path, output_csv)
