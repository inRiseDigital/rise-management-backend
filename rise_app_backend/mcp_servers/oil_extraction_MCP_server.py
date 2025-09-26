# kitchen_MCP_server.py
import asyncio
import os
import logging
from dotenv import load_dotenv
import aiohttp
from fastmcp import FastMCP  # ensure fastmcp is installed
# from fastmcp.tools import tool   # not needed if we use @app.tool
import requests
from typing import Dict, Any
import httpx


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
async def get_all_machines_deals() -> dict:
    """Retrive All machines deals  from the Django backend API.

    This tool sends a GET request to the Django endpoint
    `/oil/machines/` and create new MEP project.
    """
    result = await request_json("GET", f"{BASE_URL}/oil/machines/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"stores": result["data"]}

@app.tool()
async def add_new_machine(name: str, description: str,) -> dict:
    """Add a new machine to the Django backend API.

    Args:
        name (str): _description_
        description (str): _description_

    Returns:
        dict: _description_
    """
    data = {"name": name, "description": description}
    result = await request_json("POST", f"{BASE_URL}/oil/machines/", json=data)
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"machine": result["data"]}

@app.tool()
async def Retrieve_machine_by_id(machine_id: int) -> dict:
    """Retrieve a machine by its ID from the Django backend API.

    Args:
        machine_id (int): The ID of the machine to retrieve.

    Returns:
        dict: The machine data or an error message.
    """
    result = await request_json("GET", f"{BASE_URL}/oil/machines/{machine_id}/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"machine": result["data"]}

@app.tool()
async def update_machine(machine_id: int, name: str, description: str) -> dict:
    """Update an existing machine in the Django backend API.

    Args:
        machine_id (int): The ID of the machine to update.
        name (str): The new name for the machine.
        description (str): The new description for the machine.

    Returns:
        dict: The updated machine data or an error message.
    """
    data = {"name": name, "description": description}
    result = await request_json("PUT", f"{BASE_URL}/oil/machines/{machine_id}/", json=data)
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"machine": result["data"]}

@app.tool()
async def delete_machine(machine_id: int) -> dict:
    """Delete a machine from the Django backend API.

    Args:
        machine_id (int): The ID of the machine to delete.

    Returns:
        dict: The deleted machine data or an error message.
    """
    result = await request_json("DELETE", f"{BASE_URL}/oil/machines/{machine_id}/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"machine": result["data"]}

@app.tool()
async def get_all_oil_extraction_deatails() -> dict:
    """Retrieve all oil extraction details from the Django backend API.

    This tool sends a GET request to the Django endpoint
    `/oil/extraction/` and retrieves all oil extraction details.
    """
    result = await request_json("GET", f"{BASE_URL}/oil/extractions/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"extraction_details": result["data"]}

@app.tool()
async def add_new_oil_extraction_detail(id: int, date: str,leaf_type:str, input_weight:float, output_weight:float, price:float) -> dict:
    """Add a new oil extraction detail to the Django backend API.

    Args:
        machine_id (int): The ID of the machine associated with the oil extraction detail.
        date (str): The date of the oil extraction detail.
        leaf_type (str): The type of leaf used in the oil extraction detail.
        input_weight (float): The input weight of the oil extraction detail.
        output_weight (float): The output weight of the oil extraction detail.
        price (float): The price of the oil extraction detail.

    Returns:
        dict: The added oil extraction detail data or an error message.
    """
    data = {"machine_id": id, "date": date, "leaf_type": leaf_type, "input_weight": input_weight, "output_weight": output_weight, "price": price}
    result = await request_json("POST", f"{BASE_URL}/oil/extractions/", json=data)
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"extraction_detail": result["data"]}

@app.tool()
async def Retrieve_oil_extraction_detail_by_id(id: int) -> dict:
    """Retrieve an oil extraction detail by its ID from the Django backend API.

    Args:
        detail_id (int): The ID of the oil extraction detail to retrieve.

    Returns:
        dict: The oil extraction detail data or an error message.
    """
    result = await request_json("GET", f"{BASE_URL}/oil/extractions/{id}/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"extraction_detail": result["data"]}

@app.tool()
async def update_oil_extraction_detail(id: int, machine_id: int, date: str, leaf_type:str, input_weight:float, output_weight:float, price:float) -> dict:
    """Update an existing oil extraction detail in the Django backend API.

    Args:
        detail_id (int): The ID of the oil extraction detail to update.
        machine_id (int): The ID of the machine associated with the oil extraction detail.
        date (str): The date of the oil extraction detail.
        leaf_type (str): The type of leaf used in the oil extraction detail.
        input_weight (float): The input weight of the oil extraction detail.
        output_weight (float): The output weight of the oil extraction detail.
        price (float): The price of the oil extraction detail.

    Returns:
        dict: The updated oil extraction detail data or an error message.
    """
    data = {"machine_id": machine_id, "date": date, "leaf_type": leaf_type, "input_weight": input_weight, "output_weight": output_weight, "price": price}
    result = await request_json("PUT", f"{BASE_URL}/oil/extractions/{id}/", json=data)
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"extraction_detail": result["data"]}

@app.tool()
async def delete_oil_extraction_detail(id: int) -> dict:
    """Delete an oil extraction detail from the Django backend API.

    Args:
        detail_id (int): The ID of the oil extraction detail to delete.

    Returns:
        dict: The deleted oil extraction detail data or an error message.
    """
    result = await request_json("DELETE", f"{BASE_URL}/oil/extractions/{id}/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"extraction_detail": result["data"]}

@app.tool()
async def get_oil_perchased_details() -> dict:
    """Retrieve all oil purchased details from the Django backend API.

    This tool sends a GET request to the Django endpoint
    `/oil/purchase/` and retrieves all oil purchased details.
    """
    result = await request_json("GET", f"{BASE_URL}/oil/oil-purchases/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"purchased_details": result["data"]}

@app.tool()
async def add_new_oil_purchased_detail(date: str, oil_type:str, volume:float, received_by:str,location:str,authorized_by:str,remarks:str) -> dict:
    """Add a new oil purchased detail to the Django backend API.

    Args:
        date (str): The date of the oil purchased detail.
        supplier_name (str): The name of the supplier for the oil purchased detail.
        quantity (float): The quantity of oil purchased.
        price (float): The price of the oil purchased detail.

    Returns:
        dict: The added oil purchased detail data or an error message.
    """
    data = {"date": date, "oil_type": oil_type, "volume": volume, "received_by": received_by, "location": location, "authorized_by": authorized_by, "remarks": remarks}
    result = await request_json("POST", f"{BASE_URL}/oil/oil-purchases/", json=data)
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"purchased_detail": result["data"]}

@app.tool()
async def Retrieve_oil_purchased_detail_by_id(id: int) -> dict:
    """Retrieve an oil purchased detail by its ID from the Django backend API.

    Args:
        detail_id (int): The ID of the oil purchased detail to retrieve.

    Returns:
        dict: The oil purchased detail data or an error message.
    """
    result = await request_json("GET", f"{BASE_URL}/oil/oil-purchases/{id}/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"purchased_detail": result["data"]}

@app.tool()
async def update_oil_purchased_detail(id: int, date: str, supplier_name:str, quantity:float, price:float) -> dict:
    """Update an existing oil purchased detail in the Django backend API.

    Args:
        detail_id (int): The ID of the oil purchased detail to update.
        date (str): The date of the oil purchased detail.
        supplier_name (str): The name of the supplier for the oil purchased detail.
        quantity (float): The quantity of oil purchased.
        price (float): The price of the oil purchased detail.

    Returns:
        dict: The updated oil purchased detail data or an error message.
    """
    data = {"date": date, "supplier_name": supplier_name, "quantity": quantity, "price": price}
    result = await request_json("PUT", f"{BASE_URL}/oil/oil-purchases/{id}/", json=data)
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"purchased_detail": result["data"]}

@app.tool()
async def delete_oil_purchased_detail(id: int) -> dict:
    """Delete an oil purchased detail from the Django backend API.

    Args:
        detail_id (int): The ID of the oil purchased detail to delete.

    Returns:
        dict: The deleted oil purchased detail data or an error message.
    """
    result = await request_json("DELETE", f"{BASE_URL}/oil/oil-purchases/{id}/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"purchased_detail": result["data"]}


if __name__ == "__main__":
    #try:
    #    app.run(transport='sse')
    #finally:
        # best-effort cleanup; if event loop is still running, schedule close
    #    asyncio.run(_shutdown())
    print("Starting MCP SSE server on http://127.0.0.1:9000")
    app.run(transport="sse", host="127.0.0.1", port=9000)