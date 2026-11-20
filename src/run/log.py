"""
General-purpose logging module.
Features:
1. Automatically records inputs and outputs of calls (currently mainly LLM calls)
2. Deletes log files older than one week on startup
3. Groups log files by date
"""

import logging
import os
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from src.config.data_paths import get_data_paths
from src.utils.config import CONFIG

class Logger:
    """General-purpose logger."""
    
    def __init__(self, log_dir: str | os.PathLike | None = None):
        """
        Initialize the logger.
        
        Args:
            log_dir: directory where log files are stored
        """
        self.log_dir = Path(log_dir) if log_dir is not None else get_data_paths().logs_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Clean up old log files
        self._cleanup_old_logs()
        
        # Set up the current log file
        self._setup_current_logger()
    
    def _cleanup_old_logs(self):
        """Delete log files older than one week."""
        cutoff_date = datetime.now() - timedelta(days=7)
        
        for log_file in self.log_dir.glob("*.log"):
            try:
                # Extract the date from the file name
                date_str = log_file.stem.split("_")[-1]  # use the last segment as the date
                file_date = datetime.strptime(date_str, "%Y%m%d")
                
                if file_date < cutoff_date:
                    log_file.unlink()
                    print(f"Deleted expired log file: {log_file}")
            except (ValueError, OSError) as e:
                print(f"Error processing log file {log_file}: {e}")
    
    def _setup_current_logger(self):
        """Set up the logger for the current date."""
        current_date = datetime.now().strftime("%Y%m%d")
        log_filename = f"{current_date}.log"
        self.log_file_path = self.log_dir / log_filename
        
        # Create the logger
        self.logger = logging.getLogger(f"logger_{current_date}")
        self.logger.setLevel(logging.INFO)
        
        # Clear existing handlers (avoid duplicate records)
        self.logger.handlers.clear()
        
        # Create the file handler
        handler = logging.FileHandler(
            self.log_file_path,
            encoding='utf-8',
            mode='a'
        )
        
        # Set the log format
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        self.logger.addHandler(handler)
        
        # Do not propagate to the root logger
        self.logger.propagate = False
        
        # Record the version number
        if hasattr(CONFIG, "meta") and hasattr(CONFIG.meta, "version"):
            self.logger.info(f"========== Game Start (Version: {CONFIG.meta.version}) ==========")
        else:
            self.logger.info("========== Game Start (Version: Unknown) ==========")
    
    def log_llm_interaction(self, 
                          model_name: str,
                          prompt: str, 
                          response: str,
                          duration: Optional[float] = None,
                          additional_info: Optional[dict] = None):
        """
        Record an LLM interaction.
        
        Args:
            model_name: name of the model used
            prompt: input prompt
            response: LLM response
            duration: call duration (seconds)
            additional_info: extra information
        """
        # Machine-readable summary (no large text blocks, to avoid JSON escaping clutter with \)
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "model_name": model_name,
            "prompt_length": len(prompt),
            "response_length": len(response),
            "duration": duration
        }
        
        if additional_info:
            log_data.update(additional_info)
        
        # Record a parseable JSON summary
        log_message = f"LLM_INTERACTION: {json.dumps(log_data, ensure_ascii=False)}"
        self.logger.info(log_message)

        # Record friendlier raw multi-line text so quotes are not escaped
        self.logger.info("LLM_PROMPT:\n%s", prompt)
        self.logger.info("LLM_RESPONSE:\n%s", response)
    
    def log_error(self, error_message: str, prompt: str = None):
        """
        Record an error.
        
        Args:
            error_message: error message
            prompt: related prompt (optional)
        """
        # Error summary (without the raw prompt, to avoid escaping noise)
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "error": error_message,
        }

        log_message = f"LLM_ERROR: {json.dumps(log_data, ensure_ascii=False)}"
        self.logger.error(log_message)

        # If a prompt is provided, append the raw multi-line text for debugging
        if prompt:
            self.logger.error("LLM_ERROR_PROMPT:\n%s", prompt)
    
    def get_today_stats(self) -> dict:
        """
        Get today's statistics.
        
        Returns:
            dict: today's call count, total duration, etc.
        """
        if not self.log_file_path.exists():
            return {
                "total_calls": 0,
                "total_duration": 0,
                "total_prompt_length": 0,
                "total_response_length": 0,
                "errors": 0
            }
        
        stats = {
            "total_calls": 0,
            "total_duration": 0,
            "total_prompt_length": 0,
            "total_response_length": 0,
            "errors": 0
        }
        
        with open(self.log_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if "LLM_INTERACTION:" in line:
                    try:
                        json_str = line.split("LLM_INTERACTION: ", 1)[1]
                        data = json.loads(json_str)
                        stats["total_calls"] += 1
                        stats["total_duration"] += data.get("duration", 0) or 0
                        stats["total_prompt_length"] += data.get("prompt_length", 0)
                        stats["total_response_length"] += data.get("response_length", 0)
                    except (json.JSONDecodeError, IndexError):
                        pass
                elif "LLM_ERROR:" in line:
                    stats["errors"] += 1
        
        return stats


# Global logger instance
_logger = None

def get_logger() -> Logger:
    """Get the global logger instance."""
    global _logger
    if _logger is None:
        _logger = Logger()
    return _logger

# LLM convenience helpers
def log_llm_call(model_name: str, prompt: str, response: str, duration: float = None):
    """Convenience helper: record an LLM call."""
    logger = get_logger()
    logger.log_llm_interaction(model_name, prompt, response, duration)

def log_llm_error(error_message: str, prompt: str = None):
    """Convenience helper: record an LLM error."""
    logger = get_logger()
    logger.log_error(error_message, prompt)
