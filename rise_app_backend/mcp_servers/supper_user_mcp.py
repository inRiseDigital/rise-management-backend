# Supper user_MCP_server
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

BASE_URL = os.getenv("BASE_URL")        # e.g. "http://127.0.0.1:8000"
API_TOKEN = os.getenv("API_TOKEN")      # optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kitchen-mcp-server")

# create the FastMCP app
app = FastMCP("django-mcp-server")
TIMEOUT = 10.0

# Shared aiohttp session and lock
_shared_session: aiohttp.ClientSession | None = None
_session_lock = asyncio.Lock()


async def get_session() -> aiohttp.ClientSession:
    global _shared_session
    async with _session_lock:
        if _shared_session is None or _shared_session.closed:
            timeout = aiohttp.ClientTimeout(total=15)  # seconds
            headers = {}
            if API_TOKEN:
                headers["Authorization"] = f"Bearer {API_TOKEN}"
            _shared_session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return _shared_session


async def request_json(method: str, url: str, **kwargs) -> dict:
    """
    Make HTTP request and return {"data": ...} on 2xx or {"error":..., "status":...} on failure.
    kwargs forwarded to aiohttp session.request (e.g. json=..., params=...)
    """
    session = await get_session()
    try:
        async with session.request(method, url, **kwargs) as resp:
            status = resp.status
            # attempt JSON parse
            try:
                payload = await resp.json()
            except Exception:
                text = await resp.text()
                logger.warning("Non-JSON response from %s: %s", url, text)
                return {"error": "Invalid JSON from backend", "status": status, "raw": text}

            if 200 <= status < 300:
                return {"data": payload}
            else:
                logger.error("Error response %s from %s: %s", status, url, payload)
                return {"error": payload, "status": status}
    except asyncio.TimeoutError:
        logger.exception("Timeout when requesting %s", url)
        return {"error": "Request timed out", "status": None}
    except aiohttp.ClientError as e:
        logger.exception("Client error when requesting %s: %s", url, str(e))
        return {"error": str(e), "status": None}
    
#Store tools

@app.tool
async def add_store(name: str) -> dict:
    """
    Create a new store and return the server payload.

    Args:
        name: The store name to create.

    Returns:
        {
            "store": <server JSON (entire response or its 'data' field if present)>
        }
        or on failure:
        {
            "error": "<string>",
            "status": <optional int>,
            "message": "<optional details>"
        }
    """
    try:
        payload = {"name": name}
        result: Dict[str, Any] = await request_json(
            "POST",
            f"{BASE_URL}/stores/add_stores/",
            json=payload,
            timeout=10,
        )
    except asyncio.TimeoutError as e:
        return {"error": "TIMEOUT", "message": str(e)}
    except aiohttp.ClientError as e:
        return {"error": "NETWORK", "message": str(e)}

    if isinstance(result, dict) and "error" in result:
        # assuming your helper may normalize server errors like this
        return {"error": result.get("error"), "status": result.get("status"), "message": result.get("message")}

    # Prefer 'data' when present, else return whole result
    return {"store": result.get("data", result)}

@app.tool
async def update_store_by_id(store_id: int, data: dict) -> dict:
    """
    Update a specific store by its ID.

    This tool sends a PUT request to the Django endpoint
    `/stores/add_stores/{store_id}/` and returns the store data
    as a dictionary.
    
    Args:
        store_id (int): The ID of the store to retrieve.

    Returns:
        dict: Specific The store data.
    """
    result = await request_json("PUT", f"{BASE_URL}/stores/add_stores/{store_id}/", json=data)
    if "error" in result:
        if result.get("status") == 404:
            return {"error": "Store not found", "status": 404}
        return {"error": result["error"], "status": result.get("status")}
    return {"store": result["data"]}

@app.tool
async def delete_store_by_id(store_id: int) -> dict:
    """
    Delete a specific store by its ID.

    This tool sends a DELETE request to the Django endpoint
    `/stores/add_stores/{store_id}/` and returns the store data
    as a dictionary.
    
    Args:
        store_id (int): The ID of the store to retrieve.

    Returns:
        Confirmation message or error if not found..
    """
    result = await request_json("DELETE", f"{BASE_URL}/stores/add_stores/{store_id}/")
    if "error" in result:
        if result.get("status") == 404:
            return {"error": "Store not found", "status": 404}
        return {"error": result["error"], "status": result.get("status")}
    return {"message": "Store deleted successfully"}

@app.tool
async def add_product_category(name: str, store: int) -> dict:
    """
    Create a new product category.

    HTTP:
        POST /stores/categories/

    Args:
        name:  Category name (str)
        store: Store ID (int, FK)

    Returns:
        {"product_category": {...}} on success,
        or {"error": "...", "status": <int>} on failure.
    """
    payload = {"name": name, "store": store}
    result = await request_json("POST", f"{BASE_URL}/stores/categories/", json=payload)
    if "error" in result:
        status = result.get("status")
        if status == 400:
            return {"error": "Invalid data", "status": 400, "details": result.get("error")}
        return {"error": result["error"], "status": status}
    return {"product_category": result["data"]}

@app.tool
async def update_product_category_by_id(category_id: int, data: dict) -> dict:
    """
    Update a specific category by its ID.

    This tool sends a PUT request to the Django endpoint
    `/stores/categories/{category_id}/` and returns the updated category data
    as a dictionary.
    
    Args:
        id (int): The ID of the store to retrieve.
        name (str): The new name for the category.
        store (int): The ID of the store to associate with this category.

    Returns:
        dict: updated product category data.
    """
    result = await request_json("PUT", f"{BASE_URL}/stores/categories/{category_id}/", json=data)
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"product_category": result["data"]}

@app.tool
async def delete_product_category_by_id(category_id: int) -> dict:
    """
    Delete a specific product category by its ID.

    This tool sends a DELETE request to the Django endpoint
    `/stores/categories/{category_id}/` and returns a confirmation message
    when the deletion succeeds.

    Args:
        category_id (int): The ID of the product category to delete.

    Returns:
        dict: On success:
              {
                  "message": "Category deleted successfully"
              }
              On failure:
              {
                  "error": "<reason>",
                  "status": <HTTP status code>
              }
    """
    result = await request_json("DELETE", f"{BASE_URL}/stores/categories/{category_id}/")
    if "error" in result:
        if result.get("status") == 404:
            return {"error": "Category not found", "status": 404}
        return {"error": result["error"], "status": result.get("status")}
    return {"message": "Category deleted successfully"}

@app.tool
async def create_product_subcategory(data: dict) -> dict:
    """
    Create a new product subcategory.

    This tool sends a POST request to `/stores/subcategories/` to create a subcategory.

    Required Payload:
        data (dict): {
            "category": int,   # ID of the parent ProductCategory (FK)
            "name": str        # Subcategory name
        }

    Returns:
        dict: On success:
              {
                  "product_subcategory": { ...created subcategory... }
              }
              On failure:
              {
                  "error": "<reason>",
                  "status": <HTTP status code>
              }
    """
    result = await request_json("POST", f"{BASE_URL}/stores/subcategories/", json=data)
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"product_subcategory": result["data"]}


@app.tool
async def update_product_subcategory_by_id(subcategory_id: int, data: dict) -> dict:
    """
    Update a specific product subcategory by its ID.

    This tool sends a PUT request to the Django endpoint
    `/stores/subcategories/{subcategory_id}/` and returns the updated subcategory
    as a dictionary.

    Args:
        subcategory_id (int): The ID of the product subcategory to update.
        data (dict): Update payload. Expected keys:
            - "name" (str): New subcategory name.
            - "category" (int): ID of the parent ProductCategory (FK).
          Note: The endpoint uses PUT (full update). If your view does not allow
          partial updates, include all required fields even when changing only one.

    Returns:
        dict: On success:
              {
                  "product_subcategory": { ...updated subcategory... }
              }
              On failure:
              {
                  "error": "<reason>",
                  "status": <HTTP status code>
              }
    """
    result = await request_json("PUT", f"{BASE_URL}/stores/subcategories/{subcategory_id}/", json=data)
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"product_subcategory": result["data"]}

@app.tool
async def delete_product_subcategory_by_id(subcategory_id: int) -> dict:
    """
    Delete a specific product subcategory by its ID.

    This tool sends a DELETE request to the Django endpoint
    `/stores/subcategories/{subcategory_id}/` and returns a confirmation
    message when the deletion succeeds.

    Args:
        subcategory_id (int): The ID of the product subcategory to delete.

    Returns:
        dict: On success:
              {
                  "message": "Subcategory deleted successfully"
              }
              On failure:
              {
                  "error": "<reason>",
                  "status": <HTTP status code>
              }
    """
    result = await request_json("DELETE", f"{BASE_URL}/stores/subcategories/{subcategory_id}/")
    if "error" in result:
        if result.get("status") == 404:
            return {"error": "Subcategory not found", "status": 404}
        return {"error": result["error"], "status": result.get("status")}
    return {"message": "Subcategory deleted successfully"}

@app.tool
async def create_inventory_item(data: dict) -> dict:
    """
    Create a new inventory item.

    This tool sends a POST request to the Django endpoint
    `/stores/inventory/` to create an inventory record.

    Required Payload (data):
        store (int):        ID of the Store (FK).
        category (int):     ID of the ProductCategory (FK).
        subcategory (int):  ID of the ProductSubCategory (FK).
        units_in_stock (number | Decimal): Opening quantity (e.g.,  "5.00" or 5).
        unit_cost (number | Decimal):      Average unit cost (e.g., "61.6700" or 61.67).

    Returns:
        dict: On success:
              {
                  "inventory_item": { ...created item... }
              }
              On failure:
              {
                  "error": "<reason>",
                  "status": <HTTP status code>
              }
    """
    result = await request_json("POST", f"{BASE_URL}/stores/inventory/", json=data)
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"inventory_item": result["data"]}


@app.tool
async def update_inventory_item_by_id(item_id: int, data: dict) -> dict:
    """Update an inventory item by ID via the backend API.

    Sends a PUT request to ``{BASE_URL}/stores/inventory/{item_id}/`` with a JSON
    payload. The backend view accepts **partial** updates (server-side uses
    ``partial=True``), so ``data`` may contain any subset of fields accepted by
    ``InventoryItemSerializer``.

    Args:
        item_id: Primary key of the inventory item to update.
        data: JSON-serializable payload with serializer-defined fields
            (e.g., name, quantity, notes). Only include fields you intend to change.

    Returns:
        dict:
            - Success: ``{"inventory_item": <dict>}`` (the updated resource).
            - Failure: ``{"error": <str | dict>, "status": <int | None>}``.

    Raises:
        Any exception raised by ``request_json`` (e.g., network errors) will
        propagate to the caller.

    Example:
        >>> await update_inventory_item_by_id(12, {"quantity": 50})
        {'inventory_item': {'id': 12, 'quantity': 50, ...}}
    """
    result = await request_json("PUT", f"{BASE_URL}/stores/inventory/{item_id}/", json=data)
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"inventory_item": result["data"]}

@app.tool
async def delete_inventory_item_by_id(item_id: int) -> dict:
    """Delete an inventory item by its ID via the backend API.

    Sends a DELETE request to ``{BASE_URL}/stores/inventory/{item_id}/``.
    On success, returns a confirmation message. If the backend responds
    with a 404, a friendly "Item not found" error is returned.

    Args:
        item_id: Primary key of the inventory item to delete.

    Returns:
        dict:
            - Success: ``{"message": "Item deleted successfully"}``.
            - Not found: ``{"error": "Item not found", "status": 404}``.
            - Other error: ``{"error": <str | dict>, "status": <int | None>}``.

    Raises:
        Any exception raised by ``request_json`` (e.g., network issues) will
        propagate to the caller.

    Example:
        >>> await delete_inventory_item_by_id(12)
        {'message': 'Item deleted successfully'}
    """
    result = await request_json("DELETE", f"{BASE_URL}/stores/inventory/{item_id}/")
    if "error" in result:
        if result.get("status") == 404:
            return {"error": "Item not found", "status": 404}
        return {"error": result["error"], "status": result.get("status")}
    return {"message": "Item deleted successfully"}

@app.tool
async def inventory_receive(data: dict) -> dict:
    """Receive (ingress) inventory units for an item and update stock.

    Expects ``item_id`` in the input payload and posts the remaining fields to
    ``{BASE_URL}/stores/inventory/receive/{item_id}/``. The backend updates the
    item's stock and records a movement entry.

    Args:
        data: JSON-serializable payload with:
            - ``item_id`` (int, required): Primary key of the inventory item.
              This key is removed from the payload and used in the URL path.
            - ``units`` (int, required): Number of units received (> 0).
            - ``cost_per_unit`` (float, required): Unit cost (>= 0).

    Returns:
        dict:
            - Success: ``{"inventory_item": <dict>}`` (updated item as serialized
              by the backend).
            - Missing item_id: ``{"error": "Missing item_id"}``.
            - Failure: ``{"error": <str|dict>, "status": <int|None>}`` when the
              HTTP call fails or validation fails (e.g., 400).

    Raises:
        Any exception raised by ``request_json`` (e.g., network errors) will
        propagate to the caller.

    Example:
        >>> await inventory_receive({"item_id": 12, "units": 50, "cost_per_unit": 42.5})
        {'inventory_item': {'id': 12, 'name': 'Mineral Mix', 'quantity': 150, ...}}
    """
    item_id = data.pop("item_id", None)
    if item_id is None:
        return {"error": "Missing item_id"}
    result = await request_json(
        "POST",
        f"{BASE_URL}/stores/inventory/receive/{item_id}/",
        json=data,
    )
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"inventory_item": result["data"]}


@app.tool
async def inventory_issue(data: dict) -> dict:
    """Issue (egress) inventory units for an item and update stock.

    Expects ``item_id`` in the input payload and posts the remaining fields to
    ``{BASE_URL}/stores/inventory/issue/{item_id}/``. The backend decreases the
    item's stock and records a movement entry.

    Args:
        data: JSON-serializable payload with:
            - ``item_id`` (int, required): Primary key of the inventory item.
              This key is popped from the payload and used in the URL path.
            - ``units`` (int, required): Number of units to issue (> 0).

    Returns:
        dict:
            - Success: ``{"inventory_item": <dict>}`` (updated item as serialized
              by the backend).
            - Missing item_id: ``{"error": "Missing item_id"}``.
            - Failure: ``{"error": <str|dict>, "status": <int|None>}`` for HTTP or
              validation errors (e.g., insufficient stock).

    Raises:
        Any exception raised by ``request_json`` (e.g., network errors) will
        propagate to the caller.

    Example:
        >>> await inventory_issue({"item_id": 12, "units": 5})
        {'inventory_item': {'id': 12, 'name': 'Mineral Mix', 'quantity': 95, ...}}
    """
    item_id = data.pop("item_id", None)
    if item_id is None:
        return {"error": "Missing item_id"}
    result = await request_json(
        "POST",
        f"{BASE_URL}/stores/inventory/issue/{item_id}/",
        json=data,
    )
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"inventory_item": result["data"]}

@app.tool
async def get_inventory_movements() -> dict:
    """Fetch the inventory movement **ledger/history**.

    Calls ``{BASE_URL}/stores/inventory/movements/`` and returns a normalized
    payload of inventory **transactions** (IN/OUT). Use this to audit movement
    history, not to fetch current stock levels or item listings.

    Arguments:
        None.

    Returns:
        dict:
            - Success: ``{"inventory_movements": <list>}`` where each list item
              is an ``InventoryMovement`` serialized by the backend.
            - Failure: ``{"error": <str|dict>, "status": <int|None>}``.

    Notes:
        - This endpoint may support server-side filters such as ``direction``,
          ``store_id``, ``item_id``, ``start``, and ``end`` (see view docstring
          below). This tool calls the **unfiltered** list. If you need filters,
          extend this tool to accept query parameters.
        - Read-only and idempotent. Authentication/headers/timeouts are handled
          by ``request_json``.

    Raises:
        Any exception raised by ``request_json`` (e.g., network errors) will
        propagate to the caller.

    Example:
        >>> await get_inventory_movements()
        {"inventory_movements": [
            {"id": 301, "direction": "IN", "item": {...}, "units": 50, "occurred_at": "2025-09-01T10:15:00Z"},
            {"id": 302, "direction": "OUT", "item": {...}, "units": 5,  "occurred_at": "2025-09-01T12:00:00Z"},
            ...
        ]}
    """
    result = await request_json("GET", f"{BASE_URL}/stores/inventory/movements/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"inventory_movements": result["data"]}


#Housekeeping

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
async def create_subcategory(location: int, subcategory: str) -> dict:
    """Create a new subcategory for a specific location.

    This tool sends a POST request to the Django endpoint
    `/housekeeping/sub/` with the provided name and description.
    Returns the created subcategory details as a dictionary.
    """
    data = {"subcategory": subcategory, "location": location}
    result = await request_json("POST", f"{BASE_URL}/housekeeping/sub/", json=data)
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"subcategory": result["data"]}

@app.tool()
async def update_subcategory(subcategory_id: int, subcategory: str) -> dict:
    """Update an existing subcategory in the Django backend API.

    This tool sends a PUT request to the Django endpoint
    `/housekeeping/sub/<subcategory_id>/` with the provided name and description.
    Returns the updated subcategory details as a dictionary.
    """
    data = {"subcategory": subcategory}
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


#Kitchen

@app.tool()
async def create_new_kitchen_expense_category(name: str, description: str = "") -> dict:
    """
    Create a new kitchen expense category by calling the backend API.

    The function POSTs a JSON payload to the backend endpoint
    `{BASE_URL}/kitchen/category/` and returns the normalized response
    produced by the helper `_post_and_normalize`.

    Args:
        name (str): The category name. Required.
        description (str): Optional human-readable description of the category.

    Returns:
        dict: A normalized dictionary result from `_post_and_normalize`.
            Typical successful response:
                {"data": { "id": 42, "name": "Food", "description": "..." }, "status": 201}
            Typical error response:
                {"error": { ...validation errors... }, "status": 400}

    Example:
        >>> await create_new_kitchen_expense_category("Fruits", "Perishable items")
        {"data": {"id": 12, "name": "Fruits", "description": "Perishable items"}, "status": 201}

    Notes:
        - This function depends on the global `BASE_URL` and the helper
          `_post_and_normalize(url, data, success_status=201)` to perform the
          HTTP request and normalize errors into the above shapes.
        - The caller should inspect the returned dict for either a "data"
          key (success) or an "error" key (failure).
    """
    url = f"{BASE_URL}/kitchen/category/"
    data = {"name": name, "description": description}
    return await _post_and_normalize(url, data, success_status=201)

@app.tool()
async def update_kitchen_expense_category(category_id: int, name: str, description: str = "") -> dict:
    """
    Update an existing kitchen expense category via the backend API.

    HTTP endpoint called:
        PUT {BASE_URL}/kitchen/category/{category_id}/

    Args:
        category_id (int): ID of the category to update.
        name (str): New name for the category.
        description (str, optional): New description for the category.

    Returns:
        dict: Normalized response from `_put_and_normalize`.
            - Success example: {"data": {"id": 5, "name": "Food", "description": "...", "updated_at": "..."},
                                "status": 200}
            - Error example:   {"error": {"name": ["This field is required."]}, "status": 400}

    Notes:
        - This tool calls a helper `_put_and_normalize(url, data)` which must:
            * perform an async PUT request to `url` with JSON `data`,
            * return {"data": <parsed-json>, "status": <status>} on 2xx,
            * return {"error": <payload-or-string>, "status": <status>} for non-2xx/network errors.
        - The tool should NOT raise exceptions — always return a dict so the agent can report errors.
        - If you want partial updates, call the backend with PATCH and adjust helper accordingly.
    """
    url = f"{BASE_URL}/kitchen/category/{category_id}/"
    data = {"name": name, "description": description}
    return await _put_and_normalize(url, data)

























# --- small helpers to avoid repetition ---
async def _get_and_normalize(url: str) -> dict:
    resp = await request_json("GET", url)
    if "error" in resp:
        return {"error": resp["error"], "status": resp.get("status")}
    return {"data": resp["data"], "status": 200}


async def _post_and_normalize(url: str, data: dict, success_status: int = 201) -> dict:
    resp = await request_json("POST", url, json=data)
    if "error" in resp:
        return {"error": resp["error"], "status": resp.get("status")}
    return {"data": resp["data"], "status": success_status}


async def _put_and_normalize(url: str, data: dict) -> dict:
    resp = await request_json("PUT", url, json=data)
    if "error" in resp:
        return {"error": resp["error"], "status": resp.get("status")}
    return {"data": resp["data"], "status": 200}


async def _delete_and_normalize(url: str) -> dict:
    resp = await request_json("DELETE", url)
    if "error" in resp:
        return {"error": resp["error"], "status": resp.get("status")}
    # treat 204 or success as deletion confirmation
    if "data" in resp:
        return {"data": resp["data"], "status": 200}
    return {"data": "deleted", "status": 204}


# --- cleanup helpers ---
async def _shutdown():
    global _shared_session
    if _shared_session is not None and not _shared_session.closed:
        await _shared_session.close()
        logger.info("Closed shared aiohttp session")