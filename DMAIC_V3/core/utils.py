import hashlib
import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from datetime import datetime


def setup_logger(name: str, log_file: Optional[Path] = None, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def compute_hash(data: Union[str, bytes, Dict, List]) -> str:
    if isinstance(data, dict) or isinstance(data, list):
        data = json.dumps(data, sort_keys=True)
    
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    return hashlib.sha256(data).hexdigest()


def compute_file_hash(file_path: Path) -> str:
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_write_json(data: Any, file_path: Path, indent: int = 2) -> bool:
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = file_path.with_suffix('.tmp')
        
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, default=str)
        
        shutil.move(str(temp_path), str(file_path))
        return True
    except Exception as e:
        logging.error(f"Failed to write JSON to {file_path}: {e}")
        if temp_path.exists():
            temp_path.unlink()
        return False


def safe_read_json(file_path: Path) -> Optional[Dict]:
    try:
        if not file_path.exists():
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to read JSON from {file_path}: {e}")
        return None


def validate_path_exists(path: Path, path_type: str = "path") -> bool:
    if not path.exists():
        logging.error(f"{path_type} does not exist: {path}")
        return False
    return True


def validate_file_readable(file_path: Path) -> bool:
    if not file_path.is_file():
        logging.error(f"Not a file: {file_path}")
        return False

    if not os.access(file_path, os.R_OK):
        logging.error(f"File not readable: {file_path}")
        return False

    return True


# Convenience aliases
save_json = safe_write_json
read_json = safe_read_json


def validate_directory_writable(dir_path: Path) -> bool:
    if not dir_path.is_dir():
        logging.error(f"Not a directory: {dir_path}")
        return False
    
    if not os.access(dir_path, os.W_OK):
        logging.error(f"Directory not writable: {dir_path}")
        return False
    
    return True


def get_file_size_mb(file_path: Path) -> float:
    return file_path.stat().st_size / (1024 * 1024)


def get_directory_size_mb(dir_path: Path) -> float:
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(dir_path):
        for filename in filenames:
            file_path = Path(dirpath) / filename
            if file_path.exists():
                total_size += file_path.stat().st_size
    return total_size / (1024 * 1024)


def copy_file_with_backup(src: Path, dst: Path, backup_suffix: str = ".bak") -> bool:
    try:
        if dst.exists():
            backup_path = dst.with_suffix(dst.suffix + backup_suffix)
            shutil.copy2(src, backup_path)
        
        shutil.copy2(src, dst)
        return True
    except Exception as e:
        logging.error(f"Failed to copy {src} to {dst}: {e}")
        return False


def archive_directory(src_dir: Path, archive_path: Path) -> bool:
    try:
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        base_name = str(archive_path.with_suffix(''))
        shutil.make_archive(base_name, 'zip', src_dir)
        return True
    except Exception as e:
        logging.error(f"Failed to archive {src_dir}: {e}")
        return False


def format_duration(seconds: float) -> str:
    hours, remainder = divmod(int(seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"


def format_timestamp(dt: Optional[datetime] = None) -> str:
    if dt is None:
        dt = datetime.now()
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def parse_timestamp(timestamp_str: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(timestamp_str)
    except Exception:
        try:
            return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        except Exception as e:
            logging.error(f"Failed to parse timestamp '{timestamp_str}': {e}")
            return None


def truncate_string(s: str, max_length: int = 100, suffix: str = "...") -> str:
    if len(s) <= max_length:
        return s
    return s[:max_length - len(suffix)] + suffix


def sanitize_filename(filename: str) -> str:
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename


def get_relative_path(path: Path, base: Path) -> Path:
    try:
        return path.relative_to(base)
    except ValueError:
        return path
