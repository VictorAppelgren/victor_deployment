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
    }
]


class MCPRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[int] = None
    method: str
    params: Optional[dict] = None


@app.post("/mcp")
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
# Main
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
