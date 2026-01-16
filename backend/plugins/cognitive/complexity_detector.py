"""Complexity detection plugin."""

import logging
import re
from typing import Any, Dict, List

from .base_cognitive import BaseCognitivePlugin

logger = logging.getLogger(__name__)


class ComplexityDetectorPlugin(BaseCognitivePlugin):
    """Complexity detection using heuristics and DeBERTa."""
    
    @property
    def plugin_name(self) -> str:
        """Plugin name."""
        return "complexity_detector"
    
    @property
    def plugin_version(self) -> str:
        """Plugin version."""
        return "1.0.0"
    
    @property
    def dependencies(self) -> List[str]:
        """Dependencies."""
        return ["intent_classifier"]
    
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize plugin."""
        logger.info("Complexity detector plugin initialized")
    
    async def cleanup(self) -> None:
        """Cleanup plugin resources."""
        logger.info("Complexity detector plugin cleaned up")
    
    async def process(self, text: str, intent_result: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        """Detect query complexity.
        
        Args:
            text: Input text
            intent_result: Intent classification result
            **kwargs: Additional options
            
        Returns:
            Complexity detection result with score (0.0-1.0)
        """
        if intent_result is None:
            intent_result = {}
        
        complexity_score = 0.0
        
        # Heuristic 1: Multi-part questions
        question_marks = text.count("?")
        if question_marks > 1:
            complexity_score += 0.2
        elif question_marks == 1:
            # Check for compound questions
            if " and " in text.lower() or " or " in text.lower():
                complexity_score += 0.15
        
        # Heuristic 2: Ambiguous phrasing
        ambiguous_words = ["maybe", "perhaps", "might", "could", "possibly", "unclear"]
        if any(word in text.lower() for word in ambiguous_words):
            complexity_score += 0.15
        
        # Heuristic 3: Length and structure
        word_count = len(text.split())
        if word_count > 50:
            complexity_score += 0.1
        elif word_count > 20:
            complexity_score += 0.05
        
        # Heuristic 4: Requires reasoning (keywords)
        reasoning_keywords = ["compare", "analyze", "evaluate", "synthesize", "reason", "logic"]
        if any(word in text.lower() for word in reasoning_keywords):
            complexity_score += 0.2
        
        # Heuristic 5: Multiple topics
        topic_indicators = ["also", "additionally", "furthermore", "moreover", "besides"]
        if sum(1 for word in topic_indicators if word in text.lower()) > 1:
            complexity_score += 0.15
        
        # Heuristic 6: Intent-based complexity
        intent = intent_result.get("intent", "conversation")
        if intent == "creative":
            complexity_score += 0.1
        elif intent == "information" and word_count > 15:
            complexity_score += 0.1
        
        # Normalize to 0.0-1.0
        complexity_score = min(1.0, complexity_score)
        
        # Determine complexity level
        if complexity_score < 0.3:
            level = "simple"
        elif complexity_score < 0.6:
            level = "medium"
        else:
            level = "complex"
        
        return {
            "complexity": level,
            "score": complexity_score,
            "signals": {
                "multi_part": question_marks > 1,
                "ambiguous": any(word in text.lower() for word in ambiguous_words),
                "long": word_count > 20,
                "reasoning_required": any(word in text.lower() for word in reasoning_keywords)
            }
        }
