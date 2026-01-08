"""
Saga MCP Server - Remote Development Access

Provides Claude Code with direct access to the production server:
- Read logs from any service
- Search and read files
- Deploy and restart services
- Query Neo4j database
- Get system stats and health
- Git operations

Authentication: Uses same API_KEY as the rest of the system.
"""

import os
import subprocess
import json
import re
from datetime import datetime, timedelta
from typing import Optional, List
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# =============================================================================
# Configuration
# =============================================================================

# Valid API keys (same as NGINX and workers use)
VALID_API_KEYS = {
    "785fc6c1647ff650b6b611509cc0a8f47009e6b743340503519d433f111fcf12",  # Key 1
    "a017a1af6fe167bdfcc554debb1c9a39e2ec75b93adde5a06d11e9a1361344f5",  # Key 2
    "646b3c9454024ac1f4a2abad35cf1b8d02678b7c98d84059bde4109956adeeec",  # Key 3
}

# Base paths for file operations (security whitelist)
ALLOWED_PATHS = [
    "/opt/saga-graph",
    "/app",
    "/var/log",
    "/tmp",
]

# Sensitive file patterns to block
BLOCKED_PATTERNS = [
    r"\.env$",
    r"\.env\.local$",
    r"credentials",
    r"secrets",
    r"\.pem$",
    r"\.key$",
    r"password",
    r"\.ssh",
]

# Docker services we can manage
ALLOWED_SERVICES = {
    "frontend", "apis", "worker-main", "worker-sources",
    "neo4j", "nginx", "qdrant", "mcp-server"
}

# Repos we can pull from
REPO_PATHS = {
    "saga-fe": "/opt/saga-graph/saga-fe",
    "saga-be": "/opt/saga-graph/saga-be",
    "graph-functions": "/opt/saga-graph/graph-functions",
    "victor_deployment": "/opt/saga-graph/victor_deployment",
}

# =============================================================================
# FastAPI App
# =============================================================================

app = FastAPI(
    title="Saga MCP Server",
    description="Remote development access for Claude Code",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


# =============================================================================
# Auth - Supports both header and query parameter for flexibility
# =============================================================================

async def verify_api_key(
    request: Request,
    api_key_from_header: str = Depends(api_key_header)
):
    """
    Verify API key from either:
    1. X-API-Key header (preferred)
    2. ?key= query parameter (for WebFetch/browser access)
    """
    # Try header first
    api_key = api_key_from_header

    # Fall back to query parameter
    if not api_key:
        api_key = request.query_params.get("key")

    if not api_key or api_key not in VALID_API_KEYS:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key. Use X-API-Key header or ?key= parameter"
        )
    return api_key


# =============================================================================
# Security Helpers
# =============================================================================

def is_path_allowed(path: str) -> bool:
    """Check if path is within allowed directories."""
    try:
        real_path = os.path.realpath(path)
        return any(real_path.startswith(allowed) for allowed in ALLOWED_PATHS)
    except Exception:
        return False


def is_path_blocked(path: str) -> bool:
    """Check if path matches blocked patterns (sensitive files)."""
    path_lower = path.lower()
    return any(re.search(pattern, path_lower) for pattern in BLOCKED_PATTERNS)


def validate_path(path: str) -> str:
    """Validate and return real path, or raise error."""
    if not is_path_allowed(path):
        raise HTTPException(403, f"Access denied: {path} is outside allowed directories")
    if is_path_blocked(path):
        raise HTTPException(403, f"Access denied: {path} matches blocked pattern")
    return os.path.realpath(path)


def run_command(cmd: str | list, timeout: int = 60, cwd: str = None) -> dict:
    """Run a shell command and return result."""
    try:
        if isinstance(cmd, str):
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd
            )
        else:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd
            )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "success": result.returncode == 0
        }
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "Command timed out", "returncode": -1, "success": False}
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "returncode": -1, "success": False}


# =============================================================================
# Request/Response Models
# =============================================================================

class ReadLogRequest(BaseModel):
    service: str = Field(..., description="Docker service name (e.g., 'worker-main', 'apis')")
    lines: int = Field(100, description="Number of lines to return", ge=1, le=10000)
    since: Optional[str] = Field(None, description="Show logs since (e.g., '1h', '30m', '2024-01-01')")


class SearchLogsRequest(BaseModel):
    pattern: str = Field(..., description="Regex pattern to search for")
    service: Optional[str] = Field(None, description="Limit to specific service")
    since: Optional[str] = Field("1h", description="How far back to search")
    lines: int = Field(500, description="Max lines to return")


class ReadFileRequest(BaseModel):
    path: str = Field(..., description="Absolute path to file")
    lines: Optional[int] = Field(None, description="Limit to last N lines")
    offset: Optional[int] = Field(None, description="Start from line N")


class SearchFilesRequest(BaseModel):
    pattern: str = Field(..., description="File name pattern (glob)")
    path: str = Field("/opt/saga-graph", description="Directory to search in")
    max_results: int = Field(100, description="Maximum files to return")


class GrepRequest(BaseModel):
    pattern: str = Field(..., description="Regex pattern to search for")
    path: str = Field("/opt/saga-graph", description="Directory to search in")
    file_pattern: Optional[str] = Field(None, description="File pattern (e.g., '*.py')")
    max_results: int = Field(50, description="Maximum matches to return")


class ListDirectoryRequest(BaseModel):
    path: str = Field(..., description="Directory path")
    recursive: bool = Field(False, description="List recursively")
    max_depth: int = Field(2, description="Max depth for recursive listing")


class DeployServiceRequest(BaseModel):
    service: str = Field(..., description="Service to deploy")
    pull: bool = Field(True, description="Git pull before build")
    no_cache: bool = Field(True, description="Build without cache")


class RestartServiceRequest(BaseModel):
    service: str = Field(..., description="Service to restart")


class GitRequest(BaseModel):
    repo: str = Field(..., description="Repo name (saga-fe, saga-be, graph-functions, victor_deployment)")
    command: str = Field(..., description="Git command (status, log, diff, pull)")


class CypherRequest(BaseModel):
    query: str = Field(..., description="Cypher query to execute")
    params: dict = Field(default_factory=dict, description="Query parameters")


class CommandRequest(BaseModel):
    command: str = Field(..., description="Command to run (limited commands only)")


class TopicDetailsRequest(BaseModel):
    topic_id: str = Field(..., description="Topic ID (e.g., 'us_macro', 'nordic_banks')")


class TopicArticlesRequest(BaseModel):
    topic_id: str = Field(..., description="Topic ID")
    limit: int = Field(20, description="Max articles to return", ge=1, le=100)
    perspective: Optional[str] = Field(None, description="Filter by perspective (risk, opportunity, trend, catalyst)")


class StrategyRequest(BaseModel):
    username: str = Field(..., description="Username")
    strategy_id: Optional[str] = Field(None, description="Strategy ID (optional, for specific strategy)")


class TriggerAnalysisRequest(BaseModel):
    topic_id: str = Field(..., description="Topic ID to analyze")
    force: bool = Field(False, description="Force re-analysis even if recent")


class HideArticleRequest(BaseModel):
    article_id: str = Field(..., description="Article ID to hide")
    reason: str = Field(..., description="Reason for hiding (for audit log)")


# =============================================================================
# NEW MODELS FOR GOD-TIER MCP TOOLS
# =============================================================================

class StrategyDetailRequest(BaseModel):
    strategy_id: str = Field(..., description="Strategy ID to get details for")
    username: str = Field(..., description="Username who owns the strategy")


class ListStrategyFilesRequest(BaseModel):
    username: str = Field(..., description="Username to list strategy files for")


class RawFileRequest(BaseModel):
    username: str = Field(..., description="Username")
    filename: str = Field(..., description="Filename (e.g., 'strategy_123.json' or 'users.json')")


class TopicAnalysisFullRequest(BaseModel):
    topic_id: str = Field(..., description="Topic ID")


class TopicRelationshipsRequest(BaseModel):
    topic_id: str = Field(..., description="Topic ID")


class TopicInfluenceMapRequest(BaseModel):
    topic_id: str = Field(..., description="Topic ID to map")
    depth: int = Field(2, description="How many hops to traverse", ge=1, le=4)


class TopicHistoryRequest(BaseModel):
    topic_id: str = Field(..., description="Topic ID")
    days: int = Field(30, description="Days of history to fetch")


class ExplorationPathsRequest(BaseModel):
    strategy_id: str = Field(..., description="Strategy ID")
    username: str = Field(..., description="Username")


class StrategyHealthCheckRequest(BaseModel):
    strategy_id: str = Field(..., description="Strategy ID")
    username: str = Field(..., description="Username")


class ArticleDetailRequest(BaseModel):
    article_id: str = Field(..., description="Article ID")


class SearchArticlesRequest(BaseModel):
    query: str = Field(..., description="Search query")
    topic_id: Optional[str] = Field(None, description="Filter by topic")
    since: Optional[str] = Field(None, description="ISO date string, e.g., 2024-01-01")
    limit: int = Field(20, description="Max results", ge=1, le=100)


# =============================================================================
# MCP PROTOCOL (JSON-RPC 2.0) - Native Claude Code Integration
# =============================================================================

# Define available MCP tools with their schemas
MCP_TOOLS = [
    {
        "name": "graph_health",
        "description": "Get comprehensive graph health diagnostics - topic/article counts, orphans, distribution stats, stale analysis detection",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "graph_stats",
        "description": "Get basic graph statistics - topic count, article count, relationship counts",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "all_topics",
        "description": "List all topics with their IDs, names, types, and categories",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "topic_details",
        "description": "Get full details for a specific topic including analysis context",
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic_id": {"type": "string", "description": "The topic ID (e.g., 'fed_policy', 'eurusd')"}
            },
            "required": ["topic_id"]
        }
    },
    {
        "name": "topic_articles",
        "description": "Get articles linked to a topic with importance scores",
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic_id": {"type": "string", "description": "The topic ID"},
                "limit": {"type": "integer", "description": "Max articles to return", "default": 20}
            },
            "required": ["topic_id"]
        }
    },
    {
        "name": "recent_articles",
        "description": "Get recently ingested articles with their topic mappings",
        "inputSchema": {
            "type": "object",
            "properties": {
                "hours": {"type": "integer", "description": "Look back N hours", "default": 24},
                "limit": {"type": "integer", "description": "Max articles to return", "default": 20}
            },
            "required": []
        }
    },
    {
        "name": "graph_query",
        "description": "Run pre-built analytical queries by name. Available: topic_distribution, orphan_articles, topic_connections, analysis_freshness, high_importance_articles, articles_per_topic_stats, recent_ingestion, topic_overlap, relationship_summary",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query_name": {
                    "type": "string",
                    "description": "Name of the pre-built query",
                    "enum": ["topic_distribution", "orphan_articles", "topic_connections", "analysis_freshness",
                             "high_importance_articles", "articles_per_topic_stats", "recent_ingestion",
                             "topic_overlap", "relationship_summary"]
                },
                "limit": {"type": "integer", "description": "Optional limit for results"}
            },
            "required": ["query_name"]
        }
    },
    {
        "name": "query_neo4j",
        "description": "Execute a custom read-only Cypher query on Neo4j",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Cypher query (SELECT/MATCH only, no mutations)"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "list_users",
        "description": "List all users in the system",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "user_strategies",
        "description": "Get strategies for a specific user",
        "inputSchema": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "Username to get strategies for"}
            },
            "required": ["username"]
        }
    },
    {
        "name": "trigger_analysis",
        "description": "Trigger re-analysis for a specific topic (requires confirmation)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic_id": {"type": "string", "description": "Topic ID to analyze"},
                "confirm": {"type": "boolean", "description": "Must be true to execute"}
            },
            "required": ["topic_id", "confirm"]
        }
    },
    {
        "name": "system_health",
        "description": "Get system health - CPU, memory, disk usage",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "docker_status",
        "description": "Get status of all Docker containers",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    # === FILE TOOLS ===
    {
        "name": "read_file",
        "description": "Read contents of a file from the server (within allowed paths)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to read"},
                "lines": {"type": "integer", "description": "Max lines to return (default 500)"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "search_files",
        "description": "Search for files by name pattern in a directory",
        "inputSchema": {
            "type": "object",
            "properties": {
                "directory": {"type": "string", "description": "Directory to search in"},
                "pattern": {"type": "string", "description": "File name pattern (glob)"}
            },
            "required": ["directory", "pattern"]
        }
    },
    {
        "name": "grep",
        "description": "Search for text pattern in files",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Text/regex pattern to search"},
                "path": {"type": "string", "description": "File or directory to search in"},
                "recursive": {"type": "boolean", "description": "Search recursively", "default": True}
            },
            "required": ["pattern", "path"]
        }
    },
    {
        "name": "list_directory",
        "description": "List contents of a directory",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path"},
                "recursive": {"type": "boolean", "description": "List recursively", "default": False}
            },
            "required": ["path"]
        }
    },
    # === LOG TOOLS ===
    {
        "name": "read_log",
        "description": "Read log file for a service (worker-main, worker-sources, apis, frontend, etc.)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "service": {"type": "string", "description": "Service name"},
                "lines": {"type": "integer", "description": "Number of lines to read", "default": 100}
            },
            "required": ["service"]
        }
    },
    {
        "name": "search_logs",
        "description": "Search for pattern in service logs",
        "inputSchema": {
            "type": "object",
            "properties": {
                "service": {"type": "string", "description": "Service name"},
                "pattern": {"type": "string", "description": "Search pattern"},
                "lines": {"type": "integer", "description": "Max lines to search", "default": 1000}
            },
            "required": ["service", "pattern"]
        }
    },
    {
        "name": "tail_logs",
        "description": "Get last N lines from service logs",
        "inputSchema": {
            "type": "object",
            "properties": {
                "service": {"type": "string", "description": "Service name"},
                "lines": {"type": "integer", "description": "Number of lines", "default": 50}
            },
            "required": ["service"]
        }
    },
    # === DEPLOYMENT TOOLS ===
    {
        "name": "restart_service",
        "description": "Restart a Docker service (requires confirmation)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "service": {"type": "string", "description": "Service to restart"},
                "confirm": {"type": "boolean", "description": "Must be true to execute"}
            },
            "required": ["service", "confirm"]
        }
    },
    {
        "name": "git_status",
        "description": "Get git status for a repository",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo": {"type": "string", "description": "Repository name (saga-fe, saga-be, graph-functions, victor_deployment)"}
            },
            "required": ["repo"]
        }
    },
    {
        "name": "daily_stats",
        "description": "Get daily statistics from the backend API",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    # =============================================================================
    # GOD-TIER TOOLS - Expert Strategy Analysis & System Visibility
    # =============================================================================
    # === STRATEGY DETAIL TOOLS ===
    {
        "name": "strategy_detail",
        "description": "Get FULL strategy details including thesis text, position, target, is_default flag, timestamps - everything needed to understand a strategy",
        "inputSchema": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "Username who owns the strategy"},
                "strategy_id": {"type": "string", "description": "Strategy ID"}
            },
            "required": ["username", "strategy_id"]
        }
    },
    {
        "name": "list_strategy_files",
        "description": "List all strategy JSON files for a user with metadata (filename, is_default, asset, created_at)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "Username to list strategies for"}
            },
            "required": ["username"]
        }
    },
    {
        "name": "raw_strategy_file",
        "description": "Read raw strategy JSON file - bypass API, see exactly what's stored on disk",
        "inputSchema": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "Username"},
                "strategy_id": {"type": "string", "description": "Strategy ID (will read strategy_{id}.json)"}
            },
            "required": ["username", "strategy_id"]
        }
    },
    {
        "name": "strategy_conversations",
        "description": "Get conversation history for a strategy",
        "inputSchema": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "Username"},
                "strategy_id": {"type": "string", "description": "Strategy ID"},
                "limit": {"type": "integer", "description": "Max conversations to return", "default": 10}
            },
            "required": ["username", "strategy_id"]
        }
    },
    # === TOPIC ANALYSIS TOOLS ===
    {
        "name": "topic_analysis_full",
        "description": "Get ALL 4 analysis timeframes for a topic: fundamental (6+ months), medium (3-6 mo), current (this week), and drivers",
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic_id": {"type": "string", "description": "Topic ID"}
            },
            "required": ["topic_id"]
        }
    },
    {
        "name": "topic_relationships",
        "description": "Get all relationships for a topic - INFLUENCES, CORRELATES_WITH, HEDGES, PEERS - with strength and mechanisms",
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic_id": {"type": "string", "description": "Topic ID"}
            },
            "required": ["topic_id"]
        }
    },
    {
        "name": "topic_influence_map",
        "description": "Get full influence graph for a topic - what it affects, what affects it, N hops deep for chain reaction analysis",
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic_id": {"type": "string", "description": "Topic ID"},
                "depth": {"type": "integer", "description": "How many hops to traverse (1-4)", "default": 2}
            },
            "required": ["topic_id"]
        }
    },
    {
        "name": "topic_coverage_gaps",
        "description": "Find topics with stale/missing analysis - identify where the system needs attention",
        "inputSchema": {
            "type": "object",
            "properties": {
                "stale_days": {"type": "integer", "description": "Consider analysis stale after N days", "default": 7}
            },
            "required": []
        }
    },
    # === PIPELINE & AGENT TOOLS ===
    {
        "name": "topic_mapping_result",
        "description": "See how a strategy was mapped to topics - which topics, why, confidence - understand Topic Mapper output",
        "inputSchema": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "Username"},
                "strategy_id": {"type": "string", "description": "Strategy ID"}
            },
            "required": ["username", "strategy_id"]
        }
    },
    {
        "name": "exploration_paths",
        "description": "Get chain reactions discovered by Exploration Agent for a strategy - the 3-6 hop connections",
        "inputSchema": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "Username"},
                "strategy_id": {"type": "string", "description": "Strategy ID"}
            },
            "required": ["username", "strategy_id"]
        }
    },
    {
        "name": "agent_outputs",
        "description": "Get raw outputs from specific agents (risk_assessor, opportunity_finder, exploration, strategy_writer) for a strategy",
        "inputSchema": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "Username"},
                "strategy_id": {"type": "string", "description": "Strategy ID"},
                "agent": {"type": "string", "description": "Agent name (optional - returns all if not specified)", "enum": ["risk_assessor", "opportunity_finder", "exploration", "strategy_writer", "topic_mapper"]}
            },
            "required": ["username", "strategy_id"]
        }
    },
    # === WORKER & PIPELINE MONITORING ===
    {
        "name": "worker_status",
        "description": "Status of all workers (ingest, write, sources) with last run times, success rates",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "failed_jobs",
        "description": "Recent failures in any pipeline (ingestion, analysis, strategy writing) - catch issues early",
        "inputSchema": {
            "type": "object",
            "properties": {
                "hours": {"type": "integer", "description": "Look back N hours", "default": 24}
            },
            "required": []
        }
    },
    {
        "name": "processing_backlog",
        "description": "What's waiting to be processed - articles to classify, topics to analyze, strategies to write",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "ingestion_stats",
        "description": "Article ingestion stats - count by source, by day, success rate, recent trends",
        "inputSchema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Days of history", "default": 7}
            },
            "required": []
        }
    },
    # === ARTICLE TOOLS ===
    {
        "name": "article_detail",
        "description": "Get full article content + classification + topic assignments + importance scores",
        "inputSchema": {
            "type": "object",
            "properties": {
                "article_id": {"type": "string", "description": "Article ID"}
            },
            "required": ["article_id"]
        }
    },
    {
        "name": "search_articles",
        "description": "Search articles by keyword, date range, topic - find relevant content",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "topic_id": {"type": "string", "description": "Filter by topic (optional)"},
                "since": {"type": "string", "description": "ISO date (e.g., 2024-01-01)"},
                "limit": {"type": "integer", "description": "Max results", "default": 20}
            },
            "required": ["query"]
        }
    },
    {
        "name": "source_stats",
        "description": "Article counts by source, quality indicators, recent trends - understand content quality",
        "inputSchema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Days of history", "default": 7}
            },
            "required": []
        }
    },
    # === CROSS-CUTTING ANALYSIS ===
    {
        "name": "strategy_health_check",
        "description": "Diagnose why a strategy might be getting poor analysis - check topic mapping, analysis freshness, coverage gaps",
        "inputSchema": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "Username"},
                "strategy_id": {"type": "string", "description": "Strategy ID"}
            },
            "required": ["username", "strategy_id"]
        }
    },
    {
        "name": "cross_strategy_insights",
        "description": "Find overlapping topics/risks across ALL strategies - identify concentration risks, correlated exposures",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "system_activity_log",
        "description": "Recent system activity - analyses run, strategies updated, articles ingested, errors",
        "inputSchema": {
            "type": "object",
            "properties": {
                "hours": {"type": "integer", "description": "Look back N hours", "default": 24}
            },
            "required": []
        }
    }
]


class MCPRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[int] = None
    method: str
    params: Optional[dict] = None


@app.post("/mcp")
@app.post("/mcp/")
async def mcp_jsonrpc(request: MCPRequest, raw_request: Request):
    """
    MCP JSON-RPC 2.0 endpoint for native Claude Code integration.

    Supports:
    - initialize: Handshake and capability exchange
    - tools/list: List available tools with schemas
    - tools/call: Execute a tool by name
    """
    # Check API key (from header or query param)
    api_key = raw_request.headers.get("X-API-Key") or raw_request.query_params.get("key")

    # Allow initialize without auth for discovery
    if request.method != "initialize":
        if not api_key or api_key not in VALID_API_KEYS:
            return {
                "jsonrpc": "2.0",
                "id": request.id,
                "error": {
                    "code": -32001,
                    "message": "Authentication required. Provide X-API-Key header."
                }
            }

    try:
        if request.method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request.id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {"listChanged": False}
                    },
                    "serverInfo": {
                        "name": "saga-graph-mcp",
                        "version": "2.0.0"
                    }
                }
            }

        elif request.method == "notifications/initialized":
            # Client acknowledges initialization - no response needed
            return {"jsonrpc": "2.0", "id": request.id, "result": {}}

        elif request.method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request.id,
                "result": {
                    "tools": MCP_TOOLS
                }
            }

        elif request.method == "tools/call":
            params = request.params or {}
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            result = await execute_mcp_tool(tool_name, arguments)

            return {
                "jsonrpc": "2.0",
                "id": request.id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result, indent=2, default=str)}]
                }
            }

        else:
            return {
                "jsonrpc": "2.0",
                "id": request.id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {request.method}"
                }
            }

    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": request.id,
            "error": {
                "code": -32603,
                "message": str(e)
            }
        }


async def execute_mcp_tool(tool_name: str, arguments: dict) -> dict:
    """Execute an MCP tool and return results."""

    if tool_name == "graph_health":
        response = await graph_health()
        return response

    elif tool_name == "graph_stats":
        response = await graph_stats()
        return response

    elif tool_name == "all_topics":
        response = await all_topics()
        return response

    elif tool_name == "topic_details":
        req = TopicDetailsRequest(topic_id=arguments.get("topic_id"))
        response = await topic_details(req)
        return response

    elif tool_name == "topic_articles":
        req = TopicArticlesRequest(
            topic_id=arguments.get("topic_id"),
            limit=arguments.get("limit", 20)
        )
        response = await topic_articles(req)
        return response

    elif tool_name == "recent_articles":
        response = await recent_articles(
            limit=arguments.get("limit", 20),
            hours=arguments.get("hours", 24)
        )
        return response

    elif tool_name == "graph_query":
        response = await graph_query(
            query_name=arguments.get("query_name"),
            limit=arguments.get("limit")
        )
        return response

    elif tool_name == "query_neo4j":
        req = QueryRequest(query=arguments.get("query"))
        response = await query_neo4j(req)
        return response

    elif tool_name == "list_users":
        response = await list_users()
        return response

    elif tool_name == "user_strategies":
        req = StrategyRequest(username=arguments.get("username"))
        response = await user_strategies(req)
        return response

    elif tool_name == "trigger_analysis":
        if not arguments.get("confirm"):
            return {"error": "Must set confirm=true to trigger analysis"}
        req = TriggerAnalysisRequest(
            topic_id=arguments.get("topic_id"),
            force=arguments.get("force", False)
        )
        response = await trigger_analysis(req)
        return response

    elif tool_name == "system_health":
        response = await system_health()
        return response

    elif tool_name == "docker_status":
        response = await docker_status()
        return response

    # === FILE TOOLS ===
    elif tool_name == "read_file":
        req = ReadFileRequest(
            path=arguments.get("path"),
            lines=arguments.get("lines", 500)
        )
        response = await read_file(req)
        return response

    elif tool_name == "search_files":
        req = SearchFilesRequest(
            directory=arguments.get("directory"),
            pattern=arguments.get("pattern")
        )
        response = await search_files(req)
        return response

    elif tool_name == "grep":
        req = GrepRequest(
            pattern=arguments.get("pattern"),
            path=arguments.get("path"),
            recursive=arguments.get("recursive", True)
        )
        response = await grep(req)
        return response

    elif tool_name == "list_directory":
        req = ListDirRequest(
            path=arguments.get("path"),
            recursive=arguments.get("recursive", False)
        )
        response = await list_directory(req)
        return response

    # === LOG TOOLS ===
    elif tool_name == "read_log":
        req = LogRequest(
            service=arguments.get("service"),
            lines=arguments.get("lines", 100)
        )
        response = await read_log(req)
        return response

    elif tool_name == "search_logs":
        req = SearchLogRequest(
            service=arguments.get("service"),
            pattern=arguments.get("pattern"),
            lines=arguments.get("lines", 1000)
        )
        response = await search_logs(req)
        return response

    elif tool_name == "tail_logs":
        response = await tail_logs(
            service=arguments.get("service"),
            lines=arguments.get("lines", 50)
        )
        return response

    # === DEPLOYMENT TOOLS ===
    elif tool_name == "restart_service":
        if not arguments.get("confirm"):
            return {"error": "Must set confirm=true to restart service"}
        req = RestartRequest(service=arguments.get("service"))
        response = await restart_service(req)
        return response

    elif tool_name == "git_status":
        req = GitRequest(
            repo=arguments.get("repo"),
            command="status"
        )
        response = await git(req)
        return response

    elif tool_name == "daily_stats":
        response = await daily_stats()
        return response

    # =============================================================================
    # GOD-TIER TOOLS - New handlers
    # =============================================================================

    # === STRATEGY DETAIL TOOLS ===
    elif tool_name == "strategy_detail":
        response = await strategy_detail(
            username=arguments.get("username"),
            strategy_id=arguments.get("strategy_id")
        )
        return response

    elif tool_name == "list_strategy_files":
        response = await list_strategy_files(
            username=arguments.get("username")
        )
        return response

    elif tool_name == "raw_strategy_file":
        response = await raw_strategy_file(
            username=arguments.get("username"),
            strategy_id=arguments.get("strategy_id")
        )
        return response

    elif tool_name == "strategy_conversations":
        response = await strategy_conversations(
            username=arguments.get("username"),
            strategy_id=arguments.get("strategy_id"),
            limit=arguments.get("limit", 10)
        )
        return response

    # === TOPIC ANALYSIS TOOLS ===
    elif tool_name == "topic_analysis_full":
        response = await topic_analysis_full(
            topic_id=arguments.get("topic_id")
        )
        return response

    elif tool_name == "topic_relationships":
        response = await topic_relationships(
            topic_id=arguments.get("topic_id")
        )
        return response

    elif tool_name == "topic_influence_map":
        response = await topic_influence_map(
            topic_id=arguments.get("topic_id"),
            depth=arguments.get("depth", 2)
        )
        return response

    elif tool_name == "topic_coverage_gaps":
        response = await topic_coverage_gaps(
            stale_days=arguments.get("stale_days", 7)
        )
        return response

    # === PIPELINE & AGENT TOOLS ===
    elif tool_name == "topic_mapping_result":
        response = await topic_mapping_result(
            username=arguments.get("username"),
            strategy_id=arguments.get("strategy_id")
        )
        return response

    elif tool_name == "exploration_paths":
        response = await exploration_paths(
            username=arguments.get("username"),
            strategy_id=arguments.get("strategy_id")
        )
        return response

    elif tool_name == "agent_outputs":
        response = await agent_outputs(
            username=arguments.get("username"),
            strategy_id=arguments.get("strategy_id"),
            agent=arguments.get("agent")
        )
        return response

    # === WORKER & PIPELINE MONITORING ===
    elif tool_name == "worker_status":
        response = await worker_status()
        return response

    elif tool_name == "failed_jobs":
        response = await failed_jobs(
            hours=arguments.get("hours", 24)
        )
        return response

    elif tool_name == "processing_backlog":
        response = await processing_backlog()
        return response

    elif tool_name == "ingestion_stats":
        response = await ingestion_stats(
            days=arguments.get("days", 7)
        )
        return response

    # === ARTICLE TOOLS ===
    elif tool_name == "article_detail":
        response = await article_detail(
            article_id=arguments.get("article_id")
        )
        return response

    elif tool_name == "search_articles":
        response = await search_articles_tool(
            query=arguments.get("query"),
            topic_id=arguments.get("topic_id"),
            since=arguments.get("since"),
            limit=arguments.get("limit", 20)
        )
        return response

    elif tool_name == "source_stats":
        response = await source_stats(
            days=arguments.get("days", 7)
        )
        return response

    # === CROSS-CUTTING ANALYSIS ===
    elif tool_name == "strategy_health_check":
        response = await strategy_health_check(
            username=arguments.get("username"),
            strategy_id=arguments.get("strategy_id")
        )
        return response

    elif tool_name == "cross_strategy_insights":
        response = await cross_strategy_insights()
        return response

    elif tool_name == "system_activity_log":
        response = await system_activity_log(
            hours=arguments.get("hours", 24)
        )
        return response

    else:
        raise ValueError(f"Unknown tool: {tool_name}")


# =============================================================================
# Health & Status Endpoints
# =============================================================================

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "mcp-server", "timestamp": datetime.utcnow().isoformat()}


@app.get("/mcp/status", dependencies=[Depends(verify_api_key)])
async def mcp_status():
    """Get MCP server status and available tools."""
    return {
        "status": "running",
        "version": "2.0.0",
        "tools": {
            "logs": ["read_log", "search_logs", "tail_logs"],
            "files": ["read_file", "search_files", "grep", "list_directory"],
            "deployment": ["deploy_service", "restart_service", "docker_status"],
            "git": ["git (status/log/diff/pull)"],
            "database": ["query_neo4j"],
            "system": ["system_health", "daily_stats", "run_command"],
            "graph": ["graph_stats", "graph_health", "graph_query/{name}", "graph_queries", "all_topics", "topic_details", "topic_articles", "recent_articles"],
            "strategies": ["list_users", "user_strategies", "strategy_analysis", "strategy_topics"],
            "actions": ["hide_article", "trigger_analysis"],
        },
        "allowed_services": list(ALLOWED_SERVICES),
        "allowed_repos": list(REPO_PATHS.keys()),
    }


# =============================================================================
# LOG TOOLS
# =============================================================================

@app.post("/mcp/tools/read_log", dependencies=[Depends(verify_api_key)])
async def read_log(req: ReadLogRequest):
    """Read logs from a Docker service."""
    if req.service not in ALLOWED_SERVICES:
        raise HTTPException(400, f"Unknown service: {req.service}. Allowed: {ALLOWED_SERVICES}")

    cmd = ["docker", "logs", "--tail", str(req.lines)]
    if req.since:
        cmd.extend(["--since", req.since])
    cmd.append(req.service)

    result = run_command(cmd, timeout=30)
    return {
        "service": req.service,
        "lines_requested": req.lines,
        "logs": result["stdout"],
        "stderr": result["stderr"],
        "success": result["success"]
    }


@app.post("/mcp/tools/search_logs", dependencies=[Depends(verify_api_key)])
async def search_logs(req: SearchLogsRequest):
    """Search logs for a pattern across services."""
    services = [req.service] if req.service else list(ALLOWED_SERVICES)
    results = {}

    for service in services:
        if service not in ALLOWED_SERVICES:
            continue
        cmd = f"docker logs --since {req.since} {service} 2>&1 | grep -E '{req.pattern}' | tail -n {req.lines}"
        result = run_command(cmd, timeout=30)
        if result["stdout"].strip():
            results[service] = result["stdout"].strip().split("\n")

    return {
        "pattern": req.pattern,
        "since": req.since,
        "matches": results,
        "total_matches": sum(len(v) for v in results.values())
    }


@app.get("/mcp/tools/tail_logs/{service}", dependencies=[Depends(verify_api_key)])
async def tail_logs(service: str, lines: int = 50):
    """Get the most recent logs from a service (for polling)."""
    if service not in ALLOWED_SERVICES:
        raise HTTPException(400, f"Unknown service: {service}")

    result = run_command(["docker", "logs", "--tail", str(lines), service], timeout=10)
    return {
        "service": service,
        "lines": lines,
        "logs": result["stdout"],
        "timestamp": datetime.utcnow().isoformat()
    }


# =============================================================================
# FILE TOOLS
# =============================================================================

@app.post("/mcp/tools/read_file", dependencies=[Depends(verify_api_key)])
async def read_file(req: ReadFileRequest):
    """Read a file from the server."""
    path = validate_path(req.path)

    if not os.path.exists(path):
        raise HTTPException(404, f"File not found: {path}")
    if not os.path.isfile(path):
        raise HTTPException(400, f"Not a file: {path}")

    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            if req.offset:
                # Skip to offset
                for _ in range(req.offset):
                    f.readline()

            if req.lines:
                content = ''.join(f.readline() for _ in range(req.lines))
            else:
                content = f.read()

        # Truncate if too large
        max_size = 100000  # 100KB
        truncated = len(content) > max_size
        if truncated:
            content = content[:max_size]

        return {
            "path": path,
            "content": content,
            "truncated": truncated,
            "size": os.path.getsize(path)
        }
    except Exception as e:
        raise HTTPException(500, f"Error reading file: {e}")


@app.post("/mcp/tools/search_files", dependencies=[Depends(verify_api_key)])
async def search_files(req: SearchFilesRequest):
    """Search for files by name pattern."""
    path = validate_path(req.path)

    cmd = f"find {path} -name '{req.pattern}' -type f 2>/dev/null | head -n {req.max_results}"
    result = run_command(cmd, timeout=30)

    files = [f for f in result["stdout"].strip().split("\n") if f]

    return {
        "pattern": req.pattern,
        "path": path,
        "files": files,
        "count": len(files)
    }


@app.post("/mcp/tools/grep", dependencies=[Depends(verify_api_key)])
async def grep(req: GrepRequest):
    """Search file contents for a pattern."""
    path = validate_path(req.path)

    cmd = f"grep -rn --include='{req.file_pattern or '*'}' -E '{req.pattern}' {path} 2>/dev/null | head -n {req.max_results}"
    result = run_command(cmd, timeout=60)

    matches = []
    for line in result["stdout"].strip().split("\n"):
        if line and ":" in line:
            parts = line.split(":", 2)
            if len(parts) >= 3:
                matches.append({
                    "file": parts[0],
                    "line": int(parts[1]) if parts[1].isdigit() else 0,
                    "content": parts[2]
                })

    return {
        "pattern": req.pattern,
        "path": path,
        "file_pattern": req.file_pattern,
        "matches": matches,
        "count": len(matches)
    }


@app.post("/mcp/tools/list_directory", dependencies=[Depends(verify_api_key)])
async def list_directory(req: ListDirectoryRequest):
    """List directory contents."""
    path = validate_path(req.path)

    if not os.path.exists(path):
        raise HTTPException(404, f"Directory not found: {path}")
    if not os.path.isdir(path):
        raise HTTPException(400, f"Not a directory: {path}")

    if req.recursive:
        cmd = f"find {path} -maxdepth {req.max_depth} -type f -o -type d 2>/dev/null | head -n 500"
        result = run_command(cmd, timeout=30)
        items = [f for f in result["stdout"].strip().split("\n") if f]
    else:
        items = []
        for item in os.listdir(path):
            full_path = os.path.join(path, item)
            item_type = "dir" if os.path.isdir(full_path) else "file"
            size = os.path.getsize(full_path) if os.path.isfile(full_path) else 0
            items.append({
                "name": item,
                "type": item_type,
                "size": size,
                "path": full_path
            })

    return {
        "path": path,
        "items": items,
        "count": len(items)
    }


# =============================================================================
# DEPLOYMENT TOOLS
# =============================================================================

@app.post("/mcp/tools/deploy_service", dependencies=[Depends(verify_api_key)])
async def deploy_service(req: DeployServiceRequest):
    """Deploy a service (git pull + docker build + restart)."""
    if req.service not in ALLOWED_SERVICES:
        raise HTTPException(400, f"Unknown service: {req.service}")

    # Map services to their repos
    service_to_repo = {
        "frontend": "saga-fe",
        "apis": "saga-be",
        "worker-main": "graph-functions",
        "worker-sources": "graph-functions",
    }

    steps = []

    # Git pull if requested
    if req.pull and req.service in service_to_repo:
        repo = service_to_repo[req.service]
        repo_path = REPO_PATHS.get(repo)
        if repo_path:
            result = run_command(f"cd {repo_path} && git pull", timeout=60)
            steps.append({
                "step": "git_pull",
                "repo": repo,
                "success": result["success"],
                "output": result["stdout"] + result["stderr"]
            })

    # Docker compose build
    compose_path = "/opt/saga-graph/victor_deployment"
    cache_flag = "--no-cache" if req.no_cache else ""

    result = run_command(
        f"cd {compose_path} && docker compose build {cache_flag} {req.service}",
        timeout=600  # 10 min for build
    )
    steps.append({
        "step": "docker_build",
        "success": result["success"],
        "output": result["stdout"][-2000:] + result["stderr"][-2000:]  # Truncate
    })

    # Docker compose up
    if result["success"]:
        result = run_command(
            f"cd {compose_path} && docker compose up -d {req.service}",
            timeout=120
        )
        steps.append({
            "step": "docker_up",
            "success": result["success"],
            "output": result["stdout"] + result["stderr"]
        })

    return {
        "service": req.service,
        "steps": steps,
        "overall_success": all(s["success"] for s in steps)
    }


@app.post("/mcp/tools/restart_service", dependencies=[Depends(verify_api_key)])
async def restart_service(req: RestartServiceRequest):
    """Restart a Docker service."""
    if req.service not in ALLOWED_SERVICES:
        raise HTTPException(400, f"Unknown service: {req.service}")

    result = run_command(
        f"cd /opt/saga-graph/victor_deployment && docker compose restart {req.service}",
        timeout=120
    )

    return {
        "service": req.service,
        "success": result["success"],
        "output": result["stdout"] + result["stderr"]
    }


@app.get("/mcp/tools/docker_status", dependencies=[Depends(verify_api_key)])
async def docker_status():
    """Get status of all Docker containers."""
    result = run_command(
        "docker ps -a --format '{{json .}}'",
        timeout=10
    )

    containers = []
    for line in result["stdout"].strip().split("\n"):
        if line:
            try:
                containers.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    # Get more details for our services
    detailed = {}
    for service in ALLOWED_SERVICES:
        inspect = run_command(
            f"docker inspect {service} --format '{{{{.State.Status}}}} {{{{.State.StartedAt}}}}'",
            timeout=5
        )
        if inspect["success"]:
            parts = inspect["stdout"].strip().split(" ")
            detailed[service] = {
                "status": parts[0] if parts else "unknown",
                "started_at": parts[1] if len(parts) > 1 else "unknown"
            }

    return {
        "containers": containers,
        "services": detailed
    }


# =============================================================================
# GIT TOOLS
# =============================================================================

@app.post("/mcp/tools/git", dependencies=[Depends(verify_api_key)])
async def git_operation(req: GitRequest):
    """Run git operations on a repo."""
    if req.repo not in REPO_PATHS:
        raise HTTPException(400, f"Unknown repo: {req.repo}. Allowed: {list(REPO_PATHS.keys())}")

    repo_path = REPO_PATHS[req.repo]

    # Whitelist safe git commands
    allowed_commands = {"status", "log", "diff", "pull", "branch", "fetch"}
    cmd_parts = req.command.split()
    if not cmd_parts or cmd_parts[0] not in allowed_commands:
        raise HTTPException(400, f"Command not allowed. Allowed: {allowed_commands}")

    # Build full command
    if cmd_parts[0] == "log":
        cmd = f"cd {repo_path} && git log --oneline -20"
    elif cmd_parts[0] == "diff":
        cmd = f"cd {repo_path} && git diff HEAD~1"
    else:
        cmd = f"cd {repo_path} && git {req.command}"

    result = run_command(cmd, timeout=60)

    return {
        "repo": req.repo,
        "command": req.command,
        "success": result["success"],
        "output": result["stdout"] + result["stderr"]
    }


# =============================================================================
# DATABASE TOOLS
# =============================================================================

@app.post("/mcp/tools/query_neo4j", dependencies=[Depends(verify_api_key)])
async def query_neo4j(req: CypherRequest):
    """Execute a Cypher query against Neo4j."""
    # Safety check - only allow read queries
    query_upper = req.query.upper().strip()
    write_keywords = ["CREATE", "MERGE", "DELETE", "SET", "REMOVE", "DROP"]

    if any(kw in query_upper for kw in write_keywords):
        raise HTTPException(400, "Write queries not allowed via MCP. Use read-only queries.")

    # Execute via docker
    escaped_query = req.query.replace('"', '\\"').replace("'", "\\'")
    cmd = f'''docker exec -w /app/graph-functions apis python -c "
from src.graph.neo4j_client import run_cypher
import json
results = run_cypher('{escaped_query}', {json.dumps(req.params)})
print(json.dumps(results, default=str))
"'''

    result = run_command(cmd, timeout=30)

    if result["success"]:
        try:
            data = json.loads(result["stdout"])
            return {"query": req.query, "results": data, "success": True}
        except json.JSONDecodeError:
            return {"query": req.query, "raw_output": result["stdout"], "success": True}
    else:
        return {"query": req.query, "error": result["stderr"], "success": False}


# =============================================================================
# SYSTEM TOOLS
# =============================================================================

@app.get("/mcp/tools/system_health", dependencies=[Depends(verify_api_key)])
async def system_health():
    """Get system health (CPU, memory, disk)."""
    # CPU load
    cpu = run_command("cat /proc/loadavg", timeout=5)
    cpu_load = cpu["stdout"].split()[:3] if cpu["success"] else ["unknown"]

    # Memory
    mem = run_command("free -h | grep Mem", timeout=5)
    mem_parts = mem["stdout"].split() if mem["success"] else []

    # Disk
    disk = run_command("df -h / | tail -1", timeout=5)
    disk_parts = disk["stdout"].split() if disk["success"] else []

    # Docker
    docker = await docker_status()

    return {
        "cpu_load": cpu_load,
        "memory": {
            "total": mem_parts[1] if len(mem_parts) > 1 else "unknown",
            "used": mem_parts[2] if len(mem_parts) > 2 else "unknown",
            "free": mem_parts[3] if len(mem_parts) > 3 else "unknown",
        },
        "disk": {
            "total": disk_parts[1] if len(disk_parts) > 1 else "unknown",
            "used": disk_parts[2] if len(disk_parts) > 2 else "unknown",
            "available": disk_parts[3] if len(disk_parts) > 3 else "unknown",
            "use_percent": disk_parts[4] if len(disk_parts) > 4 else "unknown",
        },
        "docker_services": docker["services"],
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/mcp/tools/daily_stats", dependencies=[Depends(verify_api_key)])
async def daily_stats():
    """Get daily stats from the backend API."""
    result = run_command(
        "curl -s http://apis:8000/api/stats",
        timeout=10
    )

    if result["success"]:
        try:
            return json.loads(result["stdout"])
        except json.JSONDecodeError:
            return {"raw": result["stdout"]}
    else:
        return {"error": result["stderr"]}


# =============================================================================
# UTILITY TOOLS
# =============================================================================

@app.post("/mcp/tools/run_command", dependencies=[Depends(verify_api_key)])
async def run_limited_command(req: CommandRequest):
    """Run a limited set of safe commands."""
    # Whitelist of allowed command prefixes
    allowed_prefixes = [
        "docker ps",
        "docker logs",
        "docker inspect",
        "docker stats --no-stream",
        "df -h",
        "free",
        "uptime",
        "ps aux",
        "netstat -tlnp",
        "ls ",
        "cat /proc/",
        "wc -l",
        "head ",
        "tail ",
    ]

    if not any(req.command.startswith(prefix) for prefix in allowed_prefixes):
        raise HTTPException(
            400,
            f"Command not allowed. Must start with one of: {allowed_prefixes}"
        )

    result = run_command(req.command, timeout=30)

    return {
        "command": req.command,
        "success": result["success"],
        "stdout": result["stdout"],
        "stderr": result["stderr"]
    }


# =============================================================================
# GRAPH TOOLS - Read-only graph inspection
# =============================================================================

@app.get("/mcp/tools/graph_stats", dependencies=[Depends(verify_api_key)])
async def graph_stats():
    """Get overall graph statistics - topic count, article count, relationships."""
    cmd = '''docker exec -w /app/graph-functions apis python -c "
from src.graph.neo4j_client import run_cypher
import json

topic_count = run_cypher('MATCH (t:Topic) RETURN count(t) as count')[0]['count']
article_count = run_cypher('MATCH (a:Article) RETURN count(a) as count')[0]['count']
about_count = run_cypher('MATCH ()-[r:ABOUT]->() RETURN count(r) as count')[0]['count']
topic_rels = run_cypher('MATCH (:Topic)-[r:INFLUENCES|CORRELATES_WITH]->(:Topic) RETURN count(r) as count')[0]['count']
orphan_count = run_cypher('MATCH (a:Article) WHERE NOT (a)-[:ABOUT]->(:Topic) RETURN count(a) as count')[0]['count']
recent = run_cypher('MATCH (a:Article) WHERE a.created_at IS NOT NULL RETURN a.id, a.title, a.created_at ORDER BY a.created_at DESC LIMIT 5')
top_topics = run_cypher('MATCH (a:Article)-[r:ABOUT]->(t:Topic) RETURN t.id as topic_id, t.name as topic_name, count(a) as article_count ORDER BY article_count DESC LIMIT 10')

print(json.dumps({
    'topic_count': topic_count,
    'article_count': article_count,
    'about_relationships': about_count,
    'topic_relationships': topic_rels,
    'orphan_articles': orphan_count,
    'avg_articles_per_topic': round(about_count / max(topic_count, 1), 1),
    'recent_articles': recent,
    'top_topics_by_articles': top_topics
}, default=str))
"'''
    result = run_command(cmd, timeout=30)

    if result["success"]:
        try:
            return json.loads(result["stdout"])
        except json.JSONDecodeError:
            return {"raw_output": result["stdout"], "success": True}
    return {"error": result["stderr"], "success": False}


@app.get("/mcp/tools/all_topics", dependencies=[Depends(verify_api_key)])
async def all_topics():
    """Get all topics with key fields."""
    cmd = '''docker exec -w /app/graph-functions apis python -c "
from src.graph.ops.topic import get_all_topics
import json

topics = get_all_topics(fields=['id', 'name', 'type', 'category', 'last_updated'])
print(json.dumps(topics, default=str))
"'''
    result = run_command(cmd, timeout=30)

    if result["success"]:
        try:
            topics = json.loads(result["stdout"])
            return {"topics": topics, "count": len(topics)}
        except json.JSONDecodeError:
            return {"raw_output": result["stdout"], "success": True}
    return {"error": result["stderr"], "success": False}


@app.post("/mcp/tools/topic_details", dependencies=[Depends(verify_api_key)])
async def topic_details(req: TopicDetailsRequest):
    """Get full details for a specific topic including analysis."""
    cmd = f'''docker exec -w /app/graph-functions apis python -c "
from src.graph.ops.topic import get_topic_by_id, get_topic_context
import json

try:
    topic = get_topic_by_id('{req.topic_id}')
    context = get_topic_context('{req.topic_id}')
    print(json.dumps({{'topic': topic, 'context': context}}, default=str))
except Exception as e:
    print(json.dumps({{'error': str(e)}}))
"'''
    result = run_command(cmd, timeout=30)

    if result["success"]:
        try:
            return json.loads(result["stdout"])
        except json.JSONDecodeError:
            return {"raw_output": result["stdout"], "success": True}
    return {"error": result["stderr"], "success": False}


@app.post("/mcp/tools/topic_articles", dependencies=[Depends(verify_api_key)])
async def topic_articles(req: TopicArticlesRequest):
    """Get articles linked to a topic with their importance tiers."""
    cmd = f'''docker exec -w /app/graph-functions apis python -c "
from src.graph.neo4j_client import run_cypher
import json

query = \\"""
MATCH (a:Article)-[r:ABOUT]->(t:Topic {{id: '{req.topic_id}'}})
WHERE a.status IS NULL OR a.status <> 'hidden'
RETURN a.id as id, a.title as title, a.source as source,
       r.timeframe as timeframe,
       r.importance_risk as importance_risk,
       r.importance_opportunity as importance_opportunity,
       r.importance_trend as importance_trend,
       r.importance_catalyst as importance_catalyst,
       r.motivation as motivation,
       a.published_at as published
ORDER BY
    COALESCE(r.importance_risk, 0) + COALESCE(r.importance_opportunity, 0) +
    COALESCE(r.importance_trend, 0) + COALESCE(r.importance_catalyst, 0) DESC,
    a.published_at DESC
LIMIT {req.limit}
\\"""
results = run_cypher(query)
print(json.dumps(results, default=str))
"'''
    result = run_command(cmd, timeout=30)

    if result["success"]:
        try:
            articles = json.loads(result["stdout"])
            return {"topic_id": req.topic_id, "articles": articles, "count": len(articles)}
        except json.JSONDecodeError:
            return {"raw_output": result["stdout"], "success": True}
    return {"error": result["stderr"], "success": False}


@app.get("/mcp/tools/recent_articles", dependencies=[Depends(verify_api_key)])
async def recent_articles(limit: int = 20, hours: int = 24):
    """Get recently ingested articles."""
    cmd = f'''docker exec -w /app/graph-functions apis python -c "
from src.graph.neo4j_client import run_cypher
from datetime import datetime, timedelta
import json

cutoff = (datetime.utcnow() - timedelta(hours={hours})).isoformat()

query = \\"""
MATCH (a:Article)
WHERE a.created_at > $cutoff
OPTIONAL MATCH (a)-[r:ABOUT]->(t:Topic)
RETURN a.id as id, a.title as title, a.source as source,
       a.created_at as created_at,
       collect(t.id) as topics
ORDER BY a.created_at DESC
LIMIT {limit}
\\"""
results = run_cypher(query, {{'cutoff': cutoff}})
print(json.dumps(results, default=str))
"'''
    result = run_command(cmd, timeout=30)

    if result["success"]:
        try:
            articles = json.loads(result["stdout"])
            return {"articles": articles, "count": len(articles), "hours": hours}
        except json.JSONDecodeError:
            return {"raw_output": result["stdout"], "success": True}
    return {"error": result["stderr"], "success": False}


@app.get("/mcp/tools/graph_health", dependencies=[Depends(verify_api_key)])
async def graph_health():
    """Comprehensive graph health diagnostics for GOD-TIER visibility."""
    cmd = """docker exec -w /app/graph-functions apis python -c "
from src.graph.neo4j_client import run_cypher
from datetime import datetime, timedelta
import json

# === BASIC COUNTS ===
topic_count = run_cypher('MATCH (t:Topic) RETURN count(t) as count')[0]['count']
article_count = run_cypher('MATCH (a:Article) RETURN count(a) as count')[0]['count']
about_count = run_cypher('MATCH ()-[r:ABOUT]->() RETURN count(r) as count')[0]['count']

# === TOPIC-TOPIC RELATIONSHIPS ===
influences = run_cypher('MATCH (:Topic)-[r:INFLUENCES]->(:Topic) RETURN count(r) as count')[0]['count']
correlates = run_cypher('MATCH (:Topic)-[r:CORRELATES_WITH]->(:Topic) RETURN count(r) as count')[0]['count']

# === ORPHAN DETECTION ===
orphan_articles = run_cypher('MATCH (a:Article) WHERE NOT (a)-[:ABOUT]->(:Topic) RETURN count(a) as count')[0]['count']
orphan_topics = run_cypher('MATCH (t:Topic) WHERE NOT (:Article)-[:ABOUT]->(t) RETURN count(t) as count')[0]['count']

# === TOPIC DISTRIBUTION ===
topic_distribution = run_cypher('''
    MATCH (a:Article)-[:ABOUT]->(t:Topic)
    WITH t.id as topic_id, t.name as topic_name, count(a) as article_count
    RETURN topic_id, topic_name, article_count
    ORDER BY article_count DESC
''')

# Get distribution stats
article_counts = [t['article_count'] for t in topic_distribution]
min_articles = min(article_counts) if article_counts else 0
max_articles = max(article_counts) if article_counts else 0
median_articles = sorted(article_counts)[len(article_counts)//2] if article_counts else 0

# Topics with < 10 articles (starving)
starving_topics = [t for t in topic_distribution if t['article_count'] < 10]

# Topics with > 500 articles (saturated)
saturated_topics = [t for t in topic_distribution if t['article_count'] > 500]

# === ANALYSIS FRESHNESS ===
stale_analysis = run_cypher('''
    MATCH (t:Topic)
    WHERE t.last_analyzed IS NOT NULL
    AND t.last_analyzed < datetime() - duration(\\\"P7D\\\")
    RETURN t.id as topic_id, t.name as topic_name, t.last_analyzed as last_analyzed
    ORDER BY t.last_analyzed ASC
    LIMIT 10
''')

never_analyzed = run_cypher('''
    MATCH (t:Topic)
    WHERE t.last_analyzed IS NULL
    RETURN t.id as topic_id, t.name as topic_name
    LIMIT 20
''')

# === RECENT ACTIVITY ===
articles_24h = run_cypher('''
    MATCH (a:Article)
    WHERE a.created_at > datetime() - duration(\\\"PT24H\\\")
    RETURN count(a) as count
''')[0]['count']

articles_7d = run_cypher('''
    MATCH (a:Article)
    WHERE a.created_at > datetime() - duration(\\\"P7D\\\")
    RETURN count(a) as count
''')[0]['count']

# === TOP 10 AND BOTTOM 10 TOPICS ===
top_10 = topic_distribution[:10]
bottom_10 = topic_distribution[-10:] if len(topic_distribution) > 10 else topic_distribution

print(json.dumps({
    'counts': {
        'topics': topic_count,
        'articles': article_count,
        'about_relationships': about_count,
        'influences_relationships': influences,
        'correlates_relationships': correlates,
        'total_topic_relationships': influences + correlates
    },
    'health': {
        'orphan_articles': orphan_articles,
        'orphan_topics': orphan_topics,
        'starving_topics_count': len(starving_topics),
        'saturated_topics_count': len(saturated_topics),
        'stale_analysis_count': len(stale_analysis),
        'never_analyzed_count': len(never_analyzed)
    },
    'distribution': {
        'min_articles_per_topic': min_articles,
        'max_articles_per_topic': max_articles,
        'median_articles_per_topic': median_articles,
        'avg_articles_per_topic': round(about_count / max(topic_count, 1), 1)
    },
    'activity': {
        'articles_last_24h': articles_24h,
        'articles_last_7d': articles_7d
    },
    'top_10_topics': top_10,
    'bottom_10_topics': bottom_10,
    'starving_topics': starving_topics[:10],
    'stale_analysis': stale_analysis,
    'never_analyzed': never_analyzed
}, default=str))
\""""
    result = run_command(cmd, timeout=60)

    if result["success"]:
        try:
            return json.loads(result["stdout"])
        except json.JSONDecodeError:
            return {"raw_output": result["stdout"], "success": True}
    return {"error": result["stderr"], "success": False}


# Pre-built analytical queries for graph_query endpoint
GRAPH_QUERIES = {
    "topic_distribution": """
        MATCH (a:Article)-[:ABOUT]->(t:Topic)
        WITH t.id as topic_id, t.name as topic_name, count(a) as article_count
        RETURN topic_id, topic_name, article_count
        ORDER BY article_count DESC
    """,
    "orphan_articles": """
        MATCH (a:Article)
        WHERE NOT (a)-[:ABOUT]->(:Topic)
        RETURN a.id as id, a.title as title, a.created_at as created_at
        ORDER BY a.created_at DESC
        LIMIT 50
    """,
    "topic_connections": """
        MATCH (t1:Topic)-[r:INFLUENCES|CORRELATES_WITH]->(t2:Topic)
        RETURN t1.id as from_topic, type(r) as relationship, t2.id as to_topic,
               t1.name as from_name, t2.name as to_name
        ORDER BY t1.name
    """,
    "analysis_freshness": """
        MATCH (t:Topic)
        OPTIONAL MATCH (a:Article)-[:ABOUT]->(t)
        WITH t, count(a) as article_count
        RETURN t.id as topic_id, t.name as topic_name,
               t.last_analyzed as last_analyzed,
               t.last_updated as last_updated,
               article_count
        ORDER BY t.last_analyzed ASC
    """,
    "high_importance_articles": """
        MATCH (a:Article)-[r:ABOUT]->(t:Topic)
        WHERE (COALESCE(r.importance_risk, 0) + COALESCE(r.importance_opportunity, 0) +
               COALESCE(r.importance_trend, 0) + COALESCE(r.importance_catalyst, 0)) >= 3
        RETURN a.id as id, a.title as title, t.id as topic_id, t.name as topic_name,
               r.importance_risk as risk, r.importance_opportunity as opportunity,
               r.importance_trend as trend, r.importance_catalyst as catalyst,
               r.motivation as motivation
        ORDER BY (COALESCE(r.importance_risk, 0) + COALESCE(r.importance_opportunity, 0) +
                  COALESCE(r.importance_trend, 0) + COALESCE(r.importance_catalyst, 0)) DESC
        LIMIT 50
    """,
    "articles_per_topic_stats": """
        MATCH (a:Article)-[:ABOUT]->(t:Topic)
        WITH t.id as topic_id, count(a) as cnt
        RETURN min(cnt) as min_articles, max(cnt) as max_articles,
               avg(cnt) as avg_articles, stdev(cnt) as stdev_articles,
               percentileCont(cnt, 0.5) as median_articles,
               percentileCont(cnt, 0.25) as p25_articles,
               percentileCont(cnt, 0.75) as p75_articles
    """,
    "recent_ingestion": """
        MATCH (a:Article)
        WHERE a.created_at > datetime() - duration('PT24H')
        OPTIONAL MATCH (a)-[:ABOUT]->(t:Topic)
        RETURN a.id as id, a.title as title, a.created_at as created_at,
               collect(t.id) as topics
        ORDER BY a.created_at DESC
        LIMIT 30
    """,
    "topic_overlap": """
        MATCH (a:Article)-[:ABOUT]->(t1:Topic)
        MATCH (a)-[:ABOUT]->(t2:Topic)
        WHERE t1.id < t2.id
        WITH t1, t2, count(a) as shared_articles
        WHERE shared_articles > 5
        RETURN t1.id as topic1, t1.name as name1,
               t2.id as topic2, t2.name as name2,
               shared_articles
        ORDER BY shared_articles DESC
        LIMIT 30
    """,
    "relationship_summary": """
        MATCH ()-[r]->()
        RETURN type(r) as relationship_type, count(r) as count
        ORDER BY count DESC
    """
}


@app.get("/mcp/tools/graph_query/{query_name}", dependencies=[Depends(verify_api_key)])
async def graph_query(query_name: str, limit: int = None):
    """
    Run pre-built analytical queries by name.

    Available queries:
    - topic_distribution: Articles per topic
    - orphan_articles: Articles with no topic links
    - topic_connections: INFLUENCES/CORRELATES relationships
    - analysis_freshness: When each topic was last analyzed
    - high_importance_articles: Tier 3+ articles
    - articles_per_topic_stats: Distribution statistics
    - recent_ingestion: Last 24h articles
    - topic_overlap: Topics sharing many articles
    - relationship_summary: Count of each relationship type
    """
    if query_name not in GRAPH_QUERIES:
        return {
            "error": f"Unknown query: {query_name}",
            "available_queries": list(GRAPH_QUERIES.keys())
        }

    query = GRAPH_QUERIES[query_name]

    # Apply limit if provided and query doesn't have one
    if limit and "LIMIT" not in query.upper():
        query = query.strip() + f" LIMIT {limit}"

    cmd = f'''docker exec -w /app/graph-functions apis python -c "
from src.graph.neo4j_client import run_cypher
import json

query = \\"""{query}\\"""
results = run_cypher(query)
print(json.dumps(results, default=str))
"'''
    result = run_command(cmd, timeout=60)

    if result["success"]:
        try:
            data = json.loads(result["stdout"])
            return {"query": query_name, "results": data, "count": len(data)}
        except json.JSONDecodeError:
            return {"raw_output": result["stdout"], "success": True}
    return {"error": result["stderr"], "success": False}


@app.get("/mcp/tools/graph_queries", dependencies=[Depends(verify_api_key)])
async def list_graph_queries():
    """List all available pre-built graph queries."""
    return {
        "available_queries": list(GRAPH_QUERIES.keys()),
        "usage": "GET /mcp/tools/graph_query/{query_name}?limit=N"
    }


# =============================================================================
# STRATEGY TOOLS - Read user strategies via internal API
# =============================================================================

@app.get("/mcp/tools/list_users", dependencies=[Depends(verify_api_key)])
async def list_users():
    """List all users in the system."""
    result = run_command("curl -s http://apis:8000/api/users", timeout=10)

    if result["success"]:
        try:
            return json.loads(result["stdout"])
        except json.JSONDecodeError:
            return {"raw_output": result["stdout"]}
    return {"error": result["stderr"], "success": False}


@app.post("/mcp/tools/user_strategies", dependencies=[Depends(verify_api_key)])
async def user_strategies(req: StrategyRequest):
    """Get strategies for a user, optionally a specific strategy."""
    if req.strategy_id:
        # Get specific strategy with full details
        url = f"http://apis:8000/api/users/{req.username}/strategies/{req.strategy_id}"
    else:
        # List all strategies for user
        url = f"http://apis:8000/api/users/{req.username}/strategies"

    result = run_command(f"curl -s '{url}'", timeout=10)

    if result["success"]:
        try:
            data = json.loads(result["stdout"])
            return {"username": req.username, "data": data}
        except json.JSONDecodeError:
            return {"raw_output": result["stdout"]}
    return {"error": result["stderr"], "success": False}


@app.post("/mcp/tools/strategy_analysis", dependencies=[Depends(verify_api_key)])
async def strategy_analysis(req: StrategyRequest):
    """Get the latest analysis for a strategy."""
    if not req.strategy_id:
        raise HTTPException(400, "strategy_id is required for analysis")

    url = f"http://apis:8000/api/users/{req.username}/strategies/{req.strategy_id}/analysis"
    result = run_command(f"curl -s '{url}'", timeout=10)

    if result["success"]:
        try:
            data = json.loads(result["stdout"])
            return {"username": req.username, "strategy_id": req.strategy_id, "analysis": data}
        except json.JSONDecodeError:
            return {"raw_output": result["stdout"]}
    return {"error": result["stderr"], "success": False}


@app.post("/mcp/tools/strategy_topics", dependencies=[Depends(verify_api_key)])
async def strategy_topics(req: StrategyRequest):
    """Get topics associated with a strategy."""
    if not req.strategy_id:
        raise HTTPException(400, "strategy_id is required")

    url = f"http://apis:8000/api/users/{req.username}/strategies/{req.strategy_id}/topics"
    result = run_command(f"curl -s '{url}'", timeout=10)

    if result["success"]:
        try:
            data = json.loads(result["stdout"])
            return {"username": req.username, "strategy_id": req.strategy_id, "topics": data}
        except json.JSONDecodeError:
            return {"raw_output": result["stdout"]}
    return {"error": result["stderr"], "success": False}


# =============================================================================
# ACTION TOOLS - Guarded write operations
# =============================================================================

@app.post("/mcp/tools/hide_article", dependencies=[Depends(verify_api_key)])
async def hide_article(req: HideArticleRequest):
    """Hide an article (soft delete). Requires reason for audit."""
    cmd = f'''docker exec -w /app/graph-functions apis python -c "
from src.graph.ops.article import set_article_hidden
from src.observability.stats_client import track
import json

try:
    set_article_hidden('{req.article_id}')
    track('article_hidden_via_mcp', '{req.article_id}: {req.reason}')
    print(json.dumps({{'success': True, 'article_id': '{req.article_id}', 'reason': '{req.reason}'}}))
except Exception as e:
    print(json.dumps({{'success': False, 'error': str(e)}}))
"'''
    result = run_command(cmd, timeout=30)

    if result["success"]:
        try:
            return json.loads(result["stdout"])
        except json.JSONDecodeError:
            return {"raw_output": result["stdout"]}
    return {"error": result["stderr"], "success": False}


@app.post("/mcp/tools/trigger_analysis", dependencies=[Depends(verify_api_key)])
async def trigger_topic_analysis(req: TriggerAnalysisRequest):
    """Trigger analysis refresh for a topic. Runs in background."""
    # First verify topic exists
    check_cmd = f'''docker exec -w /app/graph-functions apis python -c "
from src.graph.ops.topic import check_if_topic_exists
print('exists' if check_if_topic_exists('{req.topic_id}') else 'not_found')
"'''
    check = run_command(check_cmd, timeout=10)

    if "not_found" in check["stdout"]:
        raise HTTPException(404, f"Topic not found: {req.topic_id}")

    # Trigger analysis (this runs the analysis pipeline)
    # Note: This is a simplified trigger - in production you might queue this
    cmd = f'''docker exec -d -w /app/graph-functions apis python -c "
from src.analysis.policies.reanalysis import trigger_reanalysis
from src.observability.stats_client import track

track('analysis_triggered_via_mcp', '{req.topic_id}')
trigger_reanalysis('{req.topic_id}', force={req.force})
"'''
    result = run_command(cmd, timeout=10)

    return {
        "topic_id": req.topic_id,
        "triggered": True,
        "force": req.force,
        "note": "Analysis running in background. Check logs for progress."
    }


# =============================================================================
# GOD-TIER TOOLS - Strategy Detail Endpoints
# =============================================================================

@app.get("/mcp/tools/strategy_detail", dependencies=[Depends(verify_api_key)])
async def strategy_detail(username: str, strategy_id: str):
    """Get FULL strategy details including thesis, position, target, is_default, timestamps."""
    # Read raw file from saga-be users directory
    file_path = f"/opt/saga-graph/saga-be/users/{username}/strategy_{strategy_id}.json"

    try:
        result = run_command(f"cat '{file_path}'", timeout=10)
        if result["success"] and result["stdout"].strip():
            data = json.loads(result["stdout"])
            return {
                "strategy_id": strategy_id,
                "username": username,
                "strategy": data,
                "file_path": file_path
            }
        else:
            return {"error": f"Strategy file not found: {file_path}", "success": False}
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON in strategy file: {e}", "raw": result["stdout"][:500]}


@app.get("/mcp/tools/list_strategy_files", dependencies=[Depends(verify_api_key)])
async def list_strategy_files(username: str):
    """List all strategy JSON files for a user with metadata."""
    user_dir = f"/opt/saga-graph/saga-be/users/{username}"

    # List all strategy files
    result = run_command(f"ls -la {user_dir}/strategy_*.json 2>/dev/null", timeout=10)

    if not result["success"] or not result["stdout"].strip():
        return {"username": username, "strategies": [], "count": 0, "note": "No strategy files found"}

    # Parse each strategy file to get metadata
    strategies = []
    for line in result["stdout"].strip().split("\n"):
        if "strategy_" in line:
            parts = line.split()
            filename = parts[-1] if parts else None
            if filename:
                # Read the file to get metadata
                cat_result = run_command(f"cat '{filename}'", timeout=5)
                if cat_result["success"]:
                    try:
                        data = json.loads(cat_result["stdout"])
                        strategies.append({
                            "filename": os.path.basename(filename),
                            "strategy_id": data.get("id"),
                            "asset": data.get("asset", {}).get("primary"),
                            "is_default": data.get("is_default", False),
                            "created_at": data.get("created_at"),
                            "updated_at": data.get("updated_at"),
                            "thesis_preview": (data.get("user_input", {}).get("strategy_text", "")[:100] + "...")
                        })
                    except json.JSONDecodeError:
                        strategies.append({"filename": os.path.basename(filename), "error": "Invalid JSON"})

    return {
        "username": username,
        "strategies": strategies,
        "count": len(strategies)
    }


@app.get("/mcp/tools/raw_strategy_file", dependencies=[Depends(verify_api_key)])
async def raw_strategy_file(username: str, strategy_id: str):
    """Read raw strategy JSON file - exactly what's on disk."""
    file_path = f"/opt/saga-graph/saga-be/users/{username}/strategy_{strategy_id}.json"

    result = run_command(f"cat '{file_path}'", timeout=10)

    if result["success"] and result["stdout"].strip():
        try:
            data = json.loads(result["stdout"])
            return {
                "username": username,
                "strategy_id": strategy_id,
                "file_path": file_path,
                "raw_content": data
            }
        except json.JSONDecodeError:
            return {"error": "Invalid JSON", "raw_content": result["stdout"][:2000]}
    return {"error": f"File not found: {file_path}", "success": False}


@app.get("/mcp/tools/strategy_conversations", dependencies=[Depends(verify_api_key)])
async def strategy_conversations(username: str, strategy_id: str, limit: int = 10):
    """Get conversation history for a strategy."""
    conv_dir = f"/opt/saga-graph/saga-be/users/{username}/conversations"

    # List conversation files for this strategy
    result = run_command(f"ls -t {conv_dir}/*{strategy_id}*.json 2>/dev/null | head -n {limit}", timeout=10)

    if not result["success"] or not result["stdout"].strip():
        # Try listing all conversations and filtering
        result = run_command(f"ls -t {conv_dir}/*.json 2>/dev/null | head -n 50", timeout=10)

    conversations = []
    for filepath in result["stdout"].strip().split("\n"):
        if filepath:
            cat_result = run_command(f"cat '{filepath}'", timeout=5)
            if cat_result["success"]:
                try:
                    data = json.loads(cat_result["stdout"])
                    # Check if this conversation is for the target strategy
                    if strategy_id in filepath or data.get("strategy_id") == strategy_id:
                        conversations.append({
                            "filename": os.path.basename(filepath),
                            "created_at": data.get("created_at"),
                            "message_count": len(data.get("messages", [])),
                            "messages": data.get("messages", [])[-5:]  # Last 5 messages as preview
                        })
                except json.JSONDecodeError:
                    pass

    return {
        "username": username,
        "strategy_id": strategy_id,
        "conversations": conversations[:limit],
        "count": len(conversations)
    }


# =============================================================================
# GOD-TIER TOOLS - Topic Analysis Endpoints
# =============================================================================

@app.get("/mcp/tools/topic_analysis_full", dependencies=[Depends(verify_api_key)])
async def topic_analysis_full(topic_id: str):
    """Get ALL 4 analysis timeframes for a topic."""
    cmd = f"""docker exec -w /app/graph-functions apis python -c '
import json
from src.graph.neo4j_client import run_cypher
q = "MATCH (t:Topic {{id: \\"{topic_id}\\"}}) RETURN t.id as id, t.name as name, t.type as type, t.category as category, t.fundamental_analysis as fundamental, t.medium_analysis as medium, t.current_analysis as current, t.drivers as drivers, t.last_analyzed as last_analyzed, t.last_updated as last_updated"
results = run_cypher(q)
if results:
    print(json.dumps(results[0], default=str))
else:
    print(json.dumps({{"error": "Topic not found"}}))
'"""
    result = run_command(cmd, timeout=30)

    if result["success"]:
        try:
            data = json.loads(result["stdout"])
            return {
                "topic_id": topic_id,
                "analysis": {
                    "fundamental": data.get("fundamental"),
                    "medium": data.get("medium"),
                    "current": data.get("current"),
                    "drivers": data.get("drivers")
                },
                "metadata": {
                    "name": data.get("name"),
                    "type": data.get("type"),
                    "category": data.get("category"),
                    "last_analyzed": data.get("last_analyzed"),
                    "last_updated": data.get("last_updated")
                }
            }
        except json.JSONDecodeError:
            return {"raw_output": result["stdout"], "success": True}
    return {"error": result["stderr"], "success": False}


@app.get("/mcp/tools/topic_relationships", dependencies=[Depends(verify_api_key)])
async def topic_relationships(topic_id: str):
    """Get all relationships for a topic with strength and mechanisms."""
    cmd = f"""docker exec -w /app/graph-functions apis python -c '
import json
from src.graph.neo4j_client import run_cypher
outgoing = run_cypher("MATCH (t:Topic {{id: \\"{topic_id}\\"}})-[r]->(t2:Topic) RETURN type(r) as rel_type, t2.id as target_id, t2.name as target_name, r.strength as strength, r.mechanism as mechanism")
incoming = run_cypher("MATCH (t2:Topic)-[r]->(t:Topic {{id: \\"{topic_id}\\"}}) RETURN type(r) as rel_type, t2.id as source_id, t2.name as source_name, r.strength as strength, r.mechanism as mechanism")
print(json.dumps({{"outgoing": outgoing, "incoming": incoming}}, default=str))
'"""
    result = run_command(cmd, timeout=30)

    if result["success"]:
        try:
            data = json.loads(result["stdout"])
            # Organize by relationship type
            influences_out = [r for r in data.get("outgoing", []) if r.get("rel_type") == "INFLUENCES"]
            influences_in = [r for r in data.get("incoming", []) if r.get("rel_type") == "INFLUENCES"]
            correlates = [r for r in data.get("outgoing", []) + data.get("incoming", []) if r.get("rel_type") == "CORRELATES_WITH"]
            hedges = [r for r in data.get("outgoing", []) + data.get("incoming", []) if r.get("rel_type") == "HEDGES"]
            peers = [r for r in data.get("outgoing", []) + data.get("incoming", []) if r.get("rel_type") == "PEERS"]

            return {
                "topic_id": topic_id,
                "relationships": {
                    "influences": influences_out,
                    "influenced_by": influences_in,
                    "correlates_with": correlates,
                    "hedges": hedges,
                    "peers": peers
                },
                "counts": {
                    "total_outgoing": len(data.get("outgoing", [])),
                    "total_incoming": len(data.get("incoming", []))
                }
            }
        except json.JSONDecodeError:
            return {"raw_output": result["stdout"], "success": True}
    return {"error": result["stderr"], "success": False}


@app.get("/mcp/tools/topic_influence_map", dependencies=[Depends(verify_api_key)])
async def topic_influence_map(topic_id: str, depth: int = 2):
    """Get full influence graph for a topic - N hops deep."""
    cmd = f"""docker exec -w /app/graph-functions apis python -c '
import json
from src.graph.neo4j_client import run_cypher
outward = run_cypher("MATCH path = (start:Topic {{id: \\"{topic_id}\\"}})-[:INFLUENCES*1..{depth}]->(end:Topic) WITH nodes(path) as topics, relationships(path) as rels UNWIND range(0, size(rels)-1) as idx RETURN topics[idx].id as from_id, topics[idx].name as from_name, topics[idx+1].id as to_id, topics[idx+1].name as to_name, rels[idx].strength as strength, rels[idx].mechanism as mechanism, idx + 1 as hop")
inward = run_cypher("MATCH path = (start:Topic)-[:INFLUENCES*1..{depth}]->(end:Topic {{id: \\"{topic_id}\\"}}) WITH nodes(path) as topics, relationships(path) as rels UNWIND range(0, size(rels)-1) as idx RETURN topics[idx].id as from_id, topics[idx].name as from_name, topics[idx+1].id as to_id, topics[idx+1].name as to_name, rels[idx].strength as strength, rels[idx].mechanism as mechanism, idx + 1 as hop")
print(json.dumps({{"influences_outward": outward, "influenced_by": inward}}, default=str))
'"""
    result = run_command(cmd, timeout=60)

    if result["success"]:
        try:
            data = json.loads(result["stdout"])
            return {
                "topic_id": topic_id,
                "depth": depth,
                "influence_map": data,
                "summary": {
                    "outward_connections": len(data.get("influences_outward", [])),
                    "inward_connections": len(data.get("influenced_by", []))
                }
            }
        except json.JSONDecodeError:
            return {"raw_output": result["stdout"], "success": True}
    return {"error": result["stderr"], "success": False}


@app.get("/mcp/tools/topic_coverage_gaps", dependencies=[Depends(verify_api_key)])
async def topic_coverage_gaps(stale_days: int = 7):
    """Find topics with stale/missing analysis."""
    cmd = f"""docker exec -w /app/graph-functions apis python -c '
import json
from src.graph.neo4j_client import run_cypher
never_analyzed = run_cypher("MATCH (t:Topic) WHERE t.fundamental_analysis IS NULL AND t.current_analysis IS NULL OPTIONAL MATCH (a:Article)-[:ABOUT]->(t) RETURN t.id as topic_id, t.name as topic_name, count(a) as article_count ORDER BY article_count DESC")
stale = run_cypher("MATCH (t:Topic) WHERE t.last_analyzed IS NOT NULL AND t.last_analyzed < datetime() - duration(\\"P{stale_days}D\\") OPTIONAL MATCH (a:Article)-[:ABOUT]->(t) WITH t, count(a) as article_count RETURN t.id as topic_id, t.name as topic_name, t.last_analyzed as last_analyzed, article_count ORDER BY t.last_analyzed ASC")
starving = run_cypher("MATCH (t:Topic) OPTIONAL MATCH (a:Article)-[:ABOUT]->(t) WITH t, count(a) as article_count WHERE article_count < 5 RETURN t.id as topic_id, t.name as topic_name, article_count ORDER BY article_count ASC")
print(json.dumps({{"never_analyzed": never_analyzed, "stale_analysis": stale, "starving_topics": starving, "summary": {{"never_analyzed_count": len(never_analyzed), "stale_count": len(stale), "starving_count": len(starving)}}}}, default=str))
'"""
    result = run_command(cmd, timeout=60)

    if result["success"]:
        try:
            return json.loads(result["stdout"])
        except json.JSONDecodeError:
            return {"raw_output": result["stdout"], "success": True}
    return {"error": result["stderr"], "success": False}


# =============================================================================
# GOD-TIER TOOLS - Pipeline & Agent Endpoints
# =============================================================================

@app.get("/mcp/tools/topic_mapping_result", dependencies=[Depends(verify_api_key)])
async def topic_mapping_result(username: str, strategy_id: str):
    """See how a strategy was mapped to topics."""
    # Get strategy topics from API
    url = f"http://apis:8000/api/users/{username}/strategies/{strategy_id}/topics"
    result = run_command(f"curl -s '{url}'", timeout=10)

    if result["success"]:
        try:
            topics_data = json.loads(result["stdout"])

            # Also get the strategy to show the thesis
            strategy_url = f"http://apis:8000/api/users/{username}/strategies/{strategy_id}"
            strategy_result = run_command(f"curl -s '{strategy_url}'", timeout=10)
            strategy_data = {}
            if strategy_result["success"]:
                try:
                    strategy_data = json.loads(strategy_result["stdout"])
                except:
                    pass

            return {
                "strategy_id": strategy_id,
                "username": username,
                "thesis_preview": strategy_data.get("user_input", {}).get("strategy_text", "")[:200] + "...",
                "topic_mapping": topics_data,
                "topic_count": len(topics_data) if isinstance(topics_data, list) else 0
            }
        except json.JSONDecodeError:
            return {"raw_output": result["stdout"]}
    return {"error": result["stderr"], "success": False}


@app.get("/mcp/tools/exploration_paths", dependencies=[Depends(verify_api_key)])
async def exploration_paths(username: str, strategy_id: str):
    """Get chain reactions discovered by Exploration Agent for a strategy."""
    # Get strategy analysis which contains exploration results
    url = f"http://apis:8000/api/users/{username}/strategies/{strategy_id}/analysis"
    result = run_command(f"curl -s '{url}'", timeout=10)

    if result["success"]:
        try:
            data = json.loads(result["stdout"])
            # Extract chain reactions from analysis if present
            chain_reactions = data.get("chain_reactions", [])
            exploration = data.get("exploration", {})

            return {
                "strategy_id": strategy_id,
                "username": username,
                "chain_reactions": chain_reactions,
                "exploration_output": exploration,
                "note": "Chain reactions are multi-hop influence paths discovered by the Exploration Agent"
            }
        except json.JSONDecodeError:
            return {"raw_output": result["stdout"]}
    return {"error": result["stderr"], "success": False}


@app.get("/mcp/tools/agent_outputs", dependencies=[Depends(verify_api_key)])
async def agent_outputs(username: str, strategy_id: str, agent: str = None):
    """Get raw outputs from specific agents for a strategy."""
    url = f"http://apis:8000/api/users/{username}/strategies/{strategy_id}/analysis"
    result = run_command(f"curl -s '{url}'", timeout=10)

    if result["success"]:
        try:
            data = json.loads(result["stdout"])

            # Extract agent-specific outputs
            outputs = {}
            if not agent or agent == "risk_assessor":
                outputs["risk_assessor"] = data.get("risks", data.get("risk_assessment", {}))
            if not agent or agent == "opportunity_finder":
                outputs["opportunity_finder"] = data.get("opportunities", data.get("opportunity_assessment", {}))
            if not agent or agent == "exploration":
                outputs["exploration"] = data.get("exploration", data.get("chain_reactions", {}))
            if not agent or agent == "strategy_writer":
                outputs["strategy_writer"] = data.get("summary", data.get("strategy_summary", {}))
            if not agent or agent == "topic_mapper":
                outputs["topic_mapper"] = data.get("topics", data.get("topic_mapping", {}))

            return {
                "strategy_id": strategy_id,
                "username": username,
                "agent_filter": agent,
                "outputs": outputs,
                "generated_at": data.get("generated_at", data.get("updated_at"))
            }
        except json.JSONDecodeError:
            return {"raw_output": result["stdout"]}
    return {"error": result["stderr"], "success": False}


# =============================================================================
# GOD-TIER TOOLS - Worker & Pipeline Monitoring
# =============================================================================

@app.get("/mcp/tools/worker_status", dependencies=[Depends(verify_api_key)])
async def worker_status():
    """Status of all workers with last run times."""
    workers = {}

    # Check each worker service
    for service in ["worker-main", "worker-sources"]:
        # Get container status
        status_result = run_command(
            f"docker inspect {service} --format '{{{{.State.Status}}}} {{{{.State.StartedAt}}}}'",
            timeout=5
        )

        # Get recent logs for last activity
        logs_result = run_command(
            f"docker logs --tail 50 {service} 2>&1 | grep -E '(SUCCESS|ERROR|Started|Completed|Processing)' | tail -5",
            timeout=10
        )

        workers[service] = {
            "status": status_result["stdout"].split()[0] if status_result["success"] else "unknown",
            "started_at": status_result["stdout"].split()[1] if status_result["success"] and len(status_result["stdout"].split()) > 1 else "unknown",
            "recent_activity": logs_result["stdout"].strip().split("\n") if logs_result["success"] else []
        }

    # Get WORKER_MODE from environment
    mode_result = run_command("docker exec worker-main printenv WORKER_MODE 2>/dev/null", timeout=5)

    return {
        "workers": workers,
        "worker_mode": mode_result["stdout"].strip() if mode_result["success"] else "unknown",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/mcp/tools/failed_jobs", dependencies=[Depends(verify_api_key)])
async def failed_jobs(hours: int = 24):
    """Recent failures in any pipeline."""
    failures = []

    # Search for errors in each service
    for service in ["worker-main", "worker-sources", "apis"]:
        result = run_command(
            f"docker logs --since {hours}h {service} 2>&1 | grep -iE '(ERROR|Exception|FAILED|Traceback)' | tail -20",
            timeout=30
        )

        if result["success"] and result["stdout"].strip():
            for line in result["stdout"].strip().split("\n"):
                if line:
                    failures.append({
                        "service": service,
                        "message": line[:500],
                        "type": "error"
                    })

    return {
        "hours_searched": hours,
        "failures": failures,
        "total_count": len(failures),
        "summary": {
            "by_service": {s: len([f for f in failures if f["service"] == s]) for s in ["worker-main", "worker-sources", "apis"]}
        }
    }


@app.get("/mcp/tools/processing_backlog", dependencies=[Depends(verify_api_key)])
async def processing_backlog():
    """What's waiting to be processed."""
    cmd = """docker exec -w /app/graph-functions apis python -c '
import json
from src.graph.neo4j_client import run_cypher
pending_topics = run_cypher("MATCH (a:Article) WHERE NOT (a)-[:ABOUT]->(:Topic) AND a.created_at > datetime() - duration(\\"P7D\\") RETURN count(a) as count")[0]["count"]
pending_analysis = run_cypher("MATCH (t:Topic) WHERE t.last_analyzed IS NULL OR t.last_analyzed < datetime() - duration(\\"P7D\\") RETURN count(t) as count")[0]["count"]
recent_unprocessed = run_cypher("MATCH (a:Article) WHERE a.created_at > datetime() - duration(\\"PT6H\\") AND (a.processed IS NULL OR a.processed = false) RETURN count(a) as count")[0]["count"]
print(json.dumps({"pending_topic_assignment": pending_topics, "pending_analysis_refresh": pending_analysis, "recent_unprocessed": recent_unprocessed, "health": "nominal" if (pending_topics < 100 and pending_analysis < 20) else "backlogged"}, default=str))
'"""
    result = run_command(cmd, timeout=30)

    if result["success"]:
        try:
            return json.loads(result["stdout"])
        except json.JSONDecodeError:
            return {"raw_output": result["stdout"], "success": True}
    return {"error": result["stderr"], "success": False}


@app.get("/mcp/tools/ingestion_stats", dependencies=[Depends(verify_api_key)])
async def ingestion_stats(days: int = 7):
    """Article ingestion stats by source and day."""
    cmd = f"""docker exec -w /app/graph-functions apis python -c '
import json
from src.graph.neo4j_client import run_cypher
by_source = run_cypher("MATCH (a:Article) WHERE a.created_at > datetime() - duration(\\"P{days}D\\") RETURN a.source as source, count(a) as count ORDER BY count DESC")
by_day = run_cypher("MATCH (a:Article) WHERE a.created_at > datetime() - duration(\\"P{days}D\\") RETURN date(a.created_at) as day, count(a) as count ORDER BY day DESC")
total = run_cypher("MATCH (a:Article) WHERE a.created_at > datetime() - duration(\\"P{days}D\\") RETURN count(a) as total")[0]["total"]
print(json.dumps({{"by_source": by_source, "by_day": by_day, "total_articles": total, "days": {days}, "avg_per_day": round(total / {days}, 1)}}, default=str))
'"""
    result = run_command(cmd, timeout=30)

    if result["success"]:
        try:
            return json.loads(result["stdout"])
        except json.JSONDecodeError:
            return {"raw_output": result["stdout"], "success": True}
    return {"error": result["stderr"], "success": False}


# =============================================================================
# GOD-TIER TOOLS - Article Endpoints
# =============================================================================

@app.get("/mcp/tools/article_detail", dependencies=[Depends(verify_api_key)])
async def article_detail(article_id: str):
    """Get full article content + classification + topic assignments."""
    cmd = f"""docker exec -w /app/graph-functions apis python -c '
import json
from src.graph.neo4j_client import run_cypher
results = run_cypher("MATCH (a:Article {{id: \\"{article_id}\\"}}) OPTIONAL MATCH (a)-[r:ABOUT]->(t:Topic) RETURN a.id as id, a.title as title, a.source as source, a.url as url, a.content as content, a.summary as summary, a.published_at as published_at, a.created_at as created_at, a.classification as classification, a.category as category, collect({{topic_id: t.id, topic_name: t.name, importance_risk: r.importance_risk, importance_opportunity: r.importance_opportunity}}) as topics")
if results:
    print(json.dumps(results[0], default=str))
else:
    print(json.dumps({{"error": "Article not found"}}))
'"""
    result = run_command(cmd, timeout=30)

    if result["success"]:
        try:
            return json.loads(result["stdout"])
        except json.JSONDecodeError:
            return {"raw_output": result["stdout"], "success": True}
    return {"error": result["stderr"], "success": False}


@app.get("/mcp/tools/search_articles", dependencies=[Depends(verify_api_key)])
async def search_articles_tool(query: str, topic_id: str = None, since: str = None, limit: int = 20):
    """Search articles by keyword, date range, topic."""
    import base64
    # Build cypher query
    where_clauses = [f"a.title =~ '(?i).*{query}.*' OR a.content =~ '(?i).*{query}.*'"]

    if topic_id:
        topic_match = f"MATCH (a)-[:ABOUT]->(t:Topic {{id: '{topic_id}'}})"
    else:
        topic_match = "OPTIONAL MATCH (a)-[:ABOUT]->(t:Topic)"

    if since:
        where_clauses.append(f"a.published_at >= '{since}'")

    where_clause = " AND ".join(where_clauses)
    search_q = f"MATCH (a:Article) {topic_match} WHERE {where_clause} RETURN DISTINCT a.id as id, a.title as title, a.source as source, a.published_at as published_at, a.summary as summary ORDER BY a.published_at DESC LIMIT {limit}"

    # Encode query to avoid shell escaping issues
    encoded_q = base64.b64encode(search_q.encode()).decode()

    cmd = f"""docker exec -w /app/graph-functions apis python -c '
import json, base64
from src.graph.neo4j_client import run_cypher
q = base64.b64decode("{encoded_q}").decode()
results = run_cypher(q)
print(json.dumps(results, default=str))
'"""
    result = run_command(cmd, timeout=30)

    if result["success"]:
        try:
            articles = json.loads(result["stdout"])
            return {
                "query": query,
                "topic_filter": topic_id,
                "since": since,
                "articles": articles,
                "count": len(articles)
            }
        except json.JSONDecodeError:
            return {"raw_output": result["stdout"], "success": True}
    return {"error": result["stderr"], "success": False}


@app.get("/mcp/tools/source_stats", dependencies=[Depends(verify_api_key)])
async def source_stats(days: int = 7):
    """Article counts by source with quality indicators."""
    cmd = f"""docker exec -w /app/graph-functions apis python -c '
import json
from src.graph.neo4j_client import run_cypher
stats = run_cypher("MATCH (a:Article) WHERE a.created_at > datetime() - duration(\\"P{days}D\\") RETURN a.source as source, count(a) as article_count ORDER BY article_count DESC")
print(json.dumps({{"sources": stats, "days": {days}}}, default=str))
'"""
    result = run_command(cmd, timeout=30)

    if result["success"]:
        try:
            return json.loads(result["stdout"])
        except json.JSONDecodeError:
            return {"raw_output": result["stdout"], "success": True}
    return {"error": result["stderr"], "success": False}


# =============================================================================
# GOD-TIER TOOLS - Cross-Cutting Analysis
# =============================================================================

@app.get("/mcp/tools/strategy_health_check", dependencies=[Depends(verify_api_key)])
async def strategy_health_check(username: str, strategy_id: str):
    """Diagnose why a strategy might be getting poor analysis."""
    issues = []
    strengths = []

    # 1. Get strategy details
    strategy_url = f"http://apis:8000/api/users/{username}/strategies/{strategy_id}"
    strategy_result = run_command(f"curl -s '{strategy_url}'", timeout=10)
    strategy_data = {}
    if strategy_result["success"]:
        try:
            strategy_data = json.loads(strategy_result["stdout"])
        except:
            issues.append({"severity": "high", "category": "data", "issue": "Cannot read strategy data"})

    # 2. Get topic mapping
    topics_url = f"http://apis:8000/api/users/{username}/strategies/{strategy_id}/topics"
    topics_result = run_command(f"curl -s '{topics_url}'", timeout=10)
    topics = []
    if topics_result["success"]:
        try:
            topics = json.loads(topics_result["stdout"])
            if isinstance(topics, list):
                if len(topics) < 5:
                    issues.append({
                        "severity": "high",
                        "category": "topic_mapping",
                        "issue": f"Only {len(topics)} topics mapped (optimal: 10-15)",
                        "suggestion": "Strategy thesis may lack explicit driver mechanisms"
                    })
                elif len(topics) >= 10:
                    strengths.append("Good topic coverage (10+ topics mapped)")
        except:
            pass

    # 3. Check thesis quality
    thesis = strategy_data.get("user_input", {}).get("strategy_text", "")
    if thesis:
        # Check for causal mechanisms
        causal_indicators = ["→", "because", "leads to", "causes", "drives", "if", "then", "when"]
        has_causality = any(ind in thesis.lower() for ind in causal_indicators)
        if not has_causality:
            issues.append({
                "severity": "medium",
                "category": "thesis_quality",
                "issue": "Thesis lacks explicit causal mechanisms",
                "suggestion": "Add transmission paths like 'A → B via X'"
            })
        else:
            strengths.append("Thesis contains causal mechanisms")

        # Check for invalidation signals
        invalidation_indicators = ["dies if", "wrong if", "risk:", "breaks if", "invalid"]
        has_invalidation = any(ind in thesis.lower() for ind in invalidation_indicators)
        if not has_invalidation:
            issues.append({
                "severity": "low",
                "category": "thesis_quality",
                "issue": "No thesis invalidation signals detected",
                "suggestion": "Add 'thesis dies if...' to help Risk Assessor"
            })
        else:
            strengths.append("Thesis includes invalidation signals")

    # 4. Calculate health score
    high_issues = len([i for i in issues if i["severity"] == "high"])
    medium_issues = len([i for i in issues if i["severity"] == "medium"])
    low_issues = len([i for i in issues if i["severity"] == "low"])
    health_score = max(0, 1.0 - (high_issues * 0.3) - (medium_issues * 0.15) - (low_issues * 0.05))

    return {
        "strategy_id": strategy_id,
        "username": username,
        "health_score": round(health_score, 2),
        "issues": issues,
        "strengths": strengths,
        "topic_count": len(topics) if isinstance(topics, list) else 0,
        "thesis_length": len(thesis)
    }


@app.get("/mcp/tools/cross_strategy_insights", dependencies=[Depends(verify_api_key)])
async def cross_strategy_insights():
    """Find overlapping topics/risks across ALL strategies."""
    # Get all users and their strategies
    users_result = run_command("curl -s http://apis:8000/api/users", timeout=10)

    all_topics = {}
    all_strategies = []

    if users_result["success"]:
        try:
            users = json.loads(users_result["stdout"])
            for user in users if isinstance(users, list) else []:
                username = user.get("username")
                if not username:
                    continue

                # Get strategies for this user
                strat_result = run_command(f"curl -s 'http://apis:8000/api/users/{username}/strategies'", timeout=10)
                if strat_result["success"]:
                    try:
                        strategies = json.loads(strat_result["stdout"])
                        for strat in strategies if isinstance(strategies, list) else []:
                            strat_id = strat.get("id")
                            strat_name = strat.get("asset", {}).get("primary", strat_id)
                            all_strategies.append({"username": username, "id": strat_id, "name": strat_name})

                            # Get topics for this strategy
                            topics_result = run_command(f"curl -s 'http://apis:8000/api/users/{username}/strategies/{strat_id}/topics'", timeout=10)
                            if topics_result["success"]:
                                try:
                                    topics = json.loads(topics_result["stdout"])
                                    for topic in topics if isinstance(topics, list) else []:
                                        topic_id = topic.get("id", topic) if isinstance(topic, dict) else topic
                                        if topic_id not in all_topics:
                                            all_topics[topic_id] = []
                                        all_topics[topic_id].append(strat_name)
                                except:
                                    pass
                    except:
                        pass
        except:
            pass

    # Find overlapping topics
    overlapping = [
        {"topic": tid, "strategies": strats, "count": len(strats)}
        for tid, strats in all_topics.items()
        if len(strats) > 1
    ]
    overlapping.sort(key=lambda x: x["count"], reverse=True)

    return {
        "total_strategies": len(all_strategies),
        "total_unique_topics": len(all_topics),
        "overlapping_topics": overlapping[:20],
        "highest_concentration": overlapping[0] if overlapping else None,
        "strategies": all_strategies
    }


@app.get("/mcp/tools/system_activity_log", dependencies=[Depends(verify_api_key)])
async def system_activity_log(hours: int = 24):
    """Recent system activity - analyses run, strategies updated, articles ingested."""
    activity = []

    # Get recent logs from workers
    for service in ["worker-main", "worker-sources", "apis"]:
        result = run_command(
            f"docker logs --since {hours}h {service} 2>&1 | grep -iE '(SUCCESS|COMPLETED|INGESTED|ANALYZED|UPDATED|CREATED)' | tail -30",
            timeout=30
        )

        if result["success"] and result["stdout"].strip():
            for line in result["stdout"].strip().split("\n"):
                if line:
                    activity.append({
                        "service": service,
                        "message": line[:300],
                        "type": "activity"
                    })

    # Sort by recency (assuming timestamps in log lines)
    activity = activity[-50:]  # Limit to 50 most recent

    return {
        "hours_searched": hours,
        "activity": activity,
        "count": len(activity),
        "timestamp": datetime.utcnow().isoformat()
    }


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
