from flask import Flask, request, jsonify
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
import torch
from datetime import datetime
import re
from functools import lru_cache

app = Flask(__name__)

# Use Llama 2 7B Chat with quantization if GPU, else FP16 CPU
MODEL_NAME = "meta-llama/Llama-2-7b-chat-hf"
MAX_ATTEMPTS = 2
MIN_LOG_LENGTH = 10

@lru_cache(maxsize=1)
def get_pipeline():
    """
    Load and cache the text-generation pipeline for Llama-2 Chat model.
    Applies 4-bit quantization on GPU to fit in limited memory.
    """
    use_cuda = torch.cuda.is_available()
    dtype = torch.float16 if use_cuda else torch.float32
    quant_config = None
    if use_cuda:
        quant_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_quant_type="nf4"
        )

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        trust_remote_code=True,
        torch_dtype=dtype,
        quantization_config=quant_config,
        device_map="auto" if use_cuda else {"": "cpu"}
    )

    # Use text-generation pipeline for chat-capable model
    gen = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        trust_remote_code=True,
    )
    return gen


def extract_metrics(logs: list) -> dict:
    metrics = {"errors": [], "warnings": [], "restarts": 0, "cpu_usage": [], "memory_usage": []}
    for log in logs:
        msg = log.get("message", "").lower()
        if "error" in msg:
            metrics["errors"].append(log["message"])
        elif "warning" in msg:
            metrics["warnings"].append(log["message"])
        elif "restart" in msg:
            metrics["restarts"] += 1
        if "cpu" in msg:
            m = re.search(r"cpu.*?(\d+)%", msg)
            if m:
                metrics["cpu_usage"].append(int(m.group(1)))
        if "memory" in msg:
            m = re.search(r"memory.*?(\d+\.?\d*)\s?gb", msg, re.IGNORECASE)
            if m:
                metrics["memory_usage"].append(float(m.group(1)))
    return metrics


def generate_ai_report(logs: list, gen) -> str:
    """
    Generate analysis report via text-generation pipeline.
    """
    logs_text = "\n".join(log.get("message", "") for log in logs)
    if len(logs_text) < MIN_LOG_LENGTH:
        return None

    prompt = (
        "<|system|>"
        "You are an expert system logs analyzer. "
        "Generate a report with sections:\n"
        "1. Status Summary\n"
        "2. Critical Issues\n"
        "3. Resource Trends\n"
        "4. Recommended Actions\n"
        f"Only use this log content:\n{logs_text}\n"
        "<|user|>Analyze and generate the report:<|assistant|>"
    )

    for attempt in range(MAX_ATTEMPTS):
        try:
            out = gen(
                prompt,
                max_new_tokens=300,
                temperature=0.7,
                top_p=0.95,
                do_sample=True,
                repetition_penalty=1.2,
            )
            text = out[0]["generated_text"]
            # split off the prompt
            report = text.split("<|assistant|>")[-1].strip()
            return report
        except Exception as e:
            print(f"Attempt {attempt+1} failed: {e}")
    return None


def generate_hybrid_report(logs: list, gen) -> str:
    ai_report = generate_ai_report(logs, gen)
    if ai_report:
        return ai_report
    # fallback rule-based summary
    metrics = extract_metrics(logs)
    avg_cpu = sum(metrics["cpu_usage"]) / len(metrics["cpu_usage"]) if metrics["cpu_usage"] else 0
    max_mem = max(metrics["memory_usage"]) if metrics["memory_usage"] else 0
    return (
        f"1. Status Summary:\n"
        f"- {len(metrics['errors'])} errors, {len(metrics['warnings'])} warnings\n"
        f"- {metrics['restarts']} restarts detected\n\n"
        f"2. Critical Issues:\n"
        f"{'- ' + '\n- '.join(metrics['errors'][:3]) if metrics['errors'] else 'None'}\n\n"
        f"3. Resource Trends:\n"
        f"- CPU: {'High' if avg_cpu>70 else 'Normal'} (avg {avg_cpu:.0f}%)\n"
        f"- Memory: {'Critical' if max_mem>90 else 'Normal'}\n\n"
        f"4. Recommended Actions:\n"
        f"- Investigate errors\n"
        f"- {'Check allocation' if avg_cpu>70 or max_mem>90 else 'Monitor'}"
    )

@app.route("/analyze", methods=["POST"])
def analyze():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    logs = request.json.get("logs", [])
    if not logs:
        return jsonify({"error": "No logs provided"}), 400

    gen = get_pipeline()
    report = generate_hybrid_report(logs, gen)
    analysis_type = "AI" if report and len(report) > 0 else "Rule-based"
    return jsonify({
        "report": report or "Could not generate report.",
        "model": MODEL_NAME,
        "analysis_type": analysis_type,
        "timestamp": datetime.now().isoformat()
    })

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "cuda_available": torch.cuda.is_available(),
        "device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0
    })

if __name__ == '__main__':
    print("Warming up pipeline...")
    get_pipeline()
    print("Warmup complete, CUDA?", torch.cuda.is_available())
    app.run(host='0.0.0.0', port=5000)
