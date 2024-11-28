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
import gspread
from oauth2client.service_account import ServiceAccountCredentials

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

class SheetError(Exception):
    """Google Sheets related errors"""
    pass

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Sync WandB runs to Google Sheets')
    parser.add_argument('--schedule_time', type=int, default=30,
                       help='Schedule interval in minutes (default: 30)')
    parser.add_argument('--user_name', type=str, default='ng-youn',
                       help='User name for tracking WandB runs')
    parser.add_argument('--sheet_name', type=str, required=True,
                       help='Name of the Google Sheet to use')
    parser.add_argument('--config_path', type=str, default='CONFIG.json',
                       help='Path to configuration file')
    return parser.parse_args()


def load_config(config_path: str) -> Dict[str, Any]:
    """설정 파일 로드 및 검증"""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)

        required_keys = ['GCP_JSON', 'FIXED_HEADERS']
        missing_keys = [key for key in required_keys if key not in config]
        if missing_keys:
            raise ConfigError(f"Missing required keys in config: {missing_keys}")

        try:
            team_name, project_name = config['TEAM_NAME'], config['PROJECT_NAME']
        except ConfigError as e:
            raise ConfigError(f"Failed to get WandB project info: {str(e)}")

        return config
    except FileNotFoundError:
        raise ConfigError(f"Config file not found: {config_path}")
    except json.JSONDecodeError:
        raise ConfigError(f"Invalid JSON in config file: {config_path}")

def init_sheet(sheet_name: str, config: Dict[str, Any]) -> Tuple[gspread.Worksheet, wandb.Api]:
    """스프레드시트 초기화 및 WandB API 연결"""
    try:
        # Add more detailed logging for debugging
        logger.info(f"Initializing sheet: {sheet_name}")
        logger.info(f"Using GCP JSON key file: {config['GCP_JSON']}")

        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        try:
            # Verify the JSON file exists and is readable
            with open(config['GCP_JSON'], 'r') as f:
                json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as file_error:
            logger.error(f"Error with service account JSON file: {file_error}")
            raise ConfigError(f"Invalid service account JSON file: {config['GCP_JSON']}")

        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name(
                config['GCP_JSON'], scope
            )
            client = gspread.authorize(creds)
        except Exception as auth_error:
            logger.error(f"Authentication error: {auth_error}")
            raise SheetError(f"Failed to authenticate: {str(auth_error)}")

        try:
            # Open spreadsheet with more robust error handling
            spreadsheet = client.open(sheet_name)
        except gspread.exceptions.SpreadsheetNotFound:
            logger.error(f"Spreadsheet not found: {sheet_name}")
            raise SheetError(f"Spreadsheet '{sheet_name}' not found. Please check the sheet name.")
        except Exception as open_error:
            logger.error(f"Error opening spreadsheet: {open_error}")
            raise SheetError(f"Failed to open spreadsheet: {str(open_error)}")

        # 시트 개수 제한 확인
        worksheets = spreadsheet.worksheets()
        if len(worksheets) >= 100:  # Google Sheets 제한
            oldest_sheet = min(
                (sheet for sheet in worksheets if not sheet.title.startswith('runs_')),
                key=lambda x: x.title
            )
            oldest_sheet.delete()
            logger.warning(f"Deleted oldest sheet: {oldest_sheet.title}")

        # If there is no existing sheet, create it.
        if len(spreadsheet.sheet1.get_all_values()) > 0:
            new_sheet_name = f"runs_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            worksheet = spreadsheet.add_worksheet(
                title=new_sheet_name,
                rows=min(1000, spreadsheet.sheet1.row_count),
                cols=min(50, spreadsheet.sheet1.col_count)
            )
            # Copy before sheet.
            header_row = spreadsheet.sheet1.row_values(1)
            if header_row:
                worksheet.append_row(header_row)
        else:
            worksheet = spreadsheet.sheet1

        # WandB API 연결
        api = wandb.Api()

        logger.info(f"Successfully initialized sheet: {sheet_name}")
        return worksheet, api

    except (ConfigError, SheetError) as known_error:
        logger.error(f"Configuration or Sheet Error: {known_error}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in sheet initialization: {str(e)}")
        raise SheetError(f"Failed to initialize sheet: {str(e)}")


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


def process_runs(runs: List[Any], run_id_list: List[str],
                final_headers: List[str], user_name: str) -> List[List[str]]:
    """WandB runs 처리"""
    rows_to_add = []

    for run in runs:
        if run.state == "running" and run.id not in run_id_list:
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
                    rows_to_add.append(row_data)
                except Exception as e:
                    logger.error(f"Error processing run {run.id}: {str(e)}")
                    continue

    return rows_to_add


def sync_data(sheet: gspread.Worksheet, new_rows: List[List[str]]) -> None:
    """Data sync"""
    try:
        if new_rows:
            sheet.append_rows(new_rows)
            time.sleep(1)  # API 제한 방지
    except Exception as e:
        raise SheetError(f"Failed to sync data: {str(e)}")


def main(args: argparse.Namespace) -> None:
    try:
        config = load_config(args.config_path)
        sheet, api = init_sheet(args.sheet_name, config)

        runs = api.runs(f"{config['TEAM_NAME']}/{config['PROJECT_NAME']}")
        run_id_list = [row[0] for row in sheet.get_all_values()[1:]]  # Skip header

        new_rows = process_runs(
            runs, run_id_list, config['FIXED_HEADERS'],
            args.user_name
        )

        if new_rows:
            sync_data(sheet, new_rows)
            logger.info(f"Successfully added {len(new_rows)} new runs")
        else:
            logger.info("No new runs to add")

    except Exception as e:
        logger.error(f"Error in main sync process: {str(e)}")
        raise

if __name__ == "__main__":
    args = parse_args()
    config = load_config(args.config_path)

    logger.info(f"Starting sync process (Schedule: every {args.schedule_time} minutes)")
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
