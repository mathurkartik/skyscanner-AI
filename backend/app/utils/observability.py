"""
Observability module for Phase 8.
Structured logging of prompts, tool calls, artifacts, and review outcomes.
Avoids logging full secrets (API keys, user PII).
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List
from functools import wraps
import time

# Configure structured logging
logger = logging.getLogger("travel_planner")


class ObservabilityLogger:
    """
    Structured observability for multi-agent pipeline.
    Logs summaries without exposing secrets or full user content.
    """
    
    @staticmethod
    def log_agent_start(agent_name: str, trace_id: str, **context):
        """Log agent execution start."""
        logger.info(f"[{trace_id}] Agent {agent_name} starting", extra={
            "event": "agent_start",
            "agent": agent_name,
            "trace_id": trace_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "context_keys": list(context.keys())
        })
    
    @staticmethod
    def log_agent_complete(agent_name: str, trace_id: str, duration_ms: float, 
                           artifact_version: int = 1, success: bool = True, 
                           error_type: Optional[str] = None):
        """Log agent execution completion."""
        extra = {
            "event": "agent_complete",
            "agent": agent_name,
            "trace_id": trace_id,
            "duration_ms": duration_ms,
            "artifact_version": artifact_version,
            "success": success,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        if error_type:
            extra["error_type"] = error_type
        
        if success:
            logger.info(f"[{trace_id}] Agent {agent_name} completed in {duration_ms:.1f}ms", extra=extra)
        else:
            logger.warning(f"[{trace_id}] Agent {agent_name} failed after {duration_ms:.1f}ms", extra=extra)
    
    @staticmethod
    def log_llm_prompt(trace_id: str, prompt_type: str, 
                       system_chars: int, user_chars: int, 
                       model: str, estimated_tokens: int):
        """Log LLM prompt summary (not full content)."""
        logger.info(f"[{trace_id}] LLM prompt: {prompt_type}", extra={
            "event": "llm_prompt",
            "trace_id": trace_id,
            "prompt_type": prompt_type,
            "system_chars": system_chars,
            "user_chars": user_chars,
            "model": model,
            "estimated_tokens": estimated_tokens,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    @staticmethod
    def log_llm_response(trace_id: str, prompt_type: str,
                         response_chars: int, response_tokens: int,
                         duration_ms: float, cached: bool = False):
        """Log LLM response summary."""
        logger.info(f"[{trace_id}] LLM response: {prompt_type}", extra={
            "event": "llm_response",
            "trace_id": trace_id,
            "prompt_type": prompt_type,
            "response_chars": response_chars,
            "response_tokens": response_tokens,
            "duration_ms": duration_ms,
            "cached": cached,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    @staticmethod
    def log_tool_call(trace_id: str, tool_name: str, 
                      input_summary: str, success: bool,
                      duration_ms: float, error: Optional[str] = None):
        """Log tool/router call."""
        extra = {
            "event": "tool_call",
            "trace_id": trace_id,
            "tool": tool_name,
            "input_summary": input_summary[:100],  # Truncate
            "success": success,
            "duration_ms": duration_ms,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        if error:
            extra["error"] = error[:200]  # Truncate error
        
        logger.info(f"[{trace_id}] Tool {tool_name}: {'success' if success else 'failed'}", extra=extra)
    
    @staticmethod
    def log_review_outcome(trace_id: str, draft_version: int,
                           overall_status: str, checklist_summary: Dict[str, int],
                           blocking_count: int, advisory_count: int,
                           repair_hints_count: int):
        """Log ReviewAgent outcome."""
        logger.info(f"[{trace_id}] Review: {overall_status}", extra={
            "event": "review_outcome",
            "trace_id": trace_id,
            "draft_version": draft_version,
            "overall_status": overall_status,
            "checklist_summary": checklist_summary,
            "blocking_count": blocking_count,
            "advisory_count": advisory_count,
            "repair_hints_count": repair_hints_count,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    @staticmethod
    def log_repair_action(trace_id: str, repair_cycle: int,
                          hints_processed: int, actions_taken: List[str]):
        """Log repair loop actions."""
        logger.info(f"[{trace_id}] Repair cycle {repair_cycle}", extra={
            "event": "repair_action",
            "trace_id": trace_id,
            "repair_cycle": repair_cycle,
            "hints_processed": hints_processed,
            "actions_taken": actions_taken,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    @staticmethod
    def log_partial_failure(trace_id: str, agent_name: str,
                            fallback_action: str, user_message: str):
        """Log partial failure with graceful degradation."""
        logger.warning(f"[{trace_id}] Partial failure: {agent_name}", extra={
            "event": "partial_failure",
            "trace_id": trace_id,
            "failed_agent": agent_name,
            "fallback_action": fallback_action,
            "user_message": user_message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    @staticmethod
    def log_plan_complete(trace_id: str, duration_ms: float,
                          final_status: str, repair_cycles: int,
                          days_count: int, cities_count: int):
        """Log plan completion summary."""
        logger.info(f"[{trace_id}] Plan complete: {final_status}", extra={
            "event": "plan_complete",
            "trace_id": trace_id,
            "total_duration_ms": duration_ms,
            "final_status": final_status,
            "repair_cycles": repair_cycles,
            "days_count": days_count,
            "cities_count": cities_count,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })


def timed_agent(agent_name: str):
    """Decorator to time agent execution and log observability."""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Extract trace_id if available from first arg (usually constraints or request)
            trace_id = "unknown"
            if args and hasattr(args[0], 'trace_id'):
                trace_id = args[0].trace_id
            
            start_time = time.time()
            ObservabilityLogger.log_agent_start(agent_name, trace_id)
            
            try:
                result = await func(self, *args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                version = getattr(result, 'version', 1)
                ObservabilityLogger.log_agent_complete(
                    agent_name, trace_id, duration_ms, 
                    artifact_version=version, success=True
                )
                return result
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                ObservabilityLogger.log_agent_complete(
                    agent_name, trace_id, duration_ms,
                    success=False, error_type=type(e).__name__
                )
                raise
        
        return wrapper
    return decorator
