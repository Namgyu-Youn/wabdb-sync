import scripts.logger as logger
from datetime import datetime
from typing import Any, List

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
    """Process WandB runs for Notion sync"""
    rows_to_add = []

    for run in runs:
        if (run.state == "finnished" or run.state == "killed") and run.id not in run_id_list:
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