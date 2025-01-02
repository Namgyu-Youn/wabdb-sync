import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from main import NotionSync, RunData
from scripts.logger import ConfigError, NotionSyncError

@pytest.fixture
def mock_config():
   return {
       "NOTION_TOKEN": "mock-token",
       "NOTION_DB_ID": "mock-db-id",
       "TEAM_NAME": "mock-team",
       "PROJECT_NAME": "mock-project"
   }

@pytest.fixture
def mock_wandb_run():
   run = Mock()
   run.id = "test-run-id"
   run.state = "finished"
   run.user.name = "test-user"
   run.created_at = datetime.now()
   run.config = {"learning_rate": 0.001}
   run.summary = {"accuracy": 0.95}
   return run

@pytest.fixture
def mock_services():
   with patch('wandb.Api') as wandb_mock, \
        patch('notion_client.Client') as notion_mock:

       # Mock Notion responses
       notion_mock.return_value.databases.query.return_value = {
           "results": [
               {"properties": {"Run ID": {"rich_text": [{"plain_text": "existing-run"}]}}}
           ]
       }

       # Mock WandB responses
       wandb_mock.return_value.runs.return_value = [mock_wandb_run]

       yield wandb_mock, notion_mock

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
   assert data.state == "finished"
   assert data.config["test"] == "value"
   assert data.metrics["accuracy"] == "0.95"

def test_notion_sync_initialization(mock_services, mock_config):
   sync = NotionSync(mock_config)
   assert sync is not None
   assert sync.config == mock_config

def test_notion_sync_initialization_error():
   with pytest.raises(ConfigError):
       NotionSync({})

def test_fetch_existing_run_ids(mock_services, mock_config):
   sync = NotionSync(mock_config)
   run_ids = sync.fetch_existing_run_ids()
   assert "existing-run" in run_ids

def test_create_notion_page(mock_services, mock_config):
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
   mock_services[1].return_value.pages.create.assert_called_once()

def test_sync_runs_process(mock_services, mock_config):
   sync = NotionSync(mock_config)
   sync.sync_runs()
   mock_services[1].return_value.pages.create.assert_called_once()

def test_sync_runs_error_handling(mock_services, mock_config):
   mock_services[1].return_value.databases.query.side_effect = Exception("Test error")
   sync = NotionSync(mock_config)
   with pytest.raises(Exception):
       sync.sync_runs()