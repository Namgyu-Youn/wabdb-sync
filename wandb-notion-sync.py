import os, sys, time
import schedule
import json
import argparse
import logging
from typing import Tuple, List, Dict, Any
from datetime import datetime

import wandb
from notion_client import Client
from oauth2client.service_account import ServiceAccountCredentials

# Related functions
from scripts.logger import load_config, ConfigError, NotionSyncError
from scripts.dataset import process_runs

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

def init_notion_client(config: Dict[str, Any]) -> Client:
    """Initialize Notion client"""
    try:
        notion_token = config.get('NOTION_TOKEN')
        if not notion_token:
            raise NotionSyncError("Notion API token is missing from configuration")

        return Client(auth=notion_token)
    except Exception as e:
        logger.error(f"Failed to initialize Notion client: {e}")
        raise

def fetch_existing_run_ids(notion_client: Client, database_id: str) -> List[str]:
    """Fetch existing run IDs from Notion database"""
    try:
        existing_runs = notion_client.databases.query(
            database_id=database_id,
            filter={}  # You can add more specific filters if needed
        )
        return [
            run['properties']['Run ID']['rich_text'][0]['plain_text']
            for run in existing_runs['results']
            if run['properties'].get('Run ID') and run['properties']['Run ID'].get('rich_text')
        ]
    except Exception as e:
        logger.error(f"Error retrieving existing run IDs: {e}")
        return []

def create_notion_page(notion_client: Client, database_id: str, run_data: Dict[str, Any]) -> None:
    """Create a new page in Notion database for a run"""
    try:
        properties = {
            'Name': {
                'title': [
                    {
                        'text': {
                            'content': run_data.get('id', 'Unnamed Run')
                        }
                    }
                ]
            },
            'Run ID': {
                'rich_text': [
                    {
                        'text': {
                            'content': run_data.get('id', '')
                        }
                    }
                ]
            }
        }

        # Add more properties dynamically
        for key, value in run_data.items():
            if key not in ['id']:
                properties[key.capitalize()] = {
                    'rich_text': [
                        {
                            'text': {
                                'content': str(value)
                            }
                        }
                    ]
                }

        notion_client.pages.create(
            parent={'database_id': database_id},
            properties=properties
        )
        logger.info(f"Created Notion page for run: {run_data.get('id', 'Unknown')}")
    except Exception as e:
        logger.error(f"Error creating Notion page: {e}")

def main() -> None:
    """Main synchronization function"""
    try:
        # Parse arguments
        args = parse_args()

        # Load configuration
        config = load_config('notion', args.config_path)

        # Initialize Notion client
        notion_client = init_notion_client(config)

        # Fetch existing run IDs
        existing_run_ids = fetch_existing_run_ids(notion_client, config['NOTION_DB_ID'])

        # WandB API connection
        wandb_api = wandb.Api()

        # Fetch runs
        runs = wandb_api.runs(
            path=f"{config['TEAM_NAME']}/{config['PROJECT_NAME']}",
            filters={"state": {"$in": ["finished", "killed"]}}
        )

        # Process initial headers if needed
        final_headers = ['Run ID', 'Timestamp', 'User Name']  # Base headers

        # Process runs
        new_runs = process_runs(
            runs,
            existing_run_ids,
            final_headers,
            config.get('USER_NAME', wandb.wandb_user().name)
        )

        # Sync to Notion
        for run in new_runs:
            create_notion_page(notion_client, config['NOTION_DB_ID'], run)

        logger.info(f"Successfully synced {len(new_runs)} new runs")

    except Exception as e:
        logger.error(f"Error in main sync process: {str(e)}")
        time.sleep(60)  # Wait before retrying

if __name__ == "__main__":
    args = parse_args()
    config = load_config('notion', args.config_path)

    logger.info(f"Starting Notion sync process (Schedule: every {args.schedule_time} minutes)")
    logger.info(f"Monitoring runs for user: {args.user_name}")
    logger.info(f"Wandb team name: {config.get('TEAM_NAME', 'N/A')}")
    logger.info(f"Wandb project name: {config.get('PROJECT_NAME', 'N/A')}")

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
