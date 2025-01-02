import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import pytest

from main import NotionSync, RunData
from notion_client.errors import APIResponseError

@pytest.fixture
def mock_config():
   return {
       "NOTION_TOKEN": "mock-token",
       "NOTION_DB_ID": "mock-db-id",
       "TEAM_NAME": "mock-team",
       "PROJECT_NAME": "mock-project"
   }

@pytest.fixture
def mock_notion():
   mock = MagicMock()
   mock.databases.query.return_value = {
       "results": [{"properties": {"Run ID": {"rich_text": [{"plain_text": "existing-run"}]}}}]
   }
   return mock

@pytest.fixture
def mock_wandb():
   with patch('wandb.Api'):
       yield Mock()

def test_run_data_creation():
   data = RunData(
       id="test-id",
       state="finished",
       user="test-user",
       created_at=datetime.now(),
       config={"test": "value"},
       metrics={"accuracy": "0.95"}
   )
   assert data.id == "test-id"

def test_fetch_existing_run_ids(mock_notion, mock_wandb, mock_config):
   with patch.object(NotionSync, '_init_notion_client', return_value=mock_notion):
       sync = NotionSync(mock_config)
       run_ids = sync.fetch_existing_run_ids()
       assert "existing-run" in run_ids

def test_create_notion_page(mock_notion, mock_wandb, mock_config):
   with patch.object(NotionSync, '_init_notion_client', return_value=mock_notion):
       sync = NotionSync(mock_config)
       run_data = RunData(
           id="test-id",
           state="finished",
           user="test-user",
           created_at=datetime.now(),
           config={"param": "value"},
           metrics={"metric": "0.9"}
       )
       sync.create_notion_page(run_data)
       mock_notion.pages.create.assert_called_once()

def test_sync_runs_process(mock_notion, mock_wandb, mock_config):
   with patch.object(NotionSync, '_init_notion_client', return_value=mock_notion):
       sync = NotionSync(mock_config)
       sync.sync_runs()
       mock_notion.pages.create.assert_called_once()