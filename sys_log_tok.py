import json
import re

def tokenize_message_log(input_file, output_file):
    tokenized_entries = []
    
    log_pattern = re.compile(
        r'^(?P<timestamp>\w{3} \d{1,2} \d{2}:\d{2}:\d{2}) (?P<hostname>\S+) (?P<process>[\w\-.]+)(?:\[(?P<pid>\d+)\])?: (?P<message>.+)$'
    )

    with open(input_file, 'r') as file:
        for line in file:
            match = log_pattern.match(line.strip())
            if match:
                tokenized_entry = {
                    "timestamp": match.group("timestamp"),
                    "hostname": match.group("hostname"),
                    "process": match.group("process"),
                    "pid": match.group("pid") if match.group("pid") else None,
                    "message": match.group("message").strip()
                }
                tokenized_entries.append(tokenized_entry)
            else:
                
                tokenized_entries.append({
                    "timestamp": None,
                    "hostname": None,
                    "process": None,
                    "pid": None,
                    "message": line.strip()
                })
    with open(output_file, 'w') as output:
        json.dump(tokenized_entries, output, indent=4)
    print(f"Tokenized logs saved to {output_file}")

# Path to the messages log file and output file
input_file = "/var/log/messages"  # Replace with the path to your messages file
output_file = "/root/container_logs/sys_log_tok.json"  # Replace with your desired output path

tokenize_message_log(input_file, output_file)
