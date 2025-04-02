from flask import Flask
from app.routes.analyze import analyze_bp

app = Flask(__name__)
app.register_blueprint(analyze_bp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
