MODEL_NAME = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
MAX_ATTEMPTS = 2
MIN_LOG_LENGTH = 10  
def extract_metrics(logs: list) -> dict:
    """Extract key metrics from logs using rules"""
    metrics = {
        'errors': [],
        'warnings': [],
        'restarts': 0,
        'cpu_usage': [],
        'memory_usage': []
    }

    for log in logs:
        msg = log.get('message', '').lower()
        if 'error' in msg:
            metrics['errors'].append(log['message'])
        elif 'warning' in msg:
            metrics['warnings'].append(log['message'])
        elif 'restart' in msg:
            metrics['restarts'] += 1
        
        if 'cpu' in msg:
            match = re.search(r'cpu.*?(\d+)%', msg)
            if match:
                metrics['cpu_usage'].append(int(match.group(1)))
        if 'memory' in msg:
            match = re.search(r'memory.*?(\d+\.?\d*)\s?gb', msg, re.IGNORECASE)
            if match:
                metrics['memory_usage'].append(float(match.group(1)))

    return metrics