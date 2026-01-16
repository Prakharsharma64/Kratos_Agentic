"""Council coordination plugin."""

import logging
import asyncio
from typing import Any, Dict, List, Optional
import statistics

from .base_reasoning import BaseReasoningPlugin
from ...core.config import get_config

logger = logging.getLogger(__name__)


class CouncilCoordinatorPlugin(BaseReasoningPlugin):
    """Orchestrates multi-agent council deliberation."""
    
    @property
    def plugin_name(self) -> str:
        """Plugin name."""
        return "council_coordinator"
    
    @property
    def plugin_version(self) -> str:
        """Plugin version."""
        return "1.0.0"
    
    @property
    def dependencies(self) -> List[str]:
        """Dependencies."""
        return ["phi_reasoner", "qwen_reasoner"]
    
    def __init__(self):
        """Initialize plugin."""
        self.config = get_config()
        self.phi_plugin = None
        self.qwen_plugin = None
    
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize plugin."""
        logger.info("Council coordinator plugin initialized")
    
    async def cleanup(self) -> None:
        """Cleanup plugin resources."""
        logger.info("Council coordinator plugin cleaned up")
    
    async def process(self, text: str, intent: Dict[str, Any] = None, entities: Dict[str, Any] = None, 
                     council_size: int = 4, **kwargs) -> str:
        """Coordinate council deliberation.
        
        Args:
            text: Input query
            intent: Intent classification
            entities: Extracted entities
            council_size: Number of council members (3-4 or 8)
            **kwargs: Additional options
            
        Returns:
            Final synthesized response
        """
        # Get plugins
        if self.phi_plugin is None:
            self.phi_plugin = getattr(self, "phi_reasoner_plugin", None)
        if self.qwen_plugin is None:
            self.qwen_plugin = getattr(self, "qwen_reasoner_plugin", None)
        
        if self.phi_plugin is None:
            raise RuntimeError("Phi reasoner plugin not available")
        
        # Stage 1: First Opinions (Parallel)
        opinions = await self._stage1_first_opinions(text, intent, entities, council_size)
        
        # Stage 2: Review & Ranking
        ranked_opinions = await self._stage2_review_ranking(opinions, text, intent)
        
        # Stage 3: Chairman Synthesis
        if self.qwen_plugin:
            final_response = await self._stage3_synthesis(ranked_opinions, text)
        else:
            # Fallback to Phi if Qwen not available
            final_response = ranked_opinions[0]["opinion"]
        
        return final_response
    
    async def _stage1_first_opinions(self, text: str, intent: Dict[str, Any], entities: Dict[str, Any], 
                                    council_size: int) -> List[Dict[str, Any]]:
        """Stage 1: Parallel first opinions."""
        time_limit = self.config.council.time_limit_per_member
        
        # Create tasks for parallel execution
        tasks = []
        for i in range(council_size):
            # Each member gets slightly different prompt variation
            prompt_variation = self._create_prompt_variation(text, i, council_size)
            task = self._get_member_opinion(prompt_variation, time_limit)
            tasks.append(task)
        
        # Execute in parallel with timeout
        opinions = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and format
        valid_opinions = []
        for i, result in enumerate(opinions):
            if isinstance(result, Exception):
                logger.warning(f"Council member {i} failed: {result}")
                continue
            valid_opinions.append({
                "member_id": i,
                "opinion": result,
                "score": 0.5  # Initial score
            })
        
        return valid_opinions
    
    def _create_prompt_variation(self, text: str, member_id: int, council_size: int) -> str:
        """Create prompt variation for council member."""
        perspectives = [
            "Consider the practical implications.",
            "Think about the theoretical aspects.",
            "Focus on user experience.",
            "Consider edge cases and limitations.",
            "Think about scalability and performance.",
            "Consider ethical implications.",
            "Focus on clarity and simplicity.",
            "Think about long-term consequences."
        ]
        
        perspective = perspectives[member_id % len(perspectives)]
        return f"{text}\n\nPerspective: {perspective}"
    
    async def _get_member_opinion(self, prompt: str, time_limit: int) -> str:
        """Get opinion from a council member with timeout."""
        try:
            if self.phi_plugin is None:
                return "I need more information to provide a good answer."
            
            # Call Phi reasoner with timeout
            response = await asyncio.wait_for(
                self.phi_plugin.process(prompt),
                timeout=time_limit
            )
            return response if isinstance(response, str) else str(response)
        except asyncio.TimeoutError:
            logger.warning(f"Council member timed out after {time_limit}s")
            return "I need more time to think about this."
        except Exception as e:
            logger.error(f"Council member error: {e}")
            return "I encountered an error processing this."
    
    async def _stage2_review_ranking(self, opinions: List[Dict[str, Any]], text: str, 
                                   intent: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Stage 2: Review and rank opinions."""
        # Heuristic scoring
        for opinion_data in opinions:
            opinion = opinion_data["opinion"]
            score = 0.5
            
            # Intent alignment
            intent_label = intent.get("intent", "conversation")
            if intent_label in opinion.lower():
                score += 0.1
            
            # Length check (not too short, not too long)
            word_count = len(opinion.split())
            if 20 <= word_count <= 200:
                score += 0.1
            elif word_count < 10:
                score -= 0.2
            
            # Readability (simple check)
            if "." in opinion and " " in opinion:
                score += 0.1
            
            # Semantic similarity (simplified)
            # In real implementation, would use embedding similarity
            
            opinion_data["score"] = min(1.0, max(0.0, score))
        
        # Check for disagreement (variance in scores)
        scores = [op["score"] for op in opinions]
        variance = statistics.variance(scores) if len(scores) > 1 else 0.0
        
        # If high variance, use Phi for review
        if variance > 0.1 and self.phi_plugin:
            # Use Phi to review and re-score
            review_prompt = f"Review these opinions and score them:\n\n"
            for i, op in enumerate(opinions):
                review_prompt += f"Opinion {i+1}: {op['opinion']}\n"
            review_prompt += "\nProvide scores (0-1) for each opinion."
            
            try:
                review_response = await self.phi_plugin.process(review_prompt)
                # Parse scores from response (simplified)
                # In real implementation, would parse structured response
            except Exception as e:
                logger.warning(f"Review stage failed: {e}")
        
        # Sort by score
        ranked = sorted(opinions, key=lambda x: x["score"], reverse=True)
        
        return ranked
    
    async def _stage3_synthesis(self, ranked_opinions: List[Dict[str, Any]], text: str) -> str:
        """Stage 3: Chairman synthesis using Qwen."""
        if self.qwen_plugin is None:
            # Fallback to top opinion
            return ranked_opinions[0]["opinion"]
        
        # Check for dissent
        scores = [op["score"] for op in ranked_opinions]
        variance = statistics.variance(scores) if len(scores) > 1 else 0.0
        has_dissent = variance > 0.15
        
        # Build synthesis context
        context = {
            "opinions": [op["opinion"] for op in ranked_opinions],
            "has_dissent": has_dissent,
            "top_score": ranked_opinions[0]["score"] if ranked_opinions else 0.5
        }
        
        # Synthesize
        synthesis_prompt = f"Original query: {text}\n\n"
        if has_dissent:
            synthesis_prompt += "Note: There is significant disagreement among opinions.\n\n"
        
        synthesis_prompt += "Synthesize these opinions into a coherent, helpful response."
        
        response = await self.qwen_plugin.process(synthesis_prompt, context=context)
        
        # Add dissent note if needed
        if has_dissent:
            response = f"{response}\n\n[Note: There was some disagreement among the council members on this topic.]"
        
        return response
    
    def get_vram_usage(self) -> float:
        """Get VRAM usage."""
        return 0.0  # Coordinator doesn't use VRAM directly
