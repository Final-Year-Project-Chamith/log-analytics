import json
import os

def tokenize_logs(directory, output_file):
    results = {}

    for root, _, files in os.walk(directory):
        for filename in files:
            if filename.endswith(".log"):
                container_id = os.path.basename(root)  
                file_path = os.path.join(root, filename)

                
                with open(file_path, 'r') as file:
                    tokenized_entries = []
                    for line in file:
                        try:
                            log_entry = json.loads(line.strip())
                            tokenized_entry = {
                                "containerID": container_id, 
                                "log": log_entry.get("log", "").strip(),
                                "stream": log_entry.get("stream", ""),
                                "time": log_entry.get("time", "")
                            }
                            tokenized_entries.append(tokenized_entry)
                        except json.JSONDecodeError:
                            print(f"Error decoding JSON line in {filename}: {line.strip()}")
                    if container_id not in results:
                        results[container_id] = []
                    results[container_id].extend(tokenized_entries)


    with open(output_file, 'w') as output:
        json.dump(results, output, indent=4)
    print(f"Tokenized logs saved to {output_file}")

# Directory containing the log files and output file path
directory = "/var/lib/docker/containers"  # Path to the Docker containers' log directory
output_file = "/root/container_logs/tokenized_logs.json"  # Replace with your desired output path

tokenize_logs(directory, output_file)
