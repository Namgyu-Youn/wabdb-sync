import os
import json
import logging
from typing import List, Dict, Any

import wandb
from notion_client import Client

from scripts.logger import load_config, NotionSyncError

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
            filter={}
        )
        return [
            run['properties']['Run ID']['rich_text'][0]['plain_text']
            for run in existing_runs['results']
            if run['properties'].get('Run ID', {}).get('rich_text')
        ]
    except Exception as e:
        logger.error(f"Error retrieving existing run IDs: {e}")
        return []

def get_run_data(run: Any) -> Dict[str, Any]:
    """Extract all available data from a WandB run"""
    run_data = {
        'id': run.id,
        'state': run.state,
        'user': run.user.name,
        'created_at': run.created_at.strftime("%Y-%m-%d %H:%M:%S")
    }

    # Add all config parameters
    for key, value in run.config.items():
        run_data[f"config_{key}"] = str(value)

    # Add all summary metrics
    for key, value in run.summary.items():
        if not key.startswith('_'):  # Skip internal WandB keys
            run_data[f"metric_{key}"] = str(value)

    return run_data

def create_notion_page(notion_client: Client, database_id: str, run_data: Dict[str, Any]) -> None:
    """Create a new page in Notion database for a run"""
    try:
        properties = {
            'Name': {
                'title': [{'text': {'content': run_data['id']}}]
            }
        }

        # Add all run data as properties
        for key, value in run_data.items():
            if key != 'id':  # Skip ID as it's already used in Name
                properties[key.replace('_', ' ').title()] = {
                    'rich_text': [{'text': {'content': str(value)}}]
                }

        notion_client.pages.create(
            parent={'database_id': database_id},
            properties=properties
        )
        logger.info(f"Created Notion page for run: {run_data['id']}")
    except Exception as e:
        logger.error(f"Error creating Notion page: {e}")

def main() -> None:
    """Main synchronization function"""
    try:
        # Load configuration
        config = load_config('notion', 'CONFIG.json')

        # Initialize Notion client
        notion_client = init_notion_client(config)

        # Fetch existing run IDs
        existing_run_ids = fetch_existing_run_ids(notion_client, config['NOTION_DB_ID'])

        # Initialize WandB API
        wandb_api = wandb.Api()

        # Fetch runs
        runs = wandb_api.runs(
            path=f"{config['TEAM_NAME']}/{config['PROJECT_NAME']}",
            filters={"state": {"$in": ["finished", "killed"]}}
        )

        # Process each run
        for run in runs:
            if run.id not in existing_run_ids:
                run_data = get_run_data(run)
                create_notion_page(notion_client, config['NOTION_DB_ID'], run_data)

        logger.info("Sync completed successfully")

    except Exception as e:
        logger.error(f"Error in sync process: {str(e)}")

if __name__ == "__main__":
    main()
