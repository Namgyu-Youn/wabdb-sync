import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from main import NotionSync, RunData
from scripts.logger import NotionSyncError

@pytest.fixture
def mock_config():
    return {
        "NOTION_TOKEN": "mock-token",
        "NOTION_DB_ID": "mock-db-id",
        "TEAM_NAME": "mock-team",
        "PROJECT_NAME": "mock-project"
    }

@pytest.fixture
def mock_notion_client(monkeypatch):
    mock_client = Mock()
    mock_client.databases.query.return_value = {
        "results": [{"properties": {"Run ID": {"rich_text": [{"plain_text": "existing-run"}]}}}]
    }
    mock_client.pages.create.return_value = {"id": "test-page-id"}

    monkeypatch.setattr("notion_client.Client", Mock(return_value=mock_client))
    return mock_client

@pytest.fixture
def mock_wandb_api(monkeypatch):
    mock_api = Mock()
    mock_run = Mock()
    mock_run.id = "test-run"
    mock_run.state = "finished"
    mock_run.user.name = "test-user"
    mock_run.created_at = datetime.now()
    mock_run.config = {"param": "value"}
    mock_run.summary = {"metric": "0.9"}
    mock_api.runs.return_value = [mock_run]

    monkeypatch.setattr("wandb.Api", Mock(return_value=mock_api))
    return mock_api

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

def test_fetch_existing_run_ids(mock_notion_client, mock_wandb_api, mock_config):
    sync = NotionSync(mock_config)
    run_ids = sync.fetch_existing_run_ids()
    assert "existing-run" in run_ids

def test_create_notion_page(mock_notion_client, mock_wandb_api, mock_config):
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
    mock_notion_client.pages.create.assert_called_once()

def test_sync_runs_process(mock_notion_client, mock_wandb_api, mock_config):
    sync = NotionSync(mock_config)
    sync.sync_runs()
    mock_notion_client.pages.create.assert_called_once()