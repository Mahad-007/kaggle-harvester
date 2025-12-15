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

# Create necessary directories on startup
def initialize_directories():
    """Create necessary directories if they don't exist."""
    dirs = [
        Path('data/datasets'),
        Path('data/metadata'),
        Path('data/state'),
        Path('logs'),
        Path('templates')
    ]
    for directory in dirs:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"✓ Directory ensured: {directory}")

# Initialize directories
try:
    initialize_directories()
except Exception as e:
    print(f"Warning: Could not create directories: {e}")

# Load settings
try:
    settings = Settings.load()
    print("✓ Settings loaded successfully")
    if settings:
        settings.validate()
        print("✓ Settings validated successfully")
except Exception as e:
    print(f"Warning: Could not load settings: {e}")
    import traceback
    traceback.print_exc()
    settings = None

# Print startup message
print("=" * 60)
print("Kaggle Data Ingestion Engine - Web Dashboard")
print("=" * 60)
print(f"✓ Flask app initialized")
print(f"✓ Settings status: {'Loaded' if settings else 'Not loaded (will use limited functionality)'}")
print("=" * 60)


def get_statistics():
    """Get current statistics from storage and state files."""
    if not settings:
        return {"error": "Settings not loaded"}

    stats = {
        "datasets": {
            "total": 0,
            "total_size_mb": 0,
            "total_size_gb": 0,
            "by_platform": {
                "kaggle": 0,
                "huggingface": 0
            }
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

    # Get metadata statistics and count by platform
    metadata_dir = settings.storage.metadata_dir
    if metadata_dir.exists():
        metadata_files = list(metadata_dir.glob('*.json'))
        stats["metadata"]["total_files"] = len(metadata_files)

        # Count datasets by platform
        for metadata_file in metadata_files:
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                    platform = metadata.get('platform', 'kaggle')
                    if platform in stats["datasets"]["by_platform"]:
                        stats["datasets"]["by_platform"][platform] += 1
            except Exception:
                pass  # Skip files that can't be read

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
                        'platform': metadata.get('platform', 'kaggle'),  # Include platform
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
    try:
        print("Rendering dashboard...")
        return render_template('dashboard.html')
    except Exception as e:
        print(f"Error rendering dashboard: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': 'Failed to render dashboard',
            'message': str(e)
        }), 500


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


@app.route('/api/platform', methods=['GET'])
def get_platform():
    """Get current active platform."""
    if not settings:
        return jsonify({'error': 'Settings not loaded'}), 500

    return jsonify({
        'platform': settings.platform.active,
        'available_platforms': ['kaggle', 'huggingface']
    })


@app.route('/api/platform', methods=['POST'])
def set_platform():
    """Update active platform in config file and optionally restart engine."""
    import subprocess
    import signal
    import time

    try:
        data = request.get_json()
        new_platform = data.get('platform', 'kaggle')
        auto_restart = data.get('auto_restart', False)

        # Validate platform
        if new_platform not in ['kaggle', 'huggingface']:
            return jsonify({'error': 'Invalid platform. Must be kaggle or huggingface'}), 400

        # Read current config
        config_path = Path('config/config.yaml')
        with open(config_path, 'r') as f:
            import yaml
            config = yaml.safe_load(f)

        # Check if platform is already active
        if config['platform']['active'] == new_platform:
            return jsonify({
                'success': True,
                'platform': new_platform,
                'message': f'Platform is already set to {new_platform}',
                'restarted': False
            })

        # Update platform
        config['platform']['active'] = new_platform

        # Write back
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        message = f'Platform switched to {new_platform}'
        restarted = False

        # Auto-restart if requested
        if auto_restart:
            try:
                # Get current PID
                result = subprocess.run(
                    ['pgrep', '-f', 'python3 main.py'],
                    capture_output=True,
                    text=True
                )

                if result.stdout.strip():
                    pid = int(result.stdout.strip())
                    print(f"Auto-restarting engine (PID: {pid}) for platform switch to {new_platform}")

                    # Send SIGTERM for graceful shutdown
                    try:
                        os.kill(pid, signal.SIGTERM)
                        # Wait up to 5 seconds for graceful shutdown
                        for _ in range(10):
                            time.sleep(0.5)
                            check = subprocess.run(
                                ['pgrep', '-f', 'python3 main.py'],
                                capture_output=True,
                                text=True
                            )
                            if not check.stdout.strip():
                                break
                        else:
                            # Force kill if still running
                            os.kill(pid, signal.SIGKILL)
                            time.sleep(1)
                    except ProcessLookupError:
                        pass  # Process already stopped

                # Start new engine process
                print(f"Starting engine with {new_platform} platform...")
                subprocess.Popen(
                    ['python3', 'main.py'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )

                time.sleep(2)

                # Verify it started
                verify = subprocess.run(
                    ['pgrep', '-f', 'python3 main.py'],
                    capture_output=True,
                    text=True
                )

                if verify.stdout.strip():
                    message = f'Platform switched to {new_platform} and engine restarted successfully'
                    restarted = True
                else:
                    message = f'Platform switched to {new_platform} but engine failed to restart'
            except Exception as restart_error:
                print(f"Error during auto-restart: {restart_error}")
                message = f'Platform switched to {new_platform} but auto-restart failed: {str(restart_error)}'

        return jsonify({
            'success': True,
            'platform': new_platform,
            'message': message,
            'restarted': restarted
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/config/polling-interval', methods=['GET'])
def get_polling_interval():
    """Get current polling interval."""
    if not settings:
        return jsonify({'error': 'Settings not loaded'}), 500

    return jsonify({
        'interval_seconds': settings.polling.interval_seconds
    })


@app.route('/api/config/polling-interval', methods=['POST'])
def update_polling_interval():
    """Update polling interval in config file."""
    try:
        data = request.get_json()
        new_interval = int(data.get('interval_seconds', 60))

        # Validate interval (between 10 seconds and 24 hours)
        if new_interval < 10 or new_interval > 86400:
            return jsonify({'error': 'Interval must be between 10 and 86400 seconds'}), 400

        # Read current config file
        config_path = Path('config/config.yaml')
        with open(config_path, 'r') as f:
            import yaml
            config = yaml.safe_load(f)

        # Update polling interval
        config['polling']['interval_seconds'] = new_interval

        # Write back to file
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        return jsonify({
            'success': True,
            'interval_seconds': new_interval,
            'message': 'Polling interval updated. Restart the engine for changes to take effect.'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/engine/status')
def engine_status():
    """Check if the ingestion engine is running."""
    import subprocess
    try:
        result = subprocess.run(
            ['pgrep', '-f', 'python3 main.py'],
            capture_output=True,
            text=True
        )
        is_running = bool(result.stdout.strip())

        return jsonify({
            'running': is_running,
            'pid': result.stdout.strip() if is_running else None
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/engine/stop', methods=['POST'])
def stop_engine():
    """Stop the ingestion engine."""
    import subprocess
    import signal
    import time

    try:
        # Get current PID
        result = subprocess.run(
            ['pgrep', '-f', 'python3 main.py'],
            capture_output=True,
            text=True
        )

        if not result.stdout.strip():
            return jsonify({
                'success': False,
                'error': 'Engine is not running'
            }), 400

        pid = int(result.stdout.strip())
        print(f"Stopping engine with PID: {pid}")

        # Send SIGTERM for graceful shutdown
        try:
            os.kill(pid, signal.SIGTERM)
            # Wait up to 5 seconds for graceful shutdown
            for _ in range(10):
                time.sleep(0.5)
                check = subprocess.run(
                    ['pgrep', '-f', 'python3 main.py'],
                    capture_output=True,
                    text=True
                )
                if not check.stdout.strip():
                    break
            else:
                # Force kill if still running
                print(f"Force stopping engine with PID: {pid}")
                os.kill(pid, signal.SIGKILL)
                time.sleep(1)
        except ProcessLookupError:
            pass  # Process already stopped

        # Verify it stopped
        verify = subprocess.run(
            ['pgrep', '-f', 'python3 main.py'],
            capture_output=True,
            text=True
        )

        if not verify.stdout.strip():
            return jsonify({
                'success': True,
                'message': 'Engine stopped successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to stop engine'
            }), 500

    except Exception as e:
        print(f"Error stopping engine: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/engine/restart', methods=['POST'])
def restart_engine():
    """Restart the ingestion engine."""
    import subprocess
    import signal
    import time

    try:
        # Get current PID
        result = subprocess.run(
            ['pgrep', '-f', 'python3 main.py'],
            capture_output=True,
            text=True
        )

        if result.stdout.strip():
            pid = int(result.stdout.strip())
            print(f"Stopping engine with PID: {pid}")

            # Send SIGTERM for graceful shutdown
            try:
                os.kill(pid, signal.SIGTERM)
                # Wait up to 5 seconds for graceful shutdown
                for _ in range(10):
                    time.sleep(0.5)
                    check = subprocess.run(
                        ['pgrep', '-f', 'python3 main.py'],
                        capture_output=True,
                        text=True
                    )
                    if not check.stdout.strip():
                        break
                else:
                    # Force kill if still running
                    print(f"Force stopping engine with PID: {pid}")
                    os.kill(pid, signal.SIGKILL)
                    time.sleep(1)
            except ProcessLookupError:
                pass  # Process already stopped

        # Start new engine process
        print("Starting new engine process...")
        subprocess.Popen(
            ['python3', 'main.py'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )

        # Wait a moment for the process to start
        time.sleep(2)

        # Verify it started
        verify = subprocess.run(
            ['pgrep', '-f', 'python3 main.py'],
            capture_output=True,
            text=True
        )

        if verify.stdout.strip():
            return jsonify({
                'success': True,
                'message': 'Engine restarted successfully',
                'pid': verify.stdout.strip()
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Engine failed to start'
            }), 500

    except Exception as e:
        print(f"Error restarting engine: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    Path('templates').mkdir(exist_ok=True)

    # Get port from environment variable or default to 5000
    port = int(os.getenv('PORT', 5000))

    print("=" * 60)
    print("Kaggle Data Ingestion Engine - Web Dashboard")
    print("=" * 60)
    print(f"Starting dashboard on http://localhost:{port}")
    print("Press Ctrl+C to stop")
    print("=" * 60)

    app.run(host='0.0.0.0', port=port, debug=False)
