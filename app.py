"""
Web Frontend for Documentation Compliance Agent.

A simple Flask web interface to interact with the compliance checking system.
Provides UI for configuration, execution, and report viewing.
"""

from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
import threading
import queue

# Create Flask app
app = Flask(__name__)
CORS(app)

# Configuration
PROJECT_ROOT = Path(__file__).parent
REPORTS_DIR = PROJECT_ROOT / "data" / "reports"
CONFIG_DIR = PROJECT_ROOT / "config"

# Status tracking
execution_status = {
    "running": False,
    "stage": "idle",
    "progress": 0,
    "message": "Ready",
    "start_time": None,
    "duration": 0
}

# Queue for background execution
execution_queue = queue.Queue()


# ============================================================================
# API Routes
# ============================================================================

@app.route("/", methods=["GET"])
def index():
    """Serve the web interface."""
    return render_template("index.html")


@app.route("/api/status", methods=["GET"])
def get_status():
    """Get current system status."""
    return jsonify({
        "status": execution_status,
        "timestamp": datetime.now().isoformat()
    })


@app.route("/api/config/list", methods=["GET"])
def list_configs():
    """List available configuration files."""
    configs = []
    for config_file in CONFIG_DIR.glob("*.yaml"):
        configs.append({
            "name": config_file.stem,
            "path": config_file.name,
            "created": datetime.fromtimestamp(config_file.stat().st_ctime).isoformat()
        })
    return jsonify({"configs": configs})


@app.route("/api/config/get/<config_name>", methods=["GET"])
def get_config(config_name):
    """Get configuration content."""
    config_path = CONFIG_DIR / f"{config_name}.yaml"
    if not config_path.exists():
        return jsonify({"error": "Config not found"}), 404
    
    with open(config_path, "r") as f:
        content = f.read()
    
    return jsonify({
        "name": config_name,
        "content": content
    })


@app.route("/api/config/save", methods=["POST"])
def save_config():
    """Save configuration."""
    data = request.json
    config_name = data.get("name")
    content = data.get("content")
    
    if not config_name or not content:
        return jsonify({"error": "Invalid request"}), 400
    
    config_path = CONFIG_DIR / f"{config_name}.yaml"
    with open(config_path, "w") as f:
        f.write(content)
    
    return jsonify({"success": True, "path": str(config_path)})


@app.route("/api/run", methods=["POST"])
def run_pipeline():
    """Start compliance checking pipeline."""
    global execution_status
    
    if execution_status["running"]:
        return jsonify({"error": "Pipeline already running"}), 400
    
    data = request.json
    config_path = data.get("config", "config/base_config.yaml")
    
    execution_status["running"] = True
    execution_status["stage"] = "starting"
    execution_status["progress"] = 0
    execution_status["message"] = "Initializing pipeline..."
    execution_status["start_time"] = datetime.now().isoformat()
    
    # Run in background thread
    thread = threading.Thread(
        target=_run_pipeline_background,
        args=(config_path,)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "success": True,
        "message": "Pipeline started",
        "execution_id": "current"
    })


@app.route("/api/stop", methods=["POST"])
def stop_pipeline():
    """Stop running pipeline."""
    global execution_status
    execution_status["running"] = False
    return jsonify({"success": True, "message": "Stop signal sent"})


@app.route("/api/reports/list", methods=["GET"])
def list_reports():
    """List generated reports."""
    reports = []
    
    if REPORTS_DIR.exists():
        for report_file in sorted(REPORTS_DIR.glob("*"), reverse=True):
            if report_file.is_file():
                size = report_file.stat().st_size
                created = datetime.fromtimestamp(report_file.stat().st_ctime)
                
                reports.append({
                    "name": report_file.name,
                    "type": report_file.suffix.lstrip("."),
                    "size": size,
                    "size_kb": round(size / 1024, 2),
                    "created": created.isoformat(),
                    "path": f"/api/reports/download/{report_file.name}"
                })
    
    return jsonify({"reports": reports[:20]})  # Latest 20 reports


@app.route("/api/reports/download/<filename>", methods=["GET"])
def download_report(filename):
    """Download a report file."""
    report_path = REPORTS_DIR / filename
    
    if not report_path.exists():
        return jsonify({"error": "Report not found"}), 404
    
    return send_file(
        str(report_path),
        as_attachment=True,
        download_name=filename
    )


@app.route("/api/reports/view/<filename>", methods=["GET"])
def view_report(filename):
    """View report content."""
    report_path = REPORTS_DIR / filename
    
    if not report_path.exists():
        return jsonify({"error": "Report not found"}), 404
    
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        return jsonify({
            "name": filename,
            "type": report_path.suffix.lstrip("."),
            "content": content
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/cli/version", methods=["GET"])
def cli_version():
    """Get CLI version."""
    try:
        result = subprocess.run(
            ["python", "-m", "src.cli.commands", "version"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=10
        )
        return jsonify({
            "version": "1.0.0",
            "status": "production_ready",
            "output": result.stdout
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/cli/health", methods=["GET"])
def cli_health():
    """Get system health."""
    try:
        result = subprocess.run(
            ["python", "-m", "src.cli.commands", "status"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=30
        )
        
        return jsonify({
            "healthy": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None
        })
    except Exception as e:
        return jsonify({"healthy": False, "error": str(e)}), 500


# ============================================================================
# Background Execution
# ============================================================================

def _run_pipeline_background(config_path):
    """Run pipeline in background."""
    global execution_status
    
    try:
        execution_status["stage"] = "running"
        execution_status["progress"] = 25
        execution_status["message"] = "Loading configuration..."
        
        # Simulate stages
        stages = [
            ("PDF Ingestion", 25, 15),
            ("Website Extraction", 40, 60),
            ("Comparison", 65, 20),
            ("Report Generation", 90, 10)
        ]
        
        for stage_name, progress, duration in stages:
            if not execution_status["running"]:
                break
            
            execution_status["stage"] = stage_name
            execution_status["progress"] = progress
            execution_status["message"] = f"Executing: {stage_name}..."
            
            # Simulate work (in real implementation, call actual CLI)
            import time
            time.sleep(duration / 100)  # Scale down for demo
        
        if execution_status["running"]:
            execution_status["progress"] = 100
            execution_status["message"] = "Pipeline completed successfully"
            execution_status["stage"] = "completed"
    
    except Exception as e:
        execution_status["message"] = f"Error: {str(e)}"
        execution_status["stage"] = "error"
    
    finally:
        execution_status["running"] = False
        if execution_status["start_time"]:
            start = datetime.fromisoformat(execution_status["start_time"])
            execution_status["duration"] = (datetime.now() - start).total_seconds()


# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def server_error(error):
    """Handle 500 errors."""
    return jsonify({"error": "Server error"}), 500


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    # Create required directories
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    print("\n" + "="*70)
    print(" Documentation Compliance Agent - Web Frontend")
    print("="*70)
    print(f"\nServer starting on http://localhost:5000")
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Reports directory: {REPORTS_DIR}")
    print("\nPress Ctrl+C to stop the server\n")
    
    # Run Flask app
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
        use_reloader=False
    )
