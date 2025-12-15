# Kaggle Data Ingestion Engine

A Python-based continuous polling service that monitors Kaggle for new datasets, automatically downloads them locally, and stores comprehensive metadata in JSON format.

## Features

- **Automatic Monitoring**: Continuously polls Kaggle for new datasets
- **Complete Downloads**: Downloads all dataset files locally with automatic extraction
- **Metadata Storage**: Stores comprehensive metadata in JSON format
- **Duplicate Prevention**: Tracks processed datasets to avoid re-downloading
- **Robust Error Handling**: Automatic retries with exponential backoff
- **Graceful Shutdown**: Handles interrupts cleanly, saving state
- **Production Ready**: Includes logging, state persistence, and monitoring

## Architecture Principles

This project follows clean architecture principles:

- **Atomic Structure**: Small, focused modules (100-200 lines each)
- **KISS (Keep It Simple)**: Straightforward solutions without over-engineering
- **DRY (Don't Repeat Yourself)**: Centralized, reusable components
- **SOLID Principles**: Single responsibility, dependency inversion, open/closed design

## Project Structure

```
sample_dataIngestionEngine/
├── config/
│   ├── settings.py              # Configuration loader
│   └── config.yaml              # User settings
│
├── src/
│   ├── api/
│   │   ├── kaggle_client.py     # Kaggle API wrapper
│   │   └── rate_limiter.py      # Rate limiting
│   │
│   ├── storage/
│   │   ├── file_store.py        # File operations
│   │   └── metadata_store.py    # JSON metadata
│   │
│   ├── tracking/
│   │   ├── tracker.py           # Duplicate detection
│   │   └── state_manager.py     # State persistence
│   │
│   ├── models/
│   │   └── dataset.py           # Data models
│   │
│   ├── services/
│   │   ├── ingestion_service.py # Main orchestrator
│   │   └── download_service.py  # Download coordination
│   │
│   └── utils/
│       ├── logger.py            # Logging setup
│       └── validators.py        # Validation utilities
│
├── data/
│   ├── datasets/                # Downloaded datasets
│   ├── metadata/                # JSON metadata files
│   └── state/                   # Tracking state
│
├── logs/                        # Application logs
├── main.py                      # Entry point
└── README.md                    # This file
```

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager
- Kaggle account with API credentials

### Setup Steps

1. **Clone or download this repository**

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Get Kaggle API credentials**
   - Go to https://www.kaggle.com/settings/account
   - Click "Create New API Token"
   - Download `kaggle.json` (contains your credentials)

4. **Configure credentials**

   **Option A**: Environment variables (recommended)
   ```bash
   cp .env.example .env
   # Edit .env and add your credentials:
   KAGGLE_USERNAME=your_username
   KAGGLE_KEY=your_api_key
   ```

   **Option B**: Kaggle config file
   ```bash
   mkdir -p ~/.kaggle
   cp /path/to/kaggle.json ~/.kaggle/kaggle.json
   chmod 600 ~/.kaggle/kaggle.json
   ```

5. **Verify configuration**
   ```bash
   # Check that config.yaml exists and is properly configured
   cat config/config.yaml
   ```

## Usage

### Basic Usage

Start the ingestion service:

```bash
python main.py
```

The service will:
1. Authenticate with Kaggle API
2. Start polling for new datasets every hour (configurable)
3. Download new datasets to `data/datasets/`
4. Save metadata to `data/metadata/`
5. Track state in `data/state/`
6. Log to console and `logs/kaggle_ingestion.log`

Press `Ctrl+C` to stop gracefully.

### Configuration

Edit `config/config.yaml` to customize behavior:

```yaml
# Polling interval (seconds)
polling:
  interval_seconds: 3600  # Poll every hour

# Maximum datasets to fetch per poll
kaggle:
  max_datasets_per_poll: 100

# Storage paths
storage:
  datasets_dir: "./data/datasets"
  metadata_dir: "./data/metadata"
  state_dir: "./data/state"

# Logging level
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR
```

## Data Organization

### Downloaded Datasets

```
data/datasets/
├── username1/
│   ├── dataset-name-1/
│   │   ├── file1.csv
│   │   └── file2.json
│   └── dataset-name-2/
│       └── data.csv
```

### Metadata Files

```
data/metadata/
├── username1__dataset-name-1.json
├── username1__dataset-name-2.json
```

Example metadata structure:
```json
{
  "dataset_ref": "username/dataset-name",
  "title": "Dataset Title",
  "creator_name": "username",
  "total_bytes": 1048576,
  "url": "https://www.kaggle.com/datasets/...",
  "last_updated": "2025-12-15T10:30:00Z",
  "download_count": 12345,
  "tags": ["finance", "business"],
  "local_path": "/path/to/datasets/username/dataset-name",
  "ingestion_status": "completed"
}
```

### State Tracking

```
data/state/
├── tracking_state.json          # Current state
└── tracking_state.json.backup   # Previous backup
```

## Running as a Service

### Linux (systemd)

Create `/etc/systemd/system/kaggle-ingestion.service`:

```ini
[Unit]
Description=Kaggle Data Ingestion Engine
After=network.target

[Service]
Type=simple
User=mahad
WorkingDirectory=/home/mahad/PROJECTS/BimProjects/sample_dataIngestionEngine
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=60
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable kaggle-ingestion
sudo systemctl start kaggle-ingestion
sudo systemctl status kaggle-ingestion

# View logs
journalctl -u kaggle-ingestion -f
```

## Monitoring

### Logs

Logs are written to:
- **Console**: INFO level and above
- **File**: `logs/kaggle_ingestion.log` (DEBUG level, rotated at 10MB)

Log format:
```
2025-12-15 11:30:45 [INFO] [ingestion_service] Starting poll cycle #42
2025-12-15 11:30:46 [INFO] [kaggle_client] Fetched 15 datasets from API
2025-12-15 11:30:50 [INFO] [download_service] Downloaded: user1/dataset1
```

### Viewing Real-time Logs

```bash
tail -f logs/kaggle_ingestion.log
```

### Statistics

The service tracks:
- Total datasets processed
- Successful/failed downloads
- Disk usage
- API rate limiting stats

## Troubleshooting

### Authentication Errors

```
ERROR: Kaggle API authentication failed
```

**Solution**: Check that `KAGGLE_USERNAME` and `KAGGLE_KEY` are correctly set in `.env`

### Rate Limiting

```
WARNING: Rate limit hit! Waiting 60 seconds...
```

**Solution**: The service automatically handles rate limits with exponential backoff. No action needed.

### Disk Space Issues

```
ERROR: Insufficient disk space
```

**Solution**: Free up disk space or adjust storage paths in `config/config.yaml`

### Failed Downloads

```
ERROR: Download failed after retries
```

**Solution**: Check network connectivity. The service will skip the dataset and continue. Check `logs/` for details.

## Development

### Code Structure

The codebase follows SOLID principles:

- **Single Responsibility**: Each class has one purpose
  - `KaggleClient`: Only handles API communication
  - `FileStore`: Only manages file operations
  - `Tracker`: Only tracks processed datasets

- **Dependency Inversion**: Components depend on abstractions
  - Services receive dependencies via constructor injection
  - Easy to test and swap implementations

- **Open/Closed**: Extensible without modification
  - Add new features via dependency injection
  - Example: Add filtering by creating `FilterService`

### Adding New Features

**Example: Add email notifications**

1. Create `src/services/notification_service.py`
2. Inject into `IngestionService.__init__()`
3. Call after successful downloads
4. No modification to existing code needed!

## Resource Requirements

### Disk Space

- **Metadata**: ~5KB per dataset
- **State files**: ~1MB for 100K datasets
- **Datasets**: Variable (plan for 1TB+ in production)

### Memory

- Typical usage: ~200MB
- Scales well to hundreds of thousands of datasets

### Network

- API calls: Minimal (~100KB per poll)
- Downloads: Varies by dataset size (10-50GB/day typical)

## License

This project is provided as-is for educational and personal use.

## Support

For issues or questions:
1. Check logs in `logs/kaggle_ingestion.log`
2. Review configuration in `config/config.yaml`
3. Verify Kaggle API credentials are valid

## Acknowledgments

- Uses the official [Kaggle API](https://github.com/Kaggle/kaggle-api)
- Built following clean architecture principles
- Designed for reliability and maintainability
