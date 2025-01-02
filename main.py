import os
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass

import wandb
from wandb.apis.public import Run
from notion_client import Client
from notion_client.errors import APIResponseError

from scripts.logger import load_config, NotionSyncError, ConfigError

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

@dataclass
class RunData:
    """Data structure for W&B run information"""
    id: str
    state: str
    user: str
    created_at: datetime
    config: Dict[str, str]
    metrics: Dict[str, str]

class NotionSync:
    def __init__(self, config: Dict[str, str]):
        self.config = config
        self.notion_client = self._init_notion_client()
        self.wandb_api = wandb.Api()

    def _init_notion_client(self) -> Client:
        """Initialize Notion client with error handling"""
        try:
            notion_token = self.config['NOTION_TOKEN']
            return Client(auth=notion_token)
        except KeyError:
            raise ConfigError("Notion API token is missing from configuration")
        except Exception as e:
            raise NotionSyncError(f"Failed to initialize Notion client: {str(e)}")

    def fetch_existing_run_ids(self) -> set[str]:
        """Fetch existing run IDs from Notion database"""
        try:
            existing_runs = self.notion_client.databases.query(
                database_id=self.config['NOTION_DB_ID'],
                filter={}
            )
            return {
                run['properties']['Run ID']['rich_text'][0]['plain_text']
                for run in existing_runs['results']
                if run['properties'].get('Run ID', {}).get('rich_text')
            }
        except APIResponseError as e:
            logger.error(f"Notion API error: {e}")
            raise NotionSyncError(f"Failed to fetch run IDs: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error fetching run IDs: {e}")
            raise

    def get_run_data(self, run: Run) -> RunData:
        """Extract relevant data from a W&B run"""
        config_dict = {
            k: str(v) for k, v in run.config.items()
        }

        metrics_dict = {
            k: str(v) for k, v in run.summary.items()
            if not k.startswith('_')  # Skip internal W&B keys
        }

        return RunData(
            id=run.id,
            state=run.state,
            user=run.user.name,
            created_at=run.created_at,
            config=config_dict,
            metrics=metrics_dict
        )

    def create_notion_page(self, run_data: RunData) -> None:
        """Create a new page in Notion database for a run"""
        try:
            properties = {
                'Name': {
                    'title': [{'text': {'content': run_data.id}}]
                },
                'State': {
                    'rich_text': [{'text': {'content': run_data.state}}]
                },
                'User': {
                    'rich_text': [{'text': {'content': run_data.user}}]
                },
                'Created At': {
                    'date': {
                        'start': run_data.created_at.isoformat()
                    }
                }
            }

            # Add config parameters
            for key, value in run_data.config.items():
                properties[f"Config: {key}"] = {
                    'rich_text': [{'text': {'content': value}}]
                }

            # Add metrics
            for key, value in run_data.metrics.items():
                properties[f"Metric: {key}"] = {
                    'rich_text': [{'text': {'content': value}}]
                }

            self.notion_client.pages.create(
                parent={'database_id': self.config['NOTION_DB_ID']},
                properties=properties
            )
            logger.info(f"Created Notion page for run: {run_data.id}")

        except APIResponseError as e:
            logger.error(f"Notion API error creating page: {e}")
            raise NotionSyncError(f"Failed to create page: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error creating page: {e}")
            raise

    def sync_runs(self) -> None:
        """Synchronize W&B runs to Notion"""
        try:
            existing_run_ids = self.fetch_existing_run_ids()

            runs = self.wandb_api.runs(
                path=f"{self.config['TEAM_NAME']}/{self.config['PROJECT_NAME']}",
                filters={"state": {"$in": ["finished", "killed"]}}
            )

            for run in runs:
                if run.id not in existing_run_ids:
                    run_data = self.get_run_data(run)
                    self.create_notion_page(run_data)

            logger.info("Sync completed successfully")

        except wandb.CommError as e:
            logger.error(f"W&B communication error: {e}")
            raise
        except Exception as e:
            logger.error(f"Sync process failed: {e}")
            raise

def main() -> None:
    """Main entry point"""
    try:
        config = load_config('notion', 'CONFIG.json')
        syncer = NotionSync(config)
        syncer.sync_runs()
    except (ConfigError, NotionSyncError) as e:
        logger.error(f"Configuration or sync error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise

if __name__ == "__main__":
    main()
