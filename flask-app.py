from flask import Flask, request, jsonify
from transformers import pipeline, AutoTokenizer
import torch
from datetime import datetime
import re
from functools import lru_cache

app = Flask(__name__)



@lru_cache(maxsize=1)
def get_model():
    try:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        model = pipeline(
            "text-generation",
            model=MODEL_NAME,
            torch_dtype=torch.float16,
            device_map="auto"
        )
        return model
    except Exception as e:
        print(f"⚠️ Failed to load model: {e}")
        return None

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

def generate_ai_analysis(logs_text: str, generator) -> str:
    """Generate analysis using AI with strict validation"""
    if not generator or len(logs_text) < MIN_LOG_LENGTH:
        return None
    
    prompt = f"""<|system|>
Generate a Docker log analysis report with exactly these sections:

1. Status Summary: [concise overview]
2. Critical Issues: [bullet points]
3. Resource Trends: [CPU/Memory patterns]
4. Recommended Actions: [specific steps]

Rules:
- Use only information from these logs:
{logs_text}
- Never mention commands or tools
- Be technical and concise</s>
<|user|>
Analyze these logs:</s>
<|assistant|>
"""
    
    for _ in range(MAX_ATTEMPTS):
        print("attempt", MAX_ATTEMPTS)
        try:
            result = generator(
                prompt,
                max_new_tokens=350,
                temperature=0.2,
                top_p=0.9,
                do_sample=False,
                repetition_penalty=1.3
            )[0]['generated_text']
            
            report = result.split("<|assistant|>")[-1].strip()
            if all(
                section in report 
                for section in [
                    "1. Status Summary:", 
                    "2. Critical Issues:", 
                    "3. Resource Trends:", 
                    "4. Recommended Actions:"
                ]
            ):
                return report
        except Exception:
            continue
    
    return None

def generate_hybrid_report(logs: list, generator) -> str:
    """Generate analysis using both rules and AI"""
    metrics = extract_metrics(logs)
    logs_text = "\n".join([log.get('message', '') for log in logs])
    
    ai_report = generate_ai_analysis(logs_text, generator)
    if ai_report:
        return ai_report
    
    avg_cpu = sum(metrics['cpu_usage'])/len(metrics['cpu_usage']) if metrics['cpu_usage'] else 0
    max_mem = max(metrics['memory_usage']) if metrics['memory_usage'] else 0
    
    return f"""1. Status Summary: 
- Found {len(metrics['errors'])} errors and {len(metrics['warnings'])} warnings
- {metrics['restarts']} container restarts detected

2. Critical Issues:
{'- ' + '\n- '.join(metrics['errors'][:3]) if metrics['errors'] else 'None'}

3. Resource Trends:
- CPU: {'High' if avg_cpu > 70 else 'Normal'} (avg {avg_cpu:.0f}%)
- Memory: {'Critical' if max_mem > 90 else 'Normal'}

4. Recommended Actions:
- Investigate top error messages
- {'Check resource allocation' if avg_cpu > 70 or max_mem > 90 else 'Monitor system'}
"""

@app.route('/analyze', methods=['POST'])
def analyze():
    generator = get_model()
    if not generator:
        return jsonify({"error":"model not available"}), 503
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
        
    logs = request.json.get("logs", [])
    if not logs:
        return jsonify({"error": "No logs provided"}), 400
    
    report = generate_hybrid_report(logs, generator)
    
    return jsonify({
        "report": report,
        "model": MODEL_NAME,
        "analysis_type": "AI" if generator and len(report) > 200 else "Rule-based",
        "timestamp": datetime.now().isoformat()
    })
@app.route('/test', methods=['GET'])
def test_analysis():
    generator = get_model()
    if not generator:
        return jsonify({"error": "Model not available"}), 503

    sample_logs = [
        {"message": "Error: Failed to connect to database"},
        {"message": "Container restart detected"},
        {"message": "CPU usage at 85%"},
        {"message": "Memory usage at 1.2 GB"},
        {"message": "Warning: Disk usage approaching limit"},
        {"message": "Service started successfully"},
        {"message": "Error: Timeout while connecting to service"},
        {"message": "CPU usage at 65%"},
    ]

    report = generate_hybrid_report(sample_logs, generator)

    return jsonify({
        "sample_logs_count": len(sample_logs),
        "model": MODEL_NAME,
        "report": report,
        "analysis_type": "AI" if generator and len(report) > 200 else "Rule-based",
        "timestamp": datetime.now().isoformat()
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)