import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from main import NotionSync, RunData
from scripts.logger import ConfigError, NotionSyncError

@pytest.fixture
def mock_notion_client():
    client = Mock()
    client.databases.query.return_value = {
        "results": [{"properties": {"Run ID": {"rich_text": [{"plain_text": "test-run-1"}]}}}]
    }
    client.pages.create.return_value = {"id": "test-page-id"}
    return client

@pytest.fixture
def mock_wandb_api():
    api = Mock()
    run = Mock()
    run.id = "test-run-2"
    run.state = "finished"
    run.user.name = "test-user"
    run.created_at = datetime.now()
    run.config = {"learning_rate": 0.001}
    run.summary = {"accuracy": 0.95}
    api.runs.return_value = [run]
    return api

def test_notion_sync_initialization():
    with patch('notion_client.Client') as mock_client, \
         patch('wandb.Api') as mock_api:
        sync = NotionSync({"NOTION_TOKEN": "test"})
        assert sync is not None

def test_fetch_existing_runs(mock_notion_client):
    with patch('notion_client.Client', return_value=mock_notion_client):
        sync = NotionSync({"NOTION_TOKEN": "test"})
        runs = sync.fetch_existing_run_ids()
        assert "test-run-1" in runs

def test_sync_runs_integration(mock_notion_client, mock_wandb_api):
    with patch('notion_client.Client', return_value=mock_notion_client), \
         patch('wandb.Api', return_value=mock_wandb_api):
        sync = NotionSync({
            "NOTION_TOKEN": "test",
            "TEAM_NAME": "test",
            "PROJECT_NAME": "test"
        })
        sync.sync_runs()
        mock_notion_client.pages.create.assert_called_once()

def test_run_data():
    data = RunData(
        id="test",
        state="finished",
        user="test",
        created_at=datetime.now(),
        config={"test": "value"},
        metrics={"accuracy": "0.9"}
    )
    assert data.id == "test"
    assert "test" in data.config