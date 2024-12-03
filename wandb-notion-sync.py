import math
import os, sys, time
import schedule
import json
import argparse
import logging
from typing import Tuple, List, Dict, Any
from datetime import datetime

import wandb
from notion_client import Client
from notion_client.errors import NotionAPIError

# Related function
from scripts.logger import load_config, NotionSyncError
from scripts.dataset import get_run_value, process_runs

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('wandb_notion_sync.log')
    ]
)
logger = logging.getLogger(__name__)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Sync WandB runs to Notion Database')
    parser.add_argument('--schedule_time', type=int, default=30,
                       help='Schedule interval in minutes (default: 30)')
    parser.add_argument('--user_name', type=str, default='ng-youn',
                       help='User name for tracking WandB runs')
    parser.add_argument('--config_path', type=str, default='CONFIG.json',
                       help='Path to configuration file')
    return parser.parse_args()

def init_notion_client(config: Dict[str, Any]) -> Tuple[Client, str]:
    """Initialize Notion client and validate database"""
    try:
        # Initialize Notion client
        notion_client = Client(auth=config['NOTION_TOKEN'])

        # Verify database exists
        try:
            notion_client.databases.retrieve(database_id=config['NOTION_DATABASE_ID'])
        except NotionAPIError as db_error:
            logger.error(f"Error accessing Notion database: {db_error}")
            raise NotionSyncError(f"Cannot access Notion database: {config['NOTION_DATABASE_ID']}")

        return notion_client, config['NOTION_DATABASE_ID']
    except Exception as e:
        logger.error(f"Notion client initialization error: {e}")
        raise NotionSyncError(f"Failed to initialize Notion client: {str(e)}")

def convert_to_notion_properties(run: Any, config: Dict[str, Any], user_name: str) -> Dict[str, Any]:
    """Convert run data to Notion database properties"""
    properties = {
        "Run ID": {"title": [{"text": {"content": run.id}}]},
        "Timestamp": {"date": {"start": datetime.fromtimestamp(run.summary.get("_timestamp", time.time())).isoformat()}},
        "User": {"rich_text": [{"text": {"content": user_name}}]},
        "State": {"status": {"name": run.state}}
    }

    # Add additional properties from config
    for key in config.get('FIXED_HEADERS', [])[3:]:
        value = get_run_value(run, key)
        if value is not None:
            # Determine Notion property type based on value type
            if isinstance(value, (int, float)):
                properties[key] = {"number": value}
            elif isinstance(value, bool):
                properties[key] = {"checkbox": value}
            else:
                properties[key] = {"rich_text": [{"text": {"content": str(value)}}]}

    return properties

def sync_to_notion(notion_client: Client, database_id: str, runs: List[Dict[str, Any]]) -> None:
    """Sync runs to Notion database"""
    try:
        for run in runs:
            notion_client.pages.create(
                parent={"database_id": database_id},
                properties=run
            )
            time.sleep(0.5)  # Rate limiting
        logger.info(f"Successfully added {len(runs)} new runs to Notion")
    except NotionAPIError as e:
        logger.error(f"Notion API error during sync: {e}")
        raise NotionSyncError(f"Failed to sync runs to Notion: {str(e)}")

def fetch_existing_run_ids(notion_client: Client, database_id: str) -> List[str]:
    """Fetch existing run IDs from Notion database"""
    try:
        query_response = notion_client.databases.query(
            database_id=database_id,
            filter={"property": "Run ID", "title": {"is_not_empty": True}}
        )
        return [page['properties']['Run ID']['title'][0]['text']['content']
                for page in query_response['results']]
    except Exception as e:
        logger.error(f"Error fetching existing run IDs: {e}")
        return []

def main(args: argparse.Namespace) -> None:
    try:
        # Load configuration
        config = load_config('notion', args.config_path)

        # Initialize Notion client
        notion_client, database_id = init_notion_client(config)

        # Initialize WandB API
        api = wandb.Api()

        # Fetch existing run IDs
        existing_run_ids = fetch_existing_run_ids(notion_client, database_id)

        # Fetch runs
        runs = api.runs(f"{config['TEAM_NAME']}/{config['PROJECT_NAME']}")

        # Process runs
        new_runs = process_runs(runs, existing_run_ids, config, args.user_name)

        # Sync to Notion
        if new_runs:
            sync_to_notion(notion_client, database_id, new_runs)
        else:
            logger.info("No new runs to add")

    except Exception as e:
        logger.error(f"Error in main sync process: {str(e)}")
        raise

if __name__ == "__main__":
    args = parse_args()
    config = load_config('notion', args.config_path)

    logger.info(f"Starting Notion sync process (Schedule: every {args.schedule_time} minutes)")
    logger.info(f"Monitoring runs for user: {args.user_name}")
    logger.info(f"Wandb team name: {config.get('TEAM_NAME', 'N/A')}")
    logger.info(f"Wandb project name: {config.get('PROJECT_NAME', 'N/A')}")

    schedule.every(args.schedule_time).minutes.do(lambda: main(args))

    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Sync process stopped by user")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            time.sleep(60)  # Retry 1 min later if error occurs
