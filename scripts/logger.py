from typing import Dict, Any, Optional, List
import json
import logging
import subprocess
from dataclasses import dataclass

@dataclass
class GPUMemoryInfo:
    total: int
    used: int
    free: int

class ConfigError(Exception):
    """Configuration related errors"""
    pass

class NotionSyncError(Exception):
    """Notion synchronization related errors"""
    pass

def load_config(tool_type: str, config_path: str) -> Dict[str, Any]:
    """
    Load and validate configuration file

    Args:
        tool_type: Type of tool ('gcp' or 'notion')
        config_path: Path to config file

    Returns:
        Dict containing configuration

    Raises:
        ConfigError: If configuration is invalid or missing
    """
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)

        required_keys = {'TEAM_NAME', 'PROJECT_NAME'}

        if tool_type == 'gcp':
            required_keys.add('GCP_API')
        elif tool_type == 'notion':
            required_keys.update({'NOTION_API', 'NOTION_TOKEN', 'NOTION_DB_ID'})
        else:
            raise ConfigError(f"Unsupported tool type: {tool_type}")

        missing_keys = required_keys - set(config.keys())
        if missing_keys:
            raise ConfigError(f"Missing required keys in config: {missing_keys}")

        return config

    except FileNotFoundError:
        raise ConfigError(f"Config file not found: {config_path}")
    except json.JSONDecodeError:
        raise ConfigError(f"Invalid JSON in config file: {config_path}")

def get_gpu_memory() -> Optional[List[GPUMemoryInfo]]:
    """
    Get GPU memory information for all available GPUs

    Returns:
        List of GPUMemoryInfo objects or None if error occurs
    """
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=memory.total,memory.used,memory.free',
             '--format=csv,nounits,noheader'],
            capture_output=True,
            text=True,
            check=True
        )

        gpu_info_list = []
        for line in result.stdout.strip().split('\n'):
            total, used, free = map(int, line.split(','))
            gpu_info_list.append(GPUMemoryInfo(total=total, used=used, free=free))

        return gpu_info_list

    except (subprocess.SubprocessError, ValueError) as e:
        logging.error(f"Failed to get GPU memory info: {e}")
        return None