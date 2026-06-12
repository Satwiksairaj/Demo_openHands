"""
MCP Server - Exposes Jira and GitHub tools via Model Context Protocol.
Enables LangChain agents to interact with external services as tools.
"""

import asyncio
import json
import logging
import os

import httpx
from mcp.server import Server  # type: ignore[attr-defined]
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolResult,
    ListToolsResult,
    TextContent,
    Tool,
)

logger = logging.getLogger(__name__)

# Initialize MCP server
server = Server("ai-dev-agent")


# ─── Tool Definitions ─────────────────────────────────────────────────────────

TOOLS = [
    Tool(
        name="jira_get_story",
        description="Fetch a Jira story/issue by its ID. Returns title, description, "
        "acceptance criteria, comments, and linked issues.",
        inputSchema={
            "type": "object",
            "properties": {
                "story_id": {
                    "type": "string",
                    "description": "Jira issue ID (e.g., IGN-245)",
                }
            },
            "required": ["story_id"],
        },
    ),
    Tool(
        name="jira_add_comment",
        description="Add a comment to a Jira issue.",
        inputSchema={
            "type": "object",
            "properties": {
                "story_id": {"type": "string", "description": "Jira issue ID"},
                "comment": {"type": "string", "description": "Comment text to add"},
            },
            "required": ["story_id", "comment"],
        },
    ),
    Tool(
        name="jira_update_status",
        description="Update the status of a Jira issue (e.g., move to 'In Progress' or 'Done').",
        inputSchema={
            "type": "object",
            "properties": {
                "story_id": {"type": "string", "description": "Jira issue ID"},
                "status": {"type": "string", "description": "New status name"},
            },
            "required": ["story_id", "status"],
        },
    ),
    Tool(
        name="github_create_pr",
        description="Create a Pull Request on GitHub.",
        inputSchema={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "PR title"},
                "body": {"type": "string", "description": "PR description (markdown)"},
                "head": {"type": "string", "description": "Source branch name"},
                "base": {
                    "type": "string",
                    "description": "Target branch (default: main)",
                },
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
            },
            "required": ["title", "body", "head", "owner", "repo"],
        },
    ),
    Tool(
        name="github_get_repo_info",
        description="Get repository information including default branch, language, and description.",
        inputSchema={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
            },
            "required": ["owner", "repo"],
        },
    ),
    Tool(
        name="github_list_files",
        description="List files and directories in a GitHub repository path.",
        inputSchema={
            "type": "object",
            "properties": {
                "owner": {"type": "string"},
                "repo": {"type": "string"},
                "path": {
                    "type": "string",
                    "description": "Path in repo (default: root)",
                },
                "branch": {
                    "type": "string",
                    "description": "Branch name (default: main)",
                },
            },
            "required": ["owner", "repo"],
        },
    ),
    Tool(
        name="github_get_file",
        description="Get the content of a specific file from a GitHub repository.",
        inputSchema={
            "type": "object",
            "properties": {
                "owner": {"type": "string"},
                "repo": {"type": "string"},
                "path": {
                    "type": "string",
                    "description": "File path in the repository",
                },
                "branch": {
                    "type": "string",
                    "description": "Branch name (default: main)",
                },
            },
            "required": ["owner", "repo", "path"],
        },
    ),
]


# ─── Tool Handlers ────────────────────────────────────────────────────────────


JIRA_BASE_URL = os.getenv("JIRA_BASE_URL", "")
JIRA_EMAIL = os.getenv("JIRA_EMAIL", "")
JIRA_TOKEN = os.getenv("JIRA_API_TOKEN", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")


async def handle_jira_get_story(args: dict) -> str:
    story_id = args["story_id"]
    url = f"{JIRA_BASE_URL}/rest/api/3/issue/{story_id}"
    auth = (JIRA_EMAIL, JIRA_TOKEN)

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, auth=auth)
        resp.raise_for_status()
        data = resp.json()

    fields = data.get("fields", {})

    # Fetch comments separately
    comments_url = f"{JIRA_BASE_URL}/rest/api/3/issue/{story_id}/comment"
    async with httpx.AsyncClient(timeout=30) as client:
        c_resp = await client.get(comments_url, auth=auth)
        comments_data = c_resp.json() if c_resp.status_code == 200 else {}

    return json.dumps(
        {
            "id": data.get("key"),
            "title": fields.get("summary"),
            "status": fields.get("status", {}).get("name"),
            "priority": fields.get("priority", {}).get("name"),
            "issue_type": fields.get("issuetype", {}).get("name"),
            "description": str(fields.get("description", "")),
            "labels": fields.get("labels", []),
            "comments": [
                str(c.get("body", "")) for c in comments_data.get("comments", [])
            ],
            "linked_issues": [
                link.get("inwardIssue", {}).get("key")
                or link.get("outwardIssue", {}).get("key")
                for link in fields.get("issuelinks", [])
            ],
        },
        indent=2,
    )


async def handle_jira_add_comment(args: dict) -> str:
    story_id = args["story_id"]
    comment = args["comment"]
    url = f"{JIRA_BASE_URL}/rest/api/3/issue/{story_id}/comment"

    body = {
        "body": {
            "type": "doc",
            "version": 1,
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": comment}]}
            ],
        }
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, auth=(JIRA_EMAIL, JIRA_TOKEN), json=body)
        resp.raise_for_status()

    return json.dumps({"success": True, "story_id": story_id})


async def handle_jira_update_status(args: dict) -> str:
    story_id = args["story_id"]
    status_name = args["status"]

    # First get available transitions
    trans_url = f"{JIRA_BASE_URL}/rest/api/3/issue/{story_id}/transitions"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(trans_url, auth=(JIRA_EMAIL, JIRA_TOKEN))
        resp.raise_for_status()
        transitions = resp.json().get("transitions", [])

    # Find matching transition
    transition_id = None
    for t in transitions:
        if t["name"].lower() == status_name.lower():
            transition_id = t["id"]
            break

    if not transition_id:
        available = [t["name"] for t in transitions]
        return json.dumps(
            {"error": f"Status '{status_name}' not found. Available: {available}"}
        )

    # Apply transition
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            trans_url,
            auth=(JIRA_EMAIL, JIRA_TOKEN),
            json={"transition": {"id": transition_id}},
        )
        resp.raise_for_status()

    return json.dumps({"success": True, "new_status": status_name})


async def handle_github_create_pr(args: dict) -> str:
    owner = args["owner"]
    repo = args["repo"]
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            url,
            headers=headers,
            json={
                "title": args["title"],
                "body": args["body"],
                "head": args["head"],
                "base": args.get("base", "main"),
            },
        )
        resp.raise_for_status()
        data = resp.json()

    return json.dumps(
        {
            "pr_number": data["number"],
            "pr_url": data["html_url"],
            "title": data["title"],
            "state": data["state"],
        }
    )


async def handle_github_get_repo_info(args: dict) -> str:
    owner = args["owner"]
    repo = args["repo"]
    url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    return json.dumps(
        {
            "name": data["name"],
            "description": data.get("description"),
            "language": data.get("language"),
            "default_branch": data["default_branch"],
            "topics": data.get("topics", []),
            "url": data["html_url"],
        }
    )


async def handle_github_list_files(args: dict) -> str:
    owner = args["owner"]
    repo = args["repo"]
    path = args.get("path", "")
    branch = args.get("branch", "main")
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers=headers, params={"ref": branch})
        resp.raise_for_status()
        items = resp.json()

    if not isinstance(items, list):
        items = [items]

    return json.dumps(
        [
            {
                "name": i["name"],
                "type": i["type"],
                "path": i["path"],
                "size": i.get("size", 0),
            }
            for i in items
        ]
    )


async def handle_github_get_file(args: dict) -> str:
    import base64

    owner = args["owner"]
    repo = args["repo"]
    path = args["path"]
    branch = args.get("branch", "main")
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers=headers, params={"ref": branch})
        resp.raise_for_status()
        data = resp.json()

    content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
    return json.dumps(
        {
            "path": data["path"],
            "name": data["name"],
            "size": data["size"],
            "content": content[:10000],
        }
    )


# ─── MCP Server Handlers ──────────────────────────────────────────────────────


@server.list_tools()
async def list_tools() -> ListToolsResult:
    return ListToolsResult(tools=TOOLS)


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> CallToolResult:
    handlers = {
        "jira_get_story": handle_jira_get_story,
        "jira_add_comment": handle_jira_add_comment,
        "jira_update_status": handle_jira_update_status,
        "github_create_pr": handle_github_create_pr,
        "github_get_repo_info": handle_github_get_repo_info,
        "github_list_files": handle_github_list_files,
        "github_get_file": handle_github_get_file,
    }

    handler = handlers.get(name)
    if not handler:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Unknown tool: {name}")]
        )

    try:
        result = await handler(arguments)
        return CallToolResult(content=[TextContent(type="text", text=result)])
    except Exception as e:
        logger.error(f"Tool {name} failed: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")], isError=True
        )


async def main():
    """Run the MCP server over stdio."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="ai-dev-agent",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=None, experimental_capabilities={}
                ),
            ),
        )


def create_mcp_server():
    """Return the configured MCP server instance."""
    return server


if __name__ == "__main__":
    asyncio.run(main())
