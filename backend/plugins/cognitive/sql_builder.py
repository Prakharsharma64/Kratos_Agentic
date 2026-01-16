"""SQL generation plugin with safety validation."""

import logging
import asyncio
from typing import Any, Dict, List, Optional

from .base_cognitive import BaseCognitivePlugin
from ...core.model_manager import ModelManager
from ...core.vram_monitor import ModelPriority
from ...utils.sql_validator import SQLValidator

logger = logging.getLogger(__name__)


class SQLBuilderPlugin(BaseCognitivePlugin):
    """SQL generation with safety pipeline."""
    
    @property
    def plugin_name(self) -> str:
        """Plugin name."""
        return "sql_builder"
    
    @property
    def plugin_version(self) -> str:
        """Plugin version."""
        return "1.0.0"
    
    def __init__(self):
        """Initialize plugin."""
        self.model_manager: ModelManager = None
        self.model = None
        self.tokenizer = None
        self.validator = SQLValidator()
    
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize plugin."""
        from ...core.model_manager import ModelManager
        from ...core.vram_monitor import VRAMMonitor
        
        # Get model manager
        if hasattr(self, 'model_manager_plugin'):
            self.model_manager = self.model_manager_plugin
        else:
            vram_monitor = VRAMMonitor()
            self.model_manager = ModelManager(vram_monitor)
        
        # Load Flan-T5 model
        try:
            model_name = "google/flan-t5-base"
            self.model, self.tokenizer = await self.model_manager.load_model(
                model_name,
                model_type="base",
                priority=ModelPriority.MEDIUM
            )
            logger.info("SQL builder plugin initialized")
        except Exception as e:
            logger.warning(f"Failed to load SQL model: {e}")
            self.model = None
    
    async def cleanup(self) -> None:
        """Cleanup plugin resources."""
        if self.model_manager and self.model:
            await self.model_manager.unload_model("google/flan-t5-base")
        logger.info("SQL builder plugin cleaned up")
    
    async def process(self, query: str, schema: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Generate SQL from natural language query.
        
        Args:
            query: Natural language query
            schema: Database schema information
            **kwargs: Additional options (allowlist, etc.)
            
        Returns:
            SQL generation result with validated SQL
        """
        # Step 1: Generate SQL draft
        sql_draft = await self._generate_sql_draft(query, schema)
        
        # Step 2: AST validation
        validation_result = self.validator.validate_sql(sql_draft)
        
        if not validation_result["valid"]:
            return {
                "sql": None,
                "valid": False,
                "errors": validation_result.get("errors", []),
                "message": "Generated SQL failed validation"
            }
        
        # Step 3: Allowlist check
        allowlist = kwargs.get("allowlist", {})
        if allowlist:
            allowlist_result = self.validator.check_allowlist(sql_draft, allowlist)
            if not allowlist_result["allowed"]:
                return {
                    "sql": None,
                    "valid": False,
                    "errors": allowlist_result.get("errors", []),
                    "message": "SQL uses non-allowlisted tables/columns"
                }
        
        # Step 4: Read-only enforcement
        if not self.validator.is_read_only(sql_draft):
            return {
                "sql": None,
                "valid": False,
                "errors": ["SQL contains write operations"],
                "message": "Only read-only queries are allowed"
            }
        
        # Step 5: Cost estimation
        cost_estimate = self.validator.estimate_cost(sql_draft)
        
        return {
            "sql": sql_draft,
            "valid": True,
            "cost_estimate": cost_estimate,
            "execution_plan": validation_result.get("execution_plan", {})
        }
    
    async def _generate_sql_draft(self, query: str, schema: Optional[Dict[str, Any]]) -> str:
        """Generate SQL draft from natural language."""
        if self.model is None or self.tokenizer is None:
            # Fallback: simple template-based generation
            logger.warning("SQL model not available, using fallback")
            return f"SELECT * FROM table WHERE condition = '{query}'"
        
        # Build prompt
        prompt = f"Convert the following natural language query to SQL:\n\nQuery: {query}\n\n"
        if schema:
            prompt += f"Schema: {schema}\n\n"
        prompt += "SQL:"
        
        # Generate
        loop = asyncio.get_event_loop()
        sql = await loop.run_in_executor(
            None,
            self._generate_sql_sync,
            prompt
        )
        
        return sql.strip()
    
    def _generate_sql_sync(self, prompt: str) -> str:
        """Generate SQL synchronously."""
        # Tokenize
        inputs = self.tokenizer(prompt, return_tensors="pt", max_length=512, truncation=True)
        
        # Generate
        outputs = self.model.generate(
            **inputs,
            max_length=256,
            num_beams=4,
            early_stopping=True
        )
        
        # Decode
        sql = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract SQL (remove prompt)
        if "SQL:" in sql:
            sql = sql.split("SQL:")[-1].strip()
        
        return sql
    
    def get_vram_usage(self) -> float:
        """Get VRAM usage."""
        return 0.25
