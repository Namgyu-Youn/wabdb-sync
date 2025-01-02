import os, sys
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
sys.path.insert(0, root_dir)

from main import NotionSync, RunData

@pytest.fixture
def mock_config():
    return {
        "NOTION_TOKEN": "mock-token",
        "NOTION_DB_ID": "mock-db-id",
        "TEAM_NAME": "mock-team",
        "PROJECT_NAME": "mock-project"
    }

@pytest.fixture
def mock_wandb():
    mock_run = Mock()
    mock_run.id = "test-run"
    mock_run.state = "finished"
    mock_run.user.name = "test-user"
    mock_run.created_at = datetime.now()
    mock_run.config = {"param": "value"}
    mock_run.summary = {"metric": "0.9"}

    mock_api = Mock()
    mock_api.runs.return_value = [mock_run]

    with patch('wandb.Api', return_value=mock_api):
        yield mock_api

@pytest.fixture
def mock_notion():
    mock = MagicMock()
    mock.databases.query.return_value = {
        "results": []
    }
    return mock

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
        assert isinstance(run_ids, set)

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
    with patch('main.NotionSync._init_notion_client', return_value=mock_notion), \
         patch('wandb.Api', return_value=mock_wandb):
        sync = NotionSync(mock_config)
        sync.sync_runs()
        mock_notion.pages.create.assert_called_once()