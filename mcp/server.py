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
# Auth
# =============================================================================

async def verify_api_key(api_key: str = Depends(api_key_header)):
    """Verify API key matches one of the valid keys."""
    if not api_key or api_key not in VALID_API_KEYS:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key"
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
        "version": "1.0.0",
        "tools": [
            "read_log", "search_logs", "tail_logs",
            "read_file", "search_files", "grep", "list_directory",
            "deploy_service", "restart_service", "docker_status",
            "git_status", "git_log", "git_diff", "git_pull",
            "query_neo4j", "system_health", "daily_stats",
            "run_command"
        ],
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
# Main
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
