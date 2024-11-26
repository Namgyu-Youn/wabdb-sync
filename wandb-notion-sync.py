import math
import os
from datetime import datetime
import schedule
import json
import time
import argparse
import logging
from typing import Tuple, List, Dict, Any

import wandb
from notion_client import Client

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('wandb_sync.log')
    ]
)
logger = logging.getLogger(__name__)

class ConfigError(Exception):
    """Configuration related errors"""
    pass

class NotionError(Exception):
    """Notion related errors"""
    pass

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Sync WandB runs to Notion')
    parser.add_argument('--schedule_time', type=int, default=30,
                       help='Schedule interval in minutes (default: 30)')
    parser.add_argument('--user_name', type=str, default='Anonymous',
                       help='User name for tracking WandB runs')
    parser.add_argument('--database_id', type=str, required=True,
                       help='Notion database ID to sync with')
    parser.add_argument('--config_path', type=str, default='config.json',
                       help='Path to configuration file')
    return parser.parse_args()

def get_wandb_project_info() -> Tuple[str, str]:
    """현재 실행 중인 WandB 프로젝트 정보 가져오기"""
    current_run = wandb.run
    if current_run is None:
        raise ConfigError("No active WandB run found")

    project_name = current_run.project
    entity_name = current_run.entity

    if not project_name or not entity_name:
        raise ConfigError("Failed to get project or team name from WandB run")

    return entity_name, project_name

def load_config(config_path: str) -> Dict[str, Any]:
    """설정 파일 로드 및 검증"""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)

        required_keys = ['NOTION_TOKEN', 'FIXED_HEADERS']
        missing_keys = [key for key in required_keys if key not in config]
        if missing_keys:
            raise ConfigError(f"Missing required keys in config: {missing_keys}")

        try:
            team_name, project_name = get_wandb_project_info()
            config['TEAM_NAME'] = team_name
            config['PROJECT_NAME'] = project_name
            logger.info(f"Using WandB project: {project_name} from team: {team_name}")
        except ConfigError as e:
            raise ConfigError(f"Failed to get WandB project info: {str(e)}")

        return config
    except FileNotFoundError:
        raise ConfigError(f"Config file not found: {config_path}")
    except json.JSONDecodeError:
        raise ConfigError(f"Invalid JSON in config file: {config_path}")

def init_notion(database_id: str, config: Dict[str, Any]) -> Tuple[Client, wandb.Api]:
    """Notion 클라이언트 초기화 및 WandB API 연결"""
    try:
        notion = Client(auth=config['NOTION_TOKEN'])

        # 데이터베이스 존재 여부 확인
        try:
            notion.databases.retrieve(database_id)
        except Exception as e:
            raise NotionError(f"Failed to access Notion database: {str(e)}")

        # WandB API 연결
        api = wandb.Api()

        return notion, api

    except Exception as e:
        raise NotionError(f"Failed to initialize Notion client: {str(e)}")

def get_timestamp(run: Any) -> str:
    """타임스탬프 추출"""
    try:
        return (datetime.fromtimestamp(run.summary["_timestamp"])
                .strftime("%Y-%m-%d %H:%M:%S")
                if "_timestamp" in run.summary else "")
    except Exception:
        return ""

def get_run_value(run: Any, key: str) -> str:
    """run에서 값 추출"""
    try:
        if key in run.config:
            return str(run.config[key])
        elif key in run.summary:
            return str(run.summary[key])
        return ""
    except Exception:
        return ""

def create_notion_properties(run_data: List[str], headers: List[str]) -> Dict[str, Any]:
    """Notion 속성 생성"""
    properties = {}

    for header, value in zip(headers, run_data):
        # Run ID는 제목으로 사용
        if header == "Run ID":
            properties["Name"] = {"title": [{"text": {"content": value}}]}
        elif header == "Timestamp":
            if value:
                properties[header] = {"date": {"start": value}}
        else:
            properties[header] = {"rich_text": [{"text": {"content": value}}]}

    return properties

def process_runs(runs: List[Any], existing_run_ids: List[str],
                final_headers: List[str], user_name: str) -> List[Dict[str, Any]]:
    """WandB runs 처리"""
    pages_to_create = []

    for run in runs:
        if run.state == "finished" and run.id not in existing_run_ids:
            if run.user.name == user_name:
                try:
                    row_data = [
                        run.id,
                        get_timestamp(run),
                        run.user.name,
                    ]
                    # 추가 필드 처리
                    for key in final_headers[3:]:
                        value = get_run_value(run, key)
                        row_data.append(value)

                    properties = create_notion_properties(row_data, final_headers)
                    pages_to_create.append(properties)
                except Exception as e:
                    logger.error(f"Error processing run {run.id}: {str(e)}")
                    continue

    return pages_to_create

def sync_data(notion: Client, database_id: str, pages: List[Dict[str, Any]]) -> None:
    """Data sync to Notion"""
    try:
        for page_properties in pages:
            notion.pages.create(
                parent={"database_id": database_id},
                properties=page_properties
            )
            time.sleep(0.5)  # Notion API 제한 방지
    except Exception as e:
        raise NotionError(f"Failed to sync data: {str(e)}")

def get_existing_run_ids(notion: Client, database_id: str) -> List[str]:
    """Notion 데이터베이스에서 기존 Run ID 가져오기"""
    try:
        results = []
        query = notion.databases.query(database_id=database_id)

        for page in query["results"]:
            title = page["properties"]["Name"]["title"]
            if title:
                results.append(title[0]["text"]["content"])

        return results
    except Exception as e:
        raise NotionError(f"Failed to get existing run IDs: {str(e)}")

def main(args: argparse.Namespace) -> None:
    try:
        config = load_config(args.config_path)
        notion, api = init_notion(args.database_id, config)

        runs = api.runs(f"{config['TEAM_NAME']}/{config['PROJECT_NAME']}")
        existing_run_ids = get_existing_run_ids(notion, args.database_id)

        new_pages = process_runs(
            runs, existing_run_ids, config['FIXED_HEADERS'],
            args.user_name
        )

        if new_pages:
            sync_data(notion, args.database_id, new_pages)
            logger.info(f"Successfully added {len(new_pages)} new runs")
        else:
            logger.info("No new runs to add")

    except Exception as e:
        logger.error(f"Error in main sync process: {str(e)}")
        raise

if __name__ == "__main__":
    args = parse_args()
    logger.info(f"Starting sync process (Schedule: every {args.schedule_time} minutes)")
    logger.info(f"Monitoring runs for user: {args.user_name}")

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
