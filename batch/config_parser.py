import os
from loguru import logger


class ConfigParser:
    """Zero-dependency YAML parser to read config.yaml configuration parameters."""

    @staticmethod
    def load_config(filepath: str = "config.yaml") -> dict:
        """
        Loads configuration settings from filepath.
        Returns a dictionary of parsed settings falling back to defaults if not found or invalid.
        """
        # Default fallback values
        config = {
            "workers": 3,
            "batch_size": 10,
            "timeout": 120,
            "retry": 3,
            "delay": 2.0,
            "provider": "duckduckgo"
        }
        
        if not os.path.exists(filepath):
            logger.warning(f"Configuration file '{filepath}' not found. Using system defaults.")
            return config
            
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # Skip comments or empty lines
                    if not line or line.startswith("#"):
                        continue
                    if ":" in line:
                        parts = line.split(":", 1)
                        key = parts[0].strip()
                        val = parts[1].strip()
                        
                        # Perform standard primitive type conversions
                        if val.lower() == "true":
                            val = True
                        elif val.lower() == "false":
                            val = False
                        elif val.isdigit():
                            val = int(val)
                        else:
                            try:
                                val = float(val)
                            except ValueError:
                                val = val.strip("'\"")
                        config[key] = val
            logger.info(f"Loaded config settings from '{filepath}': {config}")
            return config
            
        except Exception as e:
            logger.error(f"Error parsing configuration file '{filepath}': {e}. Using defaults.")
            return config
