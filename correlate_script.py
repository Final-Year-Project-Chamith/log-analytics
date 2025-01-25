import json
from datetime import datetime, timedelta

def load_tokenized_logs(file_path):
    """
    Load tokenized logs from a file.
    Args:
        file_path (str): Path to the JSON file containing tokenized logs.
    Returns:
        list: List of tokenized log entries.
    """
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except Exception as e:
        print(f"Error loading file {file_path}: {e}")
        return []

def parse_time(timestamp, fmt="%b %d %H:%M:%S"):
    """
    Parse a timestamp string into a datetime object.
    Args:
        timestamp (str): Timestamp string.
        fmt (str): Format of the timestamp.
    Returns:
        datetime: Parsed datetime object, or None if parsing fails.
    """
    try:
        return datetime.strptime(timestamp, fmt)
    except ValueError:
        return None

def correlate_logs(system_logs, container_logs, time_window=5):
    """
    Correlate system logs and container logs based on timestamps.
    Args:
        system_logs (list): List of system log entries.
        container_logs (list): List of container log entries.
        time_window (int): Time window in seconds for correlation.
    Returns:
        list: List of correlated log entries.
    """
    correlated_logs = []
    time_window = timedelta(seconds=time_window)

    for sys_log in system_logs:
        sys_time = parse_time(sys_log.get("timestamp"))
        if not sys_time:
            continue

        for container_id, logs in container_logs.items():
            for con_log in logs:
                con_time = parse_time(con_log.get("time"), "%Y-%m-%dT%H:%M:%S.%fZ")
                if not con_time:
                    continue

                if abs(sys_time - con_time) <= time_window:
                    correlated_logs.append({
                        "system_log": sys_log,
                        "container_log": {
                            **con_log,
                            "containerID": container_id
                        }
                    })

    return correlated_logs

def main():
    # File paths for tokenized logs
    system_log_file = "/root/container_logs/sys_log_tok.json"
    container_log_file = "/root/container_logs/tokenized_logs.json"
    output_file = "/root/container_logs/correlated_logs.json"

    # Load tokenized logs
    system_logs = load_tokenized_logs(system_log_file)
    container_logs = load_tokenized_logs(container_log_file)

    # Correlate logs
    correlated_logs = correlate_logs(system_logs, container_logs, time_window=5)

    # Save correlated logs
    try:
        with open(output_file, 'w') as output:
            json.dump(correlated_logs, output, indent=4, default=str)
        print(f"Correlated logs saved to {output_file}")
    except Exception as e:
        print(f"Failed to save correlated logs: {e}")

if __name__ == "__main__":
    main()
