"""VRAM monitoring and management."""

import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import torch

logger = logging.getLogger(__name__)


class VRAMStatus(Enum):
    """VRAM status levels."""
    OK = "ok"
    WARNING = "warning"  # Soft limit reached
    CRITICAL = "critical"  # Hard limit reached


@dataclass
class ModelPriority:
    """Model priority levels for eviction."""
    CRITICAL = 0  # Never evict (Phi-3.5-mini)
    HIGH = 1  # Evict only at hard limit (Qwen for council)
    MEDIUM = 2  # Evict at soft limit (Audio/Image models)
    LOW = 3  # Evict first (Cached models)


@dataclass
class ModelInfo:
    """Information about a loaded model."""
    name: str
    vram_usage_gb: float
    priority: int = ModelPriority.MEDIUM
    device: str = "cuda"
    loaded: bool = True


class VRAMMonitor:
    """Monitor and manage GPU VRAM usage."""
    
    def __init__(self, soft_limit: float = 0.85, hard_limit: float = 0.92):
        """Initialize VRAM monitor.
        
        Args:
            soft_limit: Soft limit as fraction (0.0-1.0)
            hard_limit: Hard limit as fraction (0.0-1.0)
        """
        self.soft_limit = soft_limit
        self.hard_limit = hard_limit
        self.models: Dict[str, ModelInfo] = {}
        self._total_vram_gb: Optional[float] = None
        self._available_vram_gb: Optional[float] = None
    
    def _get_total_vram(self) -> float:
        """Get total VRAM in GB.
        
        Returns:
            Total VRAM in gigabytes
        """
        if self._total_vram_gb is None:
            if torch.cuda.is_available():
                self._total_vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
            else:
                self._total_vram_gb = 0.0
        return self._total_vram_gb
    
    def _get_used_vram(self) -> float:
        """Get currently used VRAM in GB.
        
        Returns:
            Used VRAM in gigabytes
        """
        if torch.cuda.is_available():
            return torch.cuda.memory_allocated() / (1024 ** 3)
        return 0.0
    
    def _get_available_vram(self) -> float:
        """Get available VRAM in GB.
        
        Returns:
            Available VRAM in gigabytes
        """
        if torch.cuda.is_available():
            return (torch.cuda.get_device_properties(0).total_memory - 
                   torch.cuda.memory_allocated()) / (1024 ** 3)
        return 0.0
    
    def get_status(self) -> Tuple[VRAMStatus, float, float]:
        """Get current VRAM status.
        
        Returns:
            Tuple of (status, used_gb, total_gb)
        """
        total = self._get_total_vram()
        used = self._get_used_vram()
        
        if total == 0:
            return VRAMStatus.OK, 0.0, 0.0
        
        usage_ratio = used / total
        
        if usage_ratio >= self.hard_limit:
            return VRAMStatus.CRITICAL, used, total
        elif usage_ratio >= self.soft_limit:
            return VRAMStatus.WARNING, used, total
        else:
            return VRAMStatus.OK, used, total
    
    def register_model(self, name: str, vram_usage_gb: float, priority: int = ModelPriority.MEDIUM, 
                      device: str = "cuda") -> None:
        """Register a model with the monitor.
        
        Args:
            name: Model identifier
            vram_usage_gb: VRAM usage in GB
            priority: Eviction priority (lower = higher priority)
            device: Device where model is loaded
        """
        self.models[name] = ModelInfo(
            name=name,
            vram_usage_gb=vram_usage_gb,
            priority=priority,
            device=device,
            loaded=True
        )
        logger.info(f"Registered model: {name} ({vram_usage_gb:.2f} GB, priority={priority})")
    
    def unregister_model(self, name: str) -> None:
        """Unregister a model.
        
        Args:
            name: Model identifier
        """
        if name in self.models:
            del self.models[name]
            logger.info(f"Unregistered model: {name}")
    
    def update_model_usage(self, name: str, vram_usage_gb: float) -> None:
        """Update model VRAM usage.
        
        Args:
            name: Model identifier
            vram_usage_gb: New VRAM usage in GB
        """
        if name in self.models:
            self.models[name].vram_usage_gb = vram_usage_gb
    
    def get_models_to_evict(self, target_free_gb: float) -> list[str]:
        """Get list of models to evict to free up VRAM.
        
        Args:
            target_free_gb: Target free VRAM in GB
            
        Returns:
            List of model names to evict (sorted by priority)
        """
        status, used, total = self.get_status()
        
        if status == VRAMStatus.OK:
            return []
        
        # Calculate how much we need to free
        current_free = total - used
        needed_free = target_free_gb - current_free
        
        if needed_free <= 0:
            return []
        
        # Sort models by priority (higher priority number = evict first)
        evictable_models = [
            (name, info) for name, info in self.models.items()
            if info.loaded and info.priority > ModelPriority.CRITICAL
        ]
        evictable_models.sort(key=lambda x: x[1].priority, reverse=True)
        
        # Select models to evict
        models_to_evict = []
        freed_gb = 0.0
        
        for name, info in evictable_models:
            if freed_gb >= needed_free:
                break
            models_to_evict.append(name)
            freed_gb += info.vram_usage_gb
        
        return models_to_evict
    
    def can_load_model(self, required_gb: float, priority: int = ModelPriority.MEDIUM) -> Tuple[bool, Optional[str]]:
        """Check if a model can be loaded.
        
        Args:
            required_gb: Required VRAM in GB
            priority: Model priority
            
        Returns:
            Tuple of (can_load, reason_if_not)
        """
        status, used, total = self.get_status()
        
        if total == 0:
            return False, "No GPU available"
        
        available = total - used
        
        # Check if we have enough space
        if available >= required_gb:
            return True, None
        
        # Check if we can evict models to make space
        if priority <= ModelPriority.HIGH:
            # High priority models can trigger eviction
            models_to_evict = self.get_models_to_evict(required_gb)
            if models_to_evict:
                freed_gb = sum(self.models[name].vram_usage_gb for name in models_to_evict)
                if available + freed_gb >= required_gb:
                    return True, None
        
        return False, f"Insufficient VRAM (need {required_gb:.2f} GB, have {available:.2f} GB)"
    
    def get_summary(self) -> Dict[str, any]:
        """Get VRAM usage summary.
        
        Returns:
            Dictionary with VRAM statistics
        """
        status, used, total = self.get_status()
        available = total - used
        
        return {
            "status": status.value,
            "total_gb": total,
            "used_gb": used,
            "available_gb": available,
            "usage_ratio": used / total if total > 0 else 0.0,
            "soft_limit": self.soft_limit,
            "hard_limit": self.hard_limit,
            "models": {
                name: {
                    "vram_gb": info.vram_usage_gb,
                    "priority": info.priority,
                    "device": info.device,
                    "loaded": info.loaded
                }
                for name, info in self.models.items()
            }
        }
