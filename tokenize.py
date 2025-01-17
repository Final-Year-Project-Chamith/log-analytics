import json
import os

def tokenize_logs(directory, output_file):
    results = {}

    # Iterate over all .log files in the directory
    for filename in os.listdir(directory):
        if filename.endswith(".log"):
            container_id = filename.replace(".log", "")  # Extract container ID from filename
            file_path = os.path.join(directory, filename)

            # Process each log file
            with open(file_path, 'r') as file:
                tokenized_entries = []
                for line in file:
                    try:
                        # Parse each line as a JSON object
                        log_entry = json.loads(line.strip())
                        # Extract tokens and include the container ID
                        tokenized_entry = {
                            "containerID": container_id,  # Include the container ID
                            "log": log_entry.get("log", "").strip(),
                            "stream": log_entry.get("stream", ""),
                            "time": log_entry.get("time", "")
                        }
                        tokenized_entries.append(tokenized_entry)
                    except json.JSONDecodeError:
                        print(f"Error decoding JSON line in {filename}: {line.strip()}")
                # Store the tokenized entries using the container ID as a key
                results[container_id] = tokenized_entries

    # Write the results to the output file
    with open(output_file, 'w') as output:
        json.dump(results, output, indent=4)
    print(f"Tokenized logs saved to {output_file}")

# Directory containing the log files and output file path
directory = "/path/to/your/log/files"  # Replace with your directory path
output_file = "/path/to/your/output/tokenized_logs.json"  # Replace with your desired output path

tokenize_logs(directory, output_file)
