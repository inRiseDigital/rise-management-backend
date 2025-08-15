import aiohttp
import asyncio
import os
import logging
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from fastmcp.tools import tool

load_dotenv()
BASE_URL = os.getenv("BASE_URL")
API_TOKEN = os.getenv("API_TOKEN")  # optional: e.g., Bearer token or similar

if not BASE_URL:
    raise RuntimeError("BASE_URL is not set in environment")

# configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("django-mcp-server")

app = FastMCP("django-mcp-server")

# Shared session
_shared_session: aiohttp.ClientSession | None = None
_session_lock = asyncio.Lock()


async def get_session() -> aiohttp.ClientSession:

    """
    Obtain a shared aiohttp.ClientSession instance.

    This function initializes and returns a global shared aiohttp.ClientSession
    instance. It ensures that only one session is open at any given time, using
    an asyncio lock to manage access. If the session is closed or not yet created,
    a new session is initialized with a default timeout and optional authorization
    headers.

    Returns:
        aiohttp.ClientSession: The shared client session for making HTTP requests.
    """


    global _shared_session
    async with _session_lock:
        if _shared_session is None or _shared_session.closed:
            timeout = aiohttp.ClientTimeout(total=10)  # 10s default timeout
            headers = {}
            if API_TOKEN:
                headers["Authorization"] = f"Bearer {API_TOKEN}"
            _shared_session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return _shared_session


async def request_json(method: str, url: str, **kwargs) -> dict:
    """
    Helper for making HTTP requests and normalizing JSON responses.
    Returns either {"data": ...} on success or {"error": ..., "status": ...} on failure.
    """
    session = await get_session()
    try:
        async with session.request(method, url, **kwargs) as resp:
            status = resp.status
            try:
                payload = await resp.json()
            except Exception:
                text = await resp.text()
                logger.warning("Non-JSON response from %s: %s", url, text)
                return {"error": "Invalid JSON from backend", "status": status, "raw": text}

            if status >= 400:
                logger.error("Error response %s from %s: %s", status, url, payload)
                return {"error": payload, "status": status}
            return {"data": payload}
    except asyncio.TimeoutError:
        logger.exception("Timeout when requesting %s", url)
        return {"error": "Request timed out", "status": None}
    except aiohttp.ClientError as e:
        logger.exception("Client error when requesting %s: %s", url, str(e))
        return {"error": str(e), "status": None}
    
@app.tool()
async def get_task_list() -> dict:
    """
    Fetch the list of tasks from the backend.
    """
    url = f"{BASE_URL}/tasks/"
    response = await request_json("GET", url)
    if "error" in response:
        return {"error": response["error"], "status": response.get("status", 500)}
    return {"data": response["data"]}

@app.tool()
async def create_task(task_data: dict) -> dict:
    """
    Create a new task with the provided data.
    """
    url = f"{BASE_URL}/tasks/"
    response = await request_json("POST", url, json=task_data)
    if "error" in response:
        return {"error": response["error"], "status": response.get("status", 500)}
    return {"data": response["data"]}

@app.tool()
async def get_task_detail(task_id: int) -> dict:
    """
    Fetch details of a specific task by ID.
    """
    url = f"{BASE_URL}/tasks/{task_id}/"
    response = await request_json("GET", url)
    if "error" in response:
        return {"error": response["error"], "status": response.get("status", 500)}
    return {"data": response["data"]}

@app.tool()
async def update_task(task_id: int, task_data: dict) -> dict:
    """
    Update an existing task with the provided data.
    """
    url = f"{BASE_URL}/tasks/{task_id}/"
    response = await request_json("PUT", url, json=task_data)
    if "error" in response:
        return {"error": response["error"], "status": response.get("status", 500)}
    return {"data": response["data"]}

@app.tool()
async def delete_task(task_id: int) -> dict:
    """
    Delete a specific task by ID.
    """
    url = f"{BASE_URL}/tasks/{task_id}/"
    response = await request_json("DELETE", url)
    if "error" in response:
        return {"error": response["error"], "status": response.get("status", 500)}
    return {"data": "Task deleted successfully"}

