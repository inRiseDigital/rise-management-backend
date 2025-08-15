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
async def create_new_kitchen_expense_category(name: str,description: str = "",) -> dict:
    """
    Create a new kitchen expense category.
    """
    url = f"{BASE_URL}/kitchen/category/"
    data = {"name": name, "description": description}
    response = await request_json("POST", url, json=data)
    
    if "error" in response:
        return {"error": response["error"], "status": response.get("status", None)}
    
    return {"data": response["data"], "status": 201}

@app.tool()
async def get_all_kitchen_expense_categories() -> dict:
    """
    Retrieve all kitchen expense categories.
    """
    url = f"{BASE_URL}/kitchen/category/"
    response = await request_json("GET", url)
    
    if "error" in response:
        return {"error": response["error"], "status": response.get("status", None)}
    
    return {"data": response["data"], "status": 200}

@app.tool()
async def update_kitchen_expense_category(category_id: int, name: str, description: str = "") -> dict:
    """
    Update an existing kitchen expense category.
    """
    url = f"{BASE_URL}/kitchen/category/{category_id}/"
    data = {"name": name, "description": description}
    response = await request_json("PUT", url, json=data)
    
    if "error" in response:
        return {"error": response["error"], "status": response.get("status", None)}
    
    return {"data": response["data"], "status": 200}

@app.tool()
async def delete_kitchen_expense_category(category_id: int) -> dict:
    """
    Delete a kitchen expense category.
    """
    url = f"{BASE_URL}/kitchen/category/{category_id}/"
    response = await request_json("DELETE", url)
    
    if "error" in response:
        return {"error": response["error"], "status": response.get("status", None)}
    
    return {"data": "Category deleted successfully", "status": 204}

@app.tool()
async def create_kitchen_expense(category_id: int, amount: float, date: str, responsible_person: str, description: str = "", bill_no: str = "", image: str = "") -> dict:
    """
    Create a new kitchen expense.
    """
    url = f"{BASE_URL}/kitchen/expense/"
    data = {
        "category": category_id,
        "amount": amount,
        "date": date,
        "responsible_person": responsible_person,
        "description": description,
        "bill_no": bill_no,
        "image": image
    }
    response = await request_json("POST", url, json=data)
    
    if "error" in response:
        return {"error": response["error"], "status": response.get("status", None)}
    
    return {"data": response["data"], "status": 201}

@app.tool()
async def get_all_kitchen_expenses() -> dict:
    """
    Retrieve all kitchen expenses.
    """
    url = f"{BASE_URL}/kitchen/expense/"
    response = await request_json("GET", url)
    
    if "error" in response:
        return {"error": response["error"], "status": response.get("status", None)}
    
    return {"data": response["data"], "status": 200}

@app.tool()
async def get_kitchen_expense_details_by_id(expense_id: int) -> dict:
    """
    Retrieve details of a specific kitchen expense by its ID.
    """
    url = f"{BASE_URL}/kitchen/expense/{expense_id}/"
    response = await request_json("GET", url)
    
    if "error" in response:
        return {"error": response["error"], "status": response.get("status", None)}
    
    return {"data": response["data"], "status": 200}

@app.tool()
async def update_kitchen_expense(expense_id: int, category_id: int, amount: float, date: str, responsible_person: str, description: str = "", bill_no: str = "", image: str = "") -> dict:
    """
    Update an existing kitchen expense.
    """
    url = f"{BASE_URL}/kitchen/expense/{expense_id}/"
    data = {
        "category": category_id,
        "amount": amount,
        "date": date,
        "responsible_person": responsible_person,
        "description": description,
        "bill_no": bill_no,
        "image": image
    }
    response = await request_json("PUT", url, json=data)
    
    if "error" in response:
        return {"error": response["error"], "status": response.get("status", None)}
    
    return {"data": response["data"], "status": 200}

@app.tool()
async def delete_kitchen_expense(expense_id: int) -> dict:
    """
    Delete a kitchen expense by its ID.
    """
    url = f"{BASE_URL}/kitchen/expense/{expense_id}/"
    response = await request_json("DELETE", url)
    
    if "error" in response:
        return {"error": response["error"], "status": response.get("status", None)}
    
    return {"data": "Expense deleted successfully", "status": 204}

@app.tool()
async def get_expenses_by_category(category_id: int) -> dict:
    """
    Retrieve all expenses for a specific kitchen category.
    """
    url = f"{BASE_URL}/kitchen/category/expenses/{category_id}/"
    response = await request_json("GET", url)
    
    if "error" in response:
        return {"error": response["error"], "status": response.get("status", None)}
    
    return {"data": response["data"], "status": 200}

@app.tool()
async def generate_kitchen_report(start_date: str, end_date: str) -> dict:
    """
    Generate a kitchen report for a specific period.
    """
    url = f"{BASE_URL}/kitchen/report/?start_date={start_date}&end_date={end_date}"
    response = await request_json("GET", url)
    
    if "error" in response:
        return {"error": response["error"], "status": response.get("status", None)}
    
    return {"data": response["data"], "status": 200}