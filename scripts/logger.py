import json, logging

def load_config(tools, config_path: str) -> Dict[str, Any]:
    """Load and validate configuration file"""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)

        required_keys = ['TEAM_NAME', 'PROJECT_NAME']

        if tools == 'gcp':
            required_keys.append('GCP_API')

        elif tools == 'notion':
            required_keys.extend(['NOTION_API', 'NOTION_TOKEN', 'NOTION_DB_ID'])

        missing_keys = [key for key in required_keys if key not in config]

        if missing_keys:
            raise ConfigError(f"Missing required keys in config: {missing_keys}")

        if missing_keys:
            raise ConfigError(f"Missing required keys in config: {missing_keys}")

        try:
            team_name, project_name = config['TEAM_NAME'], config['PROJECT_NAME']
        except ConfigError as e:
            raise ConfigError(f"Failed to get WandB project info: {str(e)}")


    except FileNotFoundError:
        raise ConfigError(f"Config file not found: {config_path}")
    except json.JSONDecodeError:
        raise ConfigError(f"Invalid JSON in config file: {config_path}")

    except FileNotFoundError:
        raise ConfigError(f"Config file not found: {config_path}")
    except json.JSONDecodeError:
        raise ConfigError(f"Invalid JSON in config file: {config_path}")

class ConfigError(Exception):
    """Configuration related errors"""
    pass

class SheetError(Exception):
    """Google Sheets related errors"""
    pass

class NotionSyncError(Exception):
    """Notion synchronization related errors"""
    pass


def get_gpu_memory():
    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=memory.total,memory.used,memory.free', '--format=csv,nounits,noheader'],
                                capture_output=True, text=True)
        if result.returncode == 0 and result.stdout:
            # 결과 파싱
            memory_info = result.stdout.strip().split('\n')
            # 각 GPU별 메모리 정보 출력
            for idx, memory in enumerate(memory_info):
                total, used, free = memory.split(',')
        return int(used)
    except Exception as e:
        return "null"