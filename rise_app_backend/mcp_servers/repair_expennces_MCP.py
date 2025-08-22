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
async def get_all_expences_categories() -> dict:
    """Retrive All expences categories deals  from the Django backend API.

    This tool sends a GET request to the Django endpoint
    `/repair_expenses/categories/` and create new MEP project.
    """
    result = await request_json("GET", f"{BASE_URL}/repair_expenses/categories/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"stores": result["data"]}

@app.tool()
async def create_expence_category(name: str) -> dict:
    """Create a new expence category in the Django backend API.

    This tool sends a POST request to the Django endpoint
    `/repair_expenses/categories/` to create a new expence category.
    """
    data = {"name": name}
    result = await request_json("POST", f"{BASE_URL}/repair_expenses/categories/", json=data)
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"category": result["data"]}

@app.tool()
async def get_expences_category_by_id(id: int) -> dict:
    """Retrieve expences category by ID from the Django backend API.

    This tool sends a GET request to the Django endpoint
    `/repair_expenses/categories/{id}/` to fetch expences details.
    """
    result = await request_json("GET", f"{BASE_URL}/repair_expenses/categories/{id}/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"expense": result["data"]}
   
@app.tool()
async def update_expence_category(id: int, name: str) -> dict:
    """Update an existing expence category in the Django backend API.

    This tool sends a PUT request to the Django endpoint
    `/repair_expenses/categories/{id}/` to update expence details.
    """
    data = {"name": name}
    result = await request_json("PUT", f"{BASE_URL}/repair_expenses/categories/{id}/", json=data)
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"category": result["data"]}

@app.tool()
async def delete_expence_category(id: int) -> dict:
    """Delete an expence category by ID from the Django backend API.

    This tool sends a DELETE request to the Django endpoint
    `/repair_expenses/categories/{id}/` to remove the expence category.
    """
    result = await request_json("DELETE", f"{BASE_URL}/repair_expenses/categories/{id}/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"status": "deleted"}

@app.tool()
async def get_all_expences() -> dict:
    """Retrive All expences deals  from the Django backend API.

    This tool sends a GET request to the Django endpoint
    `/repair_expenses/` and create new MEP project.
    """
    result = await request_json("GET", f"{BASE_URL}/repair_expenses/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"stores": result["data"]}

@app.tool()
async def create_expence(date: str, responsible_person: str,category: str, subcategory: str, bill_img: str,bill_no: str, cost: float, description: str ) -> dict:
    """Create a new expence in the Django backend API.

    This tool sends a POST request to the Django endpoint
    `/repair_expenses/` to create a new expence.
    """
    data = {
        "date": date,
        "responsible_person": responsible_person,
        "category": category,
        "subcategory": subcategory,
        "bill_img": bill_img,
        "bill_no": bill_no,
        "cost": cost,
        "description": description
    }
    result = await request_json("POST", f"{BASE_URL}/repair_expenses/", json=data)
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"expense": result["data"]}