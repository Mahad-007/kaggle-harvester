#!/usr/bin/env python3
"""
Web dashboard for Kaggle Data Ingestion Engine.
Simple Flask-based UI to visualize and monitor the ingestion process.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, jsonify, request
from config.settings import Settings

app = Flask(__name__)

# Load settings
try:
    settings = Settings.load()
except Exception as e:
    print(f"Warning: Could not load settings: {e}")
    settings = None


def get_statistics():
    """Get current statistics from storage and state files."""
    if not settings:
        return {"error": "Settings not loaded"}

    stats = {
        "datasets": {
            "total": 0,
            "total_size_mb": 0,
            "total_size_gb": 0
        },
        "metadata": {
            "total_files": 0
        },
        "state": {
            "total_processed": 0,
            "successful_downloads": 0,
            "failed_downloads": 0,
            "last_poll": None
        },
        "storage": {
            "available_space_gb": 0
        }
    }

    # Get storage statistics
    datasets_dir = settings.storage.datasets_dir
    if datasets_dir.exists():
        total_size = 0
        dataset_count = 0
        for username_dir in datasets_dir.iterdir():
            if username_dir.is_dir():
                for dataset_dir in username_dir.iterdir():
                    if dataset_dir.is_dir():
                        dataset_count += 1
                        for file_path in dataset_dir.rglob('*'):
                            if file_path.is_file():
                                total_size += file_path.stat().st_size

        stats["datasets"]["total"] = dataset_count
        stats["datasets"]["total_size_mb"] = round(total_size / (1024 * 1024), 2)
        stats["datasets"]["total_size_gb"] = round(total_size / (1024 * 1024 * 1024), 2)

    # Get metadata statistics
    metadata_dir = settings.storage.metadata_dir
    if metadata_dir.exists():
        metadata_files = list(metadata_dir.glob('*.json'))
        stats["metadata"]["total_files"] = len(metadata_files)

    # Get state statistics
    state_file = settings.storage.state_dir / "tracking_state.json"
    if state_file.exists():
        try:
            with open(state_file, 'r') as f:
                state_data = json.load(f)
                state_stats = state_data.get('statistics', {})
                stats["state"]["total_processed"] = state_stats.get('total_processed', 0)
                stats["state"]["successful_downloads"] = state_stats.get('successful_downloads', 0)
                stats["state"]["failed_downloads"] = state_stats.get('failed_downloads', 0)
                stats["state"]["last_poll"] = state_stats.get('last_poll_timestamp')
        except Exception as e:
            print(f"Error reading state file: {e}")

    # Get available disk space
    try:
        stat = os.statvfs(str(datasets_dir))
        available_bytes = stat.f_bavail * stat.f_frsize
        stats["storage"]["available_space_gb"] = round(available_bytes / (1024 * 1024 * 1024), 2)
    except Exception:
        pass

    return stats


def get_recent_datasets(limit=20):
    """Get list of recent datasets with metadata."""
    if not settings:
        return []

    datasets = []
    metadata_dir = settings.storage.metadata_dir

    if metadata_dir.exists():
        metadata_files = sorted(
            metadata_dir.glob('*.json'),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )[:limit]

        for metadata_file in metadata_files:
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                    datasets.append({
                        'ref': metadata.get('dataset_ref'),
                        'title': metadata.get('title'),
                        'creator': metadata.get('creator_name'),
                        'size_mb': round(metadata.get('total_bytes', 0) / (1024 * 1024), 2),
                        'status': metadata.get('ingestion_status'),
                        'timestamp': metadata.get('ingestion_timestamp'),
                        'url': metadata.get('url'),
                        'tags': metadata.get('tags', [])[:5],  # First 5 tags
                        'download_count': metadata.get('download_count', 0)
                    })
            except Exception as e:
                print(f"Error reading metadata file {metadata_file}: {e}")

    return datasets


def get_recent_logs(lines=50):
    """Get recent log entries."""
    if not settings:
        return []

    log_file = settings.logging.file
    if not log_file.exists():
        return []

    try:
        with open(log_file, 'r') as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:]
            return [line.strip() for line in recent_lines]
    except Exception as e:
        print(f"Error reading log file: {e}")
        return []


@app.route('/')
def dashboard():
    """Main dashboard page."""
    return render_template('dashboard.html')


@app.route('/api/statistics')
def api_statistics():
    """API endpoint for statistics."""
    return jsonify(get_statistics())


@app.route('/api/datasets')
def api_datasets():
    """API endpoint for recent datasets."""
    limit = int(request.args.get('limit', 20))
    return jsonify(get_recent_datasets(limit))


@app.route('/api/logs')
def api_logs():
    """API endpoint for recent logs."""
    lines = int(request.args.get('lines', 50))
    return jsonify(get_recent_logs(lines))


@app.route('/api/health')
def api_health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })


if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    Path('templates').mkdir(exist_ok=True)

    print("=" * 60)
    print("Kaggle Data Ingestion Engine - Web Dashboard")
    print("=" * 60)
    print(f"Starting dashboard on http://localhost:5000")
    print("Press Ctrl+C to stop")
    print("=" * 60)

    app.run(host='0.0.0.0', port=5000, debug=False)
