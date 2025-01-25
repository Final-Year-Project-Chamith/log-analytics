import json
import re
import os
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(
    filename="/root/processed_logs/script_debug.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def standardize_timestamp(timestamp, format="%b %d %H:%M:%S"):
    try:
        return datetime.strptime(
            f"{datetime.now().year} {timestamp}", f"%Y {format}"
        ).isoformat()
    except ValueError as e:
        logging.error(f"Timestamp parsing error: {e}")
        return None


def tokenize_host_logs(input_file, output_file):
    tokenized_entries = []
    log_pattern = re.compile(
        r"^(?P<timestamp>\w{3} \d{1,2} \d{2}:\d{2}:\d{2}) (?P<hostname>\S+) (?P<process>[\w\-.]+)(?:\[(?P<pid>\d+)\])?: (?P<message>.+)$"
    )

    try:
        with open(input_file, "r") as file:
            for line in file:
                match = log_pattern.match(line.strip())
                if match:
                    tokenized_entry = {
                        "source": "host",
                        "timestamp": standardize_timestamp(match.group("timestamp")),
                        "hostname": match.group("hostname"),
                        "process": match.group("process"),
                        "pid": match.group("pid") if match.group("pid") else None,
                        "message": match.group("message").strip(),
                    }
                else:
                    tokenized_entry = {
                        "source": "host",
                        "timestamp": None,
                        "hostname": None,
                        "process": None,
                        "pid": None,
                        "message": line.strip(),
                    }
                tokenized_entries.append(tokenized_entry)
    except Exception as e:
        logging.error(f"Error processing host logs: {e}")

    with open(output_file, "w") as output:
        json.dump(tokenized_entries, output, indent=4)
    logging.info(f"Host logs tokenized and saved to {output_file}")


def tokenize_container_logs(directory, output_file):
    results = []
    try:
        for root, _, files in os.walk(directory):
            for filename in files:
                if filename.endswith(".log"):
                    container_id = os.path.basename(root)
                    file_path = os.path.join(root, filename)

                    with open(file_path, "r") as file:
                        for line in file:
                            try:
                                log_entry = json.loads(line.strip())
                                raw_time = log_entry.get("time", "")
                                # Normalize timestamp (truncate excessive fractional seconds)
                                if raw_time and "." in raw_time:
                                    normalized_time = raw_time.split(".")[0] + "Z"
                                else:
                                    normalized_time = raw_time

                                tokenized_entry = {
                                    "source": "container",
                                    "timestamp": (
                                        datetime.fromisoformat(
                                            normalized_time.replace("Z", "")
                                        ).isoformat()
                                        if normalized_time
                                        else None
                                    ),
                                    "container_id": container_id,
                                    "stream": log_entry.get("stream", ""),
                                    "message": log_entry.get("log", "").strip(),
                                }
                                results.append(tokenized_entry)
                            except json.JSONDecodeError as e:
                                logging.warning(
                                    f"JSON decoding error in {filename}: {e}"
                                )
                            except ValueError as e:
                                logging.warning(
                                    f"Invalid timestamp format in {filename}: {raw_time} - {e}"
                                )
    except Exception as e:
        logging.error(f"Error processing container logs: {e}")

    with open(output_file, "w") as output:
        json.dump(results, output, indent=4)
    logging.info(f"Container logs tokenized and saved to {output_file}")


def merge_logs(host_log_file, container_log_file, output_file):
    try:
        with open(host_log_file, "r") as host_file, open(
            container_log_file, "r"
        ) as container_file:
            host_logs = json.load(host_file)
            container_logs = json.load(container_file)

            combined_logs = sorted(
                host_logs + container_logs, key=lambda x: x.get("timestamp") or ""
            )

        with open(output_file, "w") as output:
            json.dump(combined_logs, output, indent=4)
        logging.info(f"Merged logs saved to {output_file}")
    except Exception as e:
        logging.error(f"Error merging logs: {e}")


# Example usage
host_input_file = "/var/log/messages"  # Updated to use /var/log/messages for CentOS
directory = "/var/lib/docker/containers"
host_output_file = "/root/processed_logs/host_logs.json"
container_output_file = "/root/processed_logs/container_logs.json"
merged_output_file = "/root/processed_logs/merged_logs.json"

os.makedirs("/root/processed_logs", exist_ok=True)

try:
    tokenize_host_logs(host_input_file, host_output_file)
    tokenize_container_logs(directory, container_output_file)
    merge_logs(host_output_file, container_output_file, merged_output_file)
except Exception as e:
    logging.critical(f"Critical error in script execution: {e}")
