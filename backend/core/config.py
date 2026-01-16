"""Configuration management for the system."""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class VRAMConfig(BaseModel):
    """VRAM monitoring configuration."""
    soft_limit: float = Field(default=0.85, ge=0.0, le=1.0)
    hard_limit: float = Field(default=0.92, ge=0.0, le=1.0)


class ModelsConfig(BaseModel):
    """Model management configuration."""
    cache_dir: str = Field(default="./models")
    auto_download: bool = Field(default=True)
    device: str = Field(default="cuda")  # "cuda" or "cpu"


class PluginsConfig(BaseModel):
    """Plugin configuration."""
    enabled: List[str] = Field(default_factory=list)
    disabled: List[str] = Field(default_factory=list)


class CouncilConfig(BaseModel):
    """Council system configuration."""
    simple_threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    medium_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    full_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    time_limit_per_member: int = Field(default=10, gt=0)


class MemoryConfig(BaseModel):
    """Memory system configuration."""
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    decay_rate: float = Field(default=0.02, ge=0.0, le=1.0)
    cleanup_threshold: float = Field(default=0.2, ge=0.0, le=1.0)


class HumanizationConfig(BaseModel):
    """Humanization configuration."""
    emoji_max_per_message: int = Field(default=3, ge=0)
    exclude_domains: List[str] = Field(default_factory=lambda: ["legal", "medical", "sql"])


class SystemConfig(BaseModel):
    """Complete system configuration."""
    vram: VRAMConfig = Field(default_factory=VRAMConfig)
    models: ModelsConfig = Field(default_factory=ModelsConfig)
    plugins: PluginsConfig = Field(default_factory=PluginsConfig)
    council: CouncilConfig = Field(default_factory=CouncilConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    humanization: HumanizationConfig = Field(default_factory=HumanizationConfig)


class Config:
    """Configuration manager."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration.
        
        Args:
            config_path: Path to config.yaml file (default: ./backend/config.yaml)
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.yaml"
        else:
            config_path = Path(config_path)
        
        self.config_path = config_path
        self._config: Optional[SystemConfig] = None
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                yaml_data = yaml.safe_load(f) or {}
        else:
            yaml_data = {}
        
        # Override with environment variables
        yaml_data = self._apply_env_overrides(yaml_data)
        
        self._config = SystemConfig(**yaml_data)
    
    def _apply_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides."""
        # VRAM limits
        if os.getenv("VRAM_SOFT_LIMIT"):
            if "vram" not in config:
                config["vram"] = {}
            config["vram"]["soft_limit"] = float(os.getenv("VRAM_SOFT_LIMIT"))
        
        if os.getenv("VRAM_HARD_LIMIT"):
            if "vram" not in config:
                config["vram"] = {}
            config["vram"]["hard_limit"] = float(os.getenv("VRAM_HARD_LIMIT"))
        
        # Model device
        if os.getenv("MODEL_DEVICE"):
            if "models" not in config:
                config["models"] = {}
            config["models"]["device"] = os.getenv("MODEL_DEVICE")
        
        # Model cache directory
        if os.getenv("MODEL_CACHE_DIR"):
            if "models" not in config:
                config["models"] = {}
            config["models"]["cache_dir"] = os.getenv("MODEL_CACHE_DIR")
        
        return config
    
    def get_config(self) -> SystemConfig:
        """Get current configuration.
        
        Returns:
            SystemConfig instance
        """
        if self._config is None:
            self._load_config()
        return self._config
    
    def reload(self) -> None:
        """Reload configuration from file."""
        self._load_config()


# Global configuration instance
_config_instance: Optional[Config] = None


def get_config() -> SystemConfig:
    """Get global configuration instance.
    
    Returns:
        SystemConfig instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance.get_config()
