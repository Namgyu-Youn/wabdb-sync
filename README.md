# wandb-sync

Automatically sync your WandB (Weights & Biases) experiments data to Notion or Google Spreadsheet for better collaboration.

## ✨ Features
- Auto-sync experiment data from WandB to Notion/Google Spreadsheet
- Handles NaN values and special characters
- Records only finished or killed experiments
- Prevents duplicate run records

<br/>

**⬇️ Sample ⬇️**

| Run ID | Timestamp | User | Model Type | Batch Size | Epochs | Training Loss | Validation Loss |
|--------|-----------|------|------------|------------|--------|---------------|-----------------|
| 2xk8p9n0 | 2024-11-20 14:30:15 | Namgyu-Youn | ResNet50 | 32 | 100 | 0.245 | 0.312 |
| 2xk8p9n0 | 2024-11-20 14:30:15 | - | ResNet50 | 32 | 100 | 0.245 | 0.312 |
| 7mq2r5v3 | 2024-11-20 15:45:22 | - | ResNet101 | 64 | 150 | 0.198 | 0.287 |

## ➕ Prerequisites
- Python 3.10 or higher
- Docker (optional)
- Poetry (optional)
- notion_client, wandb

## 🚩 Installation

### Option 1: Standard Python Setup

1. Clone the repository
```bash
git clone https://github.com/Namgyu-Youn/wandb-sync.git
cd wandb-sync
```

2. Create and activate virtual environment
```bash
python -m venv env
# On Windows
env\Scripts\activate
# On macOS/Linux
source env/bin/activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

### Option 2: Using Poetry

1. Install Poetry
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

2. Clone and install dependencies
```bash
git clone https://github.com/Namgyu-Youn/wandb-sync.git
cd wandb-sync
poetry install
```

### Option 3: Using Docker

1. Clone the repository
```bash
git clone https://github.com/Namgyu-Youn/wandb-sync.git
cd wandb-sync
```

2. Build and run with Docker Compose
```bash
docker-compose up --build
```


## Notes
- Requires Notion API or Google Sheets API credentials
- Free tier updates every 30 minutes
- For documentation: [Notion API](https://developers.notion.com/reference/database), [Google Sheets API](https://developers.google.com/sheets/api/guides/concepts)