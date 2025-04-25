from flask import Flask, request, jsonify
from transformers import pipeline, AutoTokenizer
import torch
from datetime import datetime
import re
from functools import lru_cache

app = Flask(__name__)

MODEL_NAME = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
MAX_ATTEMPTS = 2
MIN_LOG_LENGTH = 10


@lru_cache(maxsize=1)
def get_model():
    try:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        model = pipeline(
            "text-generation",
            model=MODEL_NAME,
            torch_dtype=torch.float16,
            device_map="auto",
        )
        return model
    except Exception as e:
        print(f"⚠️ Failed to load model: {e}")
        return None


def extract_metrics(logs: list) -> dict:
    metrics = {
        "errors": [],
        "warnings": [],
        "restarts": 0,
        "cpu_usage": [],
        "memory_usage": [],
    }

    for log in logs:
        msg = log.get("message", "").lower()
        if "error" in msg:
            metrics["errors"].append(log["message"])
        elif "warning" in msg:
            metrics["warnings"].append(log["message"])
        elif "restart" in msg:
            metrics["restarts"] += 1

        if "cpu" in msg:
            match = re.search(r"cpu.*?(\d+)%", msg)
            if match:
                metrics["cpu_usage"].append(int(match.group(1)))
        if "memory" in msg:
            match = re.search(r"memory.*?(\d+\.?\d*)\s?gb", msg, re.IGNORECASE)
            if match:
                metrics["memory_usage"].append(float(match.group(1)))

    return metrics


def generate_ai_analysis(logs_text: str, generator) -> str:
    if not generator or len(logs_text) < MIN_LOG_LENGTH:
        return None

    prompt = f"""<|system|>
Generate a Docker log analysis report with sections:

1. Status Summary
2. Critical Issues
3. Resource Trends
4. Recommended Actions

Only use this log content:
{logs_text}
</s><|user|>
Analyze and generate the report:</s><|assistant|>
"""

    for attempt in range(MAX_ATTEMPTS):
        print(f"🔁 Attempt {attempt + 1}")
        try:
            result = generator(
                prompt,
                max_new_tokens=350,
                temperature=0.7,
                top_p=0.95,
                do_sample=True,
                repetition_penalty=1.2,
            )[0]["generated_text"]

            report = result.split("<|assistant|>")[-1].strip()
            print("AI Generated Report:\n", report[:300])  # preview
            return report  # Return even if not perfectly formatted
        except Exception as e:
            print(f"LLM attempt {attempt + 1} failed:", e)

    return None


def generate_hybrid_report(logs: list, generator) -> str:
    metrics = extract_metrics(logs)
    logs_text = "\n".join([log.get("message", "") for log in logs])

    ai_report = generate_ai_analysis(logs_text, generator)
    if ai_report:
        return ai_report

    avg_cpu = (
        sum(metrics["cpu_usage"]) / len(metrics["cpu_usage"])
        if metrics["cpu_usage"]
        else 0
    )
    max_mem = max(metrics["memory_usage"]) if metrics["memory_usage"] else 0

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


@app.route("/analyze", methods=["POST"])
def analyze():
    generator = get_model()
    if not generator:
        return jsonify({"error": "model not available"}), 503
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    logs = request.json.get("logs", [])
    if not logs:
        return jsonify({"error": "No logs provided"}), 400

    report = generate_hybrid_report(logs, generator)

    return jsonify(
        {
            "report": report or "LLM could not generate a report.",
            "model": MODEL_NAME,
            "analysis_type": "AI" if report else "Rule-based",
            "timestamp": datetime.now().isoformat(),
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
