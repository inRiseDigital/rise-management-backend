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
async def get_all_locations() -> dict:
    """Retrieve all house keeping location list of from the Django backend API.

    This tool sends a GET request to the Django endpoint
    `/housekeeping/location/` and returns all available house keeping locations
    as a dictionary.
    """
    result = await request_json("GET", f"{BASE_URL}/housekeeping/location/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"stores": result["data"]}

@app.tool()
async def create_location(name: str, description: str = "") -> dict:
    """Create a new house keeping location in the Django backend API.

    This tool sends a POST request to the Django endpoint
    `/housekeeping/location/` with the provided name and description.
    Returns the created location details as a dictionary.
    """
    data = {"name": name, "description": description}
    result = await request_json("POST", f"{BASE_URL}/housekeeping/location/", json=data)
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"location": result["data"]}

@app.tool()
async def get_location_by_id(location_id: int) -> dict:
    """Retrieve a specific house keeping location by its ID.

    This tool sends a GET request to the Django endpoint
    `/housekeeping/location/<location_id>/` and returns the details of the
    specified house keeping location.
    """
    result = await request_json("GET", f"{BASE_URL}/housekeeping/location/{location_id}/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"location": result["data"]}

@app.tool()
async def update_location(location_id: int, name: str, description: str = "") -> dict:
    """Update an existing house keeping location in the Django backend API.

    This tool sends a PUT request to the Django endpoint
    `/housekeeping/location/<location_id>/` with the provided name and description.
    Returns the updated location details as a dictionary.
    """
    data = {"name": name, "description": description}
    result = await request_json("PUT", f"{BASE_URL}/housekeeping/location/{location_id}/", json=data)
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"location": result["data"]}

@app.tool()
async def delete_location(location_id: int) -> dict:
    """Delete a house keeping location from the Django backend API.

    This tool sends a DELETE request to the Django endpoint
    `/housekeeping/location/<location_id>/` and returns the deleted location
    details as a dictionary.
    """
    result = await request_json("DELETE", f"{BASE_URL}/housekeeping/location/{location_id}/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"location": result["data"]}

@app.tool()
async def get_subcategories(location_id: int) -> dict:
    """Retrieve all subcategories .

    This tool sends a GET request to the Django endpoint
    `/housekeeping/locations/sub/` and returns all
    subcategories associated with the specified location.
    """
    result = await request_json("GET", f"{BASE_URL}/housekeeping/locations/sub/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"subcategories": result["data"]}

@app.tool()
async def create_subcategory(location_id: int, name: str, description: str = "") -> dict:
    """Create a new subcategory for a specific location.

    This tool sends a POST request to the Django endpoint
    `/housekeeping/sub/` with the provided name and description.
    Returns the created subcategory details as a dictionary.
    """
    data = {"name": name, "description": description, "location_id": location_id}
    result = await request_json("POST", f"{BASE_URL}/housekeeping/sub/", json=data)
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"subcategory": result["data"]}

@app.tool()
async def get_subcategory_by_id(subcategory_id: int) -> dict:
    """Retrieve a specific subcategory by its ID.

    This tool sends a GET request to the Django endpoint
    `/housekeeping/sub/<subcategory_id>/` and returns the details of the
    specified subcategory.
    """
    result = await request_json("GET", f"{BASE_URL}/housekeeping/sub/{subcategory_id}/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"subcategory": result["data"]}

@app.tool()
async def update_subcategory(subcategory_id: int, name: str, description: str = "") -> dict:
    """Update an existing subcategory in the Django backend API.

    This tool sends a PUT request to the Django endpoint
    `/housekeeping/sub/<subcategory_id>/` with the provided name and description.
    Returns the updated subcategory details as a dictionary.
    """
    data = {"name": name, "description": description}
    result = await request_json("PUT", f"{BASE_URL}/housekeeping/sub/{subcategory_id}/", json=data)
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"subcategory": result["data"]}

@app.tool()
async def delete_subcategory(subcategory_id: int) -> dict:
    """Delete a subcategory from the Django backend API.

    This tool sends a DELETE request to the Django endpoint
    `/housekeeping/sub/<subcategory_id>/` and returns the deleted subcategory
    details as a dictionary.
    """
    result = await request_json("DELETE", f"{BASE_URL}/housekeeping/sub/{subcategory_id}/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"subcategory": result["data"]}

@app.tool()
async def create_new_tasks(location_id: int, subcategory_id: int, task_name: str, description: str = "") -> dict:
    """Create a new task for a specific location and subcategory.

    This tool sends a POST request to the Django endpoint
    `/housekeeping/daily_task/` with the provided task details.
    Returns the created task details as a dictionary.
    """
    data = {
        "location_id": location_id,
        "subcategory_id": subcategory_id,
        "task_name": task_name,
        "description": description
    }
    result = await request_json("POST", f"{BASE_URL}/housekeeping/daily_task/", json=data)
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"task": result["data"]}

@app.tool()
async def update_task(task_id: int, task_name: str, description: str = "") -> dict:
    """Update an existing task in the Django backend API.

    This tool sends a PUT request to the Django endpoint
    `/housekeeping/daily_task/<task_id>/` with the provided task details.
    Returns the updated task details as a dictionary.
    """
    data = {"task_name": task_name, "description": description}
    result = await request_json("PUT", f"{BASE_URL}/housekeeping/daily_task/{task_id}/", json=data)
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"task": result["data"]}

@app.tool()
async def delete_task(task_id: int) -> dict:
    """Delete a task from the Django backend API.

    This tool sends a DELETE request to the Django endpoint
    `/housekeeping/daily_task/<task_id>/` and returns the deleted task
    details as a dictionary.
    """
    result = await request_json("DELETE", f"{BASE_URL}/housekeeping/daily_task/{task_id}/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"task": result["data"]}

@app.tool()
async def get_tasks_by_location(location_id: int) -> dict:
    """Retrieve all tasks for a specific location.

    This tool sends a GET request to the Django endpoint
    `/housekeeping/task_by_location/<location_id>/` and returns all tasks
    associated with the specified location.
    """
    result = await request_json("GET", f"{BASE_URL}/housekeeping/task_by_location/{location_id}/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"tasks": result["data"]}

@app.tool()
async def get_tasks_by_period(start_date: str, end_date: str) -> dict:
    """Retrieve tasks done in a selected time period.

    This tool sends a GET request to the Django endpoint
    `/housekeeping/tasks/by-period/` with the specified start and end dates.
    Returns the tasks grouped by period as a dictionary.
    """
    params = {"start_date": start_date, "end_date": end_date}
    result = await request_json("GET", f"{BASE_URL}/housekeeping/tasks/by-period/", params=params)
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"tasks_by_period": result["data"]}

@app.tool()
async def generate_task_report_pdf(start_date: str, end_date: str) -> dict:
    """Generate a PDF report for tasks done in a selected time period.

    This tool sends a GET request to the Django endpoint
    `/housekeeping/tasks/pdf-by-period/` with the specified start and end dates.
    Returns the PDF report as a dictionary.
    """
    params = {"start_date": start_date, "end_date": end_date}
    result = await request_json("GET", f"{BASE_URL}/housekeeping/tasks/pdf-by-period/", params=params)
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"pdf_report": result["data"]}

@app.tool()
async def get_subcategories_by_location(location_id: int) -> dict:
    """Retrieve all subcategories for a specific location.

    This tool sends a GET request to the Django endpoint
    `/housekeeping/locations/subcategories/<location_id>/` and returns all
    subcategories associated with the specified location.
    """
    result = await request_json("GET", f"{BASE_URL}/housekeeping/locations/subcategories/{location_id}/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"subcategories": result["data"]}
