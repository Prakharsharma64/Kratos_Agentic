"""Complexity detection heuristics."""

import re
from typing import Dict, List


def detect_multi_part(text: str) -> bool:
    """Detect if query has multiple parts."""
    question_marks = text.count("?")
    if question_marks > 1:
        return True
    
    # Check for compound questions
    compound_indicators = [" and ", " or ", " also ", " plus ", " as well as "]
    if any(indicator in text.lower() for indicator in compound_indicators):
        return True
    
    return False


def detect_ambiguity(text: str) -> bool:
    """Detect ambiguous phrasing."""
    ambiguous_words = ["maybe", "perhaps", "might", "could", "possibly", "unclear", "unsure"]
    return any(word in text.lower() for word in ambiguous_words)


def detect_reasoning_requirement(text: str) -> bool:
    """Detect if query requires reasoning."""
    reasoning_keywords = [
        "compare", "analyze", "evaluate", "synthesize", "reason", "logic",
        "why", "how", "explain", "justify", "conclude"
    ]
    return any(keyword in text.lower() for keyword in reasoning_keywords)


def detect_synthesis_requirement(text: str) -> bool:
    """Detect if query requires synthesis across sources."""
    synthesis_keywords = [
        "combine", "merge", "integrate", "synthesize", "unify",
        "all of", "together", "both", "multiple"
    ]
    return any(keyword in text.lower() for keyword in synthesis_keywords)


def calculate_complexity_score(text: str, intent: Dict[str, Any] = None) -> float:
    """Calculate overall complexity score.
    
    Args:
        text: Input text
        intent: Intent classification result
        
    Returns:
        Complexity score (0.0-1.0)
    """
    score = 0.0
    
    # Multi-part
    if detect_multi_part(text):
        score += 0.2
    
    # Ambiguity
    if detect_ambiguity(text):
        score += 0.15
    
    # Reasoning requirement
    if detect_reasoning_requirement(text):
        score += 0.2
    
    # Synthesis requirement
    if detect_synthesis_requirement(text):
        score += 0.15
    
    # Length
    word_count = len(text.split())
    if word_count > 50:
        score += 0.1
    elif word_count > 20:
        score += 0.05
    
    # Intent-based
    if intent:
        intent_type = intent.get("intent", "conversation")
        if intent_type == "creative":
            score += 0.1
        elif intent_type == "information" and word_count > 15:
            score += 0.1
    
    return min(1.0, score)
