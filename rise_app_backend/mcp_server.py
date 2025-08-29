import aiohttp
import asyncio
import os
import logging
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from fastmcp.tools import tool
from fastmcp import FastMCP
import requests
from typing import Dict, Any

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
                print(f"Requesting {method} {url} with params: {kwargs.get('params', {})} and json: {kwargs.get('json', {})}")
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

@app.tool
async def get_stores() -> dict:
    """
    List all stores.

    HTTP:
        GET /stores/add_stores/

    Returns:
        {"stores": <server JSON>} on success,
        or {"error": <str|obj>, "status": <int>, "details"?: <str>} on failure.

    Notes:
        • Not for creating categories.
        • Not for validating store IDs when an ID is already supplied elsewhere.
    """
    try:
        res=requests.get("http://127.0.0.1:8000/stores/add_stores/")
                
        res=res.json()
        
        return {"stores": res}
    except requests.RequestException as e:
        logger.exception("Failed to fetch stores: %s", str(e))
        # Return a structured error response instead of a raw string
        return {"error": "Failed to fetch stores", "status": None, "details": str(e)}
    except Exception as e:
        logger.exception("Failed to fetch stores: %s", str(e))
        print(f"Failed to fetch stores: {str(e.args)}")  # Print the error message to the console instead o f"error": "Failed to fetch stores", "status": None}


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
async def get_store_by_id(store_id: int) -> dict:
    """
    Retrieve a store by ID.

    HTTP:
        GET /stores/add_stores/{store_id}/

    Path:
        store_id (int) — store primary key.

    Returns:
        {"store": <store JSON>} on success,
        {"error": "Store not found", "status": 404} if missing,
        or {"error": <str|obj>, "status": <int>} on other failures.
    """
    result = await request_json("GET", f"{BASE_URL}/stores/add_stores/{store_id}/")
    if "error" in result:
        if result.get("status") == 404:
            return {"error": "Store not found", "status": 404}
        return {"error": result["error"], "status": result.get("status")}
    return {"store": result["data"]}

@app.tool
async def get_store_by_name(name: str) -> dict:
    """
    Retrieve a store by name.

    HTTP:
        GET /stores/add_stores/{name}/

    Path:
        name (str) — store name.

    Returns:
        {"store": <store JSON>} on success,
        {"error": "Store not found", "status": 404} if missing,
        or {"error": <str|obj>, "status": <int>} on other failures.

    Notes:
        Endpoint path shape follows current backend routing.
    """
    result = await request_json("GET", f"{BASE_URL}/stores/add_stores/{name}/")
    if "error" in result:
        if result.get("status") == 404:
            return {"error": "Store not found", "status": 404}
        return {"error": result["error"], "status": result.get("status")}
    return {"store": result["data"]}

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


# === Product Categories ===

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
async def get_product_categories() -> dict:
    """
    Fetch a all categories.

    This tool sends a GET request to the Django endpoint
    `/stores/categories/` and returns the categories data
    as a dictionary.
    

    Returns:
        dict: Return all product categories.
    """
    result = await request_json("GET", f"{BASE_URL}/stores/categories/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"product_categories": result["data"]}


@app.tool
async def get_product_category_by_id(category_id: int) -> dict:
    
    """
    Fetch a specific Product category by its ID.

    This tool sends a GET request to the Django endpoint
    `/stores/categories/{category_id}/` and returns the product category data
    as a dictionary.
    
    Args:
        category_id (int): The ID of the category to retrieve.

    Returns:
        dict: specific product category data.
    """
    
    result = await request_json("GET", f"{BASE_URL}/stores/categories/{category_id}/")
    if "error" in result:
        if result.get("status") == 404:
            return {"error": "Category not found", "status": 404}
        return {"error": result["error"], "status": result.get("status")}
    return {"product_category": result["data"]}


@app.tool
async def update_product_category_by_id(category_id: int, data: dict) -> dict:
    """
    Update a specific category by its ID.

    This tool sends a GET request to the Django endpoint
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


# === Product Subcategories ===

@app.tool
async def get_product_subcategories() -> dict:
    """
    Retrieve all product subcategories.

    This tool sends a GET request to the Django endpoint
    `/stores/subcategories/` and returns the full list of product subcategories
    as a dictionary.

    Args:
        None

    Returns:
        dict: On success:
              {
                  "product_subcategories": [ ... ]
              }
              On failure:
              {
                  "error": "<reason>",
                  "status": <HTTP status code>
              }
    """
    result = await request_json("GET", f"{BASE_URL}/stores/subcategories/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"product_subcategories": result["data"]}


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
async def get_product_subcategory_by_id(subcategory_id: int) -> dict:
    """
    Retrieve a specific product subcategory by its ID.

    This tool sends a GET request to the Django endpoint
    `/stores/subcategories/{subcategory_id}/` and returns the subcategory data
    as a dictionary.

    Args:
        subcategory_id (int): The ID of the product subcategory to retrieve.

    Returns:
        dict: On success:
              {
                  "product_subcategory": { ...subcategory fields... }
              }
              On failure:
              {
                  "error": "<reason>",
                  "status": <HTTP status code>
              }
    """
    result = await request_json("GET", f"{BASE_URL}/stores/subcategories/{subcategory_id}/")
    if "error" in result:
        if result.get("status") == 404:
            return {"error": "Subcategory not found", "status": 404}
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
async def get_product_subcategories_by_category_id(category_id: int) -> dict:
    """
    Retrieve all product subcategories for a specific category.

    This tool sends a GET request to the Django endpoint
    `/stores/subcategories/category/{category_id}/` and returns the list of
    subcategories that belong to the given category.

    Args:
        category_id (int): The ID of the parent ProductCategory.

    Returns:
        dict: On success:
              {
                  "product_subcategories": [ ...subcategories... ]
              }
              On failure:
              {
                  "error": "<reason>",
                  "status": <HTTP status code>
              }
    """
    result = await request_json("GET", f"{BASE_URL}/stores/subcategories/category/{category_id}/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"product_subcategories": result["data"]}


# === Inventory ===

@app.tool
async def get_inventory_items() -> dict:
    """
    Retrieve all inventory items.

    This tool sends a GET request to the Django endpoint
    `/stores/inventory/` and returns the full list of inventory items
    (current stock and average cost). 

    Note:
        Use this for current balances. For movement history (IN/OUT ledger),
        call `get_inventory_movements()` instead.

    Args:
        None

    Returns:
        dict: On success:
              {
                  "inventory_items": [ ... ]
              }
              On failure:
              {
                  "error": "<reason>",
                  "status": <HTTP status code>
              }
    """
    result = await request_json("GET", f"{BASE_URL}/stores/inventory/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"inventory_items": result["data"]}


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
async def get_inventory_item_by_id(item_id: int) -> dict:
    """Retrieve a specific inventory item by its ID."""
    result = await request_json("GET", f"{BASE_URL}/stores/inventory/{item_id}/")
    if "error" in result:
        if result.get("status") == 404:
            return {"error": "Item not found", "status": 404}
        return {"error": result["error"], "status": result.get("status")}
    return {"inventory_item": result["data"]}


@app.tool
async def update_inventory_item_by_id(item_id: int, data: dict) -> dict:
    """Update a specific inventory item."""
    result = await request_json("PUT", f"{BASE_URL}/stores/inventory/{item_id}/", json=data)
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"inventory_item": result["data"]}


@app.tool
async def delete_inventory_item_by_id(item_id: int) -> dict:
    """Delete a specific inventory item."""
    result = await request_json("DELETE", f"{BASE_URL}/stores/inventory/{item_id}/")
    if "error" in result:
        if result.get("status") == 404:
            return {"error": "Item not found", "status": 404}
        return {"error": result["error"], "status": result.get("status")}
    return {"message": "Item deleted successfully"}


@app.tool
async def inventory_receive(data: dict) -> dict:
    """
    Receive inventory items and update the stock.
    Expects keys: item_id (int), units (int), cost_per_unit (float)
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
    """
    Issue inventory items and update the stock.
    Expects key: item_id (int), units (int)
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
    """Inventory **history** tool.
    Use for movement **ledger / history / transactions / IN / OUT**.
    Calls GET /stores/inventory/movements/ and returns {"inventory_movements":[...]}.
    Do **not** use this for current stock or item listings.
    """
    result = await request_json("GET", f"{BASE_URL}/stores/inventory/movements/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"inventory_movements": result["data"]}


@app.tool
async def filter_inventory_items(
    store_id: int | None = None,
    category_id: int | None = None,
    subcategory_id: int | None = None,
) -> dict:
    """
    Retrieve filtered inventory items by store/category/subcategory.
    """
    params = {}
    if store_id is not None:
        params["store"] = store_id
    if category_id is not None:
        params["category"] = category_id
    if subcategory_id is not None:
        params["sub"] = subcategory_id

    result = await request_json(
        "GET", f"{BASE_URL}/stores/inventory/filter/", params=params
    )
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"filtered_inventory": result["data"]}


async def _shutdown():
    global _shared_session
    if _shared_session and not _shared_session.closed:
        await _shared_session.close()
        logger.info("HTTP session closed.")


if __name__ == "__main__":
    #try:
    #    app.run(transport='sse')
    #finally:
        # best-effort cleanup; if event loop is still running, schedule close
    #    asyncio.run(_shutdown())
    print("Starting MCP SSE server on http://127.0.0.1:9000")
    app.run(transport="sse",host="127.0.0.1", port=9000)