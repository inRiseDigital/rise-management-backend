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


# === Stores ===

@app.tool()
async def get_all_milk_entries() -> dict:
    """Retrieve all Milk entry data list of from the Django backend API.

    This tool sends a GET request to the Django endpoint
    `/cattle_hut/milk/` and returns all available store data
    as a dictionary.
    """
    result = await request_json("GET", f"{BASE_URL}/cattle_hut/milk/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"stores": result["data"]}

@app.tool()
async def get_all_milk_entrys_in_time_period(start_date: str, end_date: str) -> dict:
    """Retrieve all Milk entry data list of from the Django backend API within a specific time period.

    This tool sends a GET request to the Django endpoint
    `/cattle_hut/milk/?start_date=<start_date>&end_date=<end_date>` and returns all available store data
    as a dictionary.
    """
    result = await request_json("GET", f"{BASE_URL}/cattle_hut/milk/?start_date={start_date}&end_date={end_date}")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"stores": result["data"]}

@app.tool()
async def create_milk_entry(data: dict) -> dict:
    """Create a new milk entry."""
    result = await request_json("POST", f"{BASE_URL}/cattle_hut/milk/", json=data)
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"milk_entry": result["data"]}

@app.tool()
async def get_milk_entry_by_id(id: int) -> dict:
    """Retrieve a specific milk entry by its ID."""
    result = await request_json("GET", f"{BASE_URL}/cattle_hut/milk/{id}/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"milk_entry": result["data"]}

@app.tool()
async def update_milk_entry(id: int, data: dict) -> dict:
    """Update an existing milk entry by its ID."""
    result = await request_json("PUT", f"{BASE_URL}/cattle_hut/milk/{id}/", json=data)
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"milk_entry": result["data"]}

@app.tool()
async def delete_milk_entry(id: int) -> dict:
    """Delete a milk entry by its ID."""
    result = await request_json("DELETE", f"{BASE_URL}/cattle_hut/milk/{id}/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"message": "Milk entry deleted successfully"}

@app.tool()
async def get_all_cost_entries() -> dict:
    """Retrieve all cost entries from the Django backend API."""
    result = await request_json("GET", f"{BASE_URL}/cattle_hut/costs/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"costs": result["data"]}

@app.tool()
async def create_cost_entry(data: dict) -> dict:
    """Create a new cost entry."""
    result = await request_json("POST", f"{BASE_URL}/cattle_hut/costs/", json=data)
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"cost_entry": result["data"]}

@app.tool()
async def get_cost_entry_by_id(id: int) -> dict:
    """Retrieve a specific cost entry by its ID."""
    result = await request_json("GET", f"{BASE_URL}/cattle_hut/costs/{id}/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"cost_entry": result["data"]}

@app.tool()
async def update_cost_entry(id: int, data: dict) -> dict:
    """Update an existing cost entry by its ID."""
    result = await request_json("PUT", f"{BASE_URL}/cattle_hut/costs/{id}/", json=data)
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"cost_entry": result["data"]}

@app.tool()
async def delete_cost_entry(id: int) -> dict:
    """Delete a cost entry by its ID."""
    result = await request_json("DELETE", f"{BASE_URL}/cattle_hut/costs/{id}/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"message": "Cost entry deleted successfully"}

@app.tool()
async def export_milk_collection_pdf(start_date: str, end_date: str) -> dict:
    """
    Export milk collection data as a PDF report between given start and end dates.

    Args:
        start_date (str): Start date in 'YYYY-MM-DD' format.
        end_date (str): End date in 'YYYY-MM-DD' format.

    Returns:
        dict: {
            "filename": <downloaded filename>,
            "file_path": <local path if saved>,
            "message": Success or error message
        }
    """
    url = f"{BASE_URL}/milk/milk_pdf_export/"
    params = {"start_date": start_date, "end_date": end_date}

    session = await get_session()
    try:
        async with session.get(url, params=params) as resp:
            if resp.status != 200:
                return {"error": f"Failed to export PDF. Status code: {resp.status}"}

            content_disposition = resp.headers.get("Content-Disposition", "")
            filename = "milk_report.pdf"
            if "filename=" in content_disposition:
                filename = content_disposition.split("filename=")[-1].strip('"')

            # Save to local file (optional)
            output_path = f"./{filename}"
            with open(output_path, "wb") as f:
                f.write(await resp.read())

            return {
                "filename": filename,
                "file_path": output_path,
                "message": f"Milk report PDF successfully downloaded as {filename}"
            }

    except Exception as e:
        return {"error": str(e)}

@app.tool()
async def get_latest_milk_collection() -> dict:
    """
    Fetch the latest milk collection entry.

    Returns:
        dict: Latest milk collection data or an error message.
    """
    result = await request_json("GET", f"{BASE_URL}/milk/latest/")
    if "error" in result:
        if result.get("status") == 404:
            return {"error": "No milk collection entry found", "status": 404}
        return {"error": result["error"], "status": result.get("status")}
    return {"latest_milk_collection": result["data"]}

@app.tool()
async def get_month_to_date_income(date: str = None) -> dict:
    """
    Fetch the month-to-date income for milk collection.

    Args:
        date (str): Optional date in 'YYYY-MM-DD' format. If not provided, defaults to today.

    Returns:
        dict: Month-to-date income data or an error message.
    """
    url = f"{BASE_URL}/milk/month_to_date_income/"
    params = {}
    if date:
        params["date"] = date

    result = await request_json("GET", url, params=params)
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"month_to_date_income": result["data"]}