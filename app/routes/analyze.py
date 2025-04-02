from flask import Blueprint, request, jsonify
from model.loader import get_model
from app.services.ai_analysis import generate_ai_analysis
from app.services.rule_engine import extract_metrics
MODEL_NAME = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
MAX_ATTEMPTS = 2
MIN_LOG_LENGTH = 10  
analyze_bp = Blueprint("analyze", __name__)

@analyze_bp.route("/analyze", methods=["POST"])
def analyze():
    generator = get_model()
    if not generator:
        return jsonify({"error": "Model not available"}), 503

    logs = request.json.get("logs", [])
    if not logs:
        return jsonify({"error": "No logs provided"}), 400

    from app.services.utils import truncate_logs
    logs = truncate_logs(logs, max_lines=200)

    report = generate_ai_analysis(logs, generator)
    return jsonify({
        "report": report,
        "model": generator.model.config.name,
        "analysis_type": "AI" if "Status Summary:" in report else "Rule-based",
        "timestamp": datetime.now().isoformat()
    })

@analyze_bp.route("/test", methods=["GET"])
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

