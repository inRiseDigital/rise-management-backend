import aiohttp
import asyncio
import os
import logging
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from fastmcp.tools import tool
from fastmcp import FastMCP
import requests

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
    """Retrieve all stores list of from the Django backend API.

    This tool sends a GET request to the Django endpoint
    `/stores/add_stores/` and returns all available store data
    as a dictionary.
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
async def add_store() -> dict:
    """Create a new store entry and return the resulting stores payload.

    This tool makes a POST request to your Django backend to add a store
    (or trigger whatever logic lives at that endpoint) and then returns
    the server’s JSON response under the key "store".

    Endpoint:
        POST http://127.0.0.1:8000/stores/add_stores/

    Returns:
        dict: {
            "store": <The JSON-decoded response from the server>
        }

    Raises:
        aiohttp.ClientError: On network or protocol errors.
        asyncio.TimeoutError: If the request takes too long.
    """
    result = await request_json("POST", f"{BASE_URL}/stores/add_stores/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"store": result["data"]}


@app.tool
async def get_store_by_id(store_id: int) -> dict:
    """
    Fetch a specific store by its ID.

    This tool sends a GET request to the Django endpoint
    `/stores/stores/{store_id}/` and returns the store data
    as a dictionary.
    
    Args:
        store_id (int): The ID of the store to retrieve.

    Returns:
        dict: The store data.
    """
    result = await request_json("GET", f"{BASE_URL}/stores/stores/{store_id}/")
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
    `/stores/stores/{store_id}/` and returns the store data
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
    `/stores/stores/{store_id}/` and returns the store data
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
async def add_product_category(data: dict) -> dict:
    """
    Ceare a new product category.

    This tool sends a POST request to the Django endpoint
    `/stores/categories/` and returns the store data
    as a dictionary.
    
    Args:
        store_id (int): The ID of the store to retrieve.

    Returns:
        dict: The category data id, name, and store.
    """
    result = await request_json("POST", f"{BASE_URL}/stores/categories/", json=data)
    if "error" in result:
        if result.get("status") == 400:
            return {"error": "Invalid data", "status": 400}
        return {"error": result["error"], "status": result.get("status")}
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
    """Delete a specific product category by its ID."""
    result = await request_json("DELETE", f"{BASE_URL}/stores/categories/{category_id}/")
    if "error" in result:
        if result.get("status") == 404:
            return {"error": "Category not found", "status": 404}
        return {"error": result["error"], "status": result.get("status")}
    return {"message": "Category deleted successfully"}


# === Product Subcategories ===

@app.tool
async def get_product_subcategories() -> dict:
    """Retrieve all product subcategories."""
    result = await request_json("GET", f"{BASE_URL}/stores/subcategories/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"product_subcategories": result["data"]}


@app.tool
async def create_product_subcategory(data: dict) -> dict:
    """Create a new product subcategory."""
    result = await request_json("POST", f"{BASE_URL}/stores/subcategories/", json=data)
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"product_subcategory": result["data"]}


@app.tool
async def get_product_subcategory_by_id(subcategory_id: int) -> dict:
    """Retrieve a specific product subcategory by its ID."""
    result = await request_json("GET", f"{BASE_URL}/stores/subcategories/{subcategory_id}/")
    if "error" in result:
        if result.get("status") == 404:
            return {"error": "Subcategory not found", "status": 404}
        return {"error": result["error"], "status": result.get("status")}
    return {"product_subcategory": result["data"]}


@app.tool
async def update_product_subcategory_by_id(subcategory_id: int, data: dict) -> dict:
    """Update a specific product subcategory by its ID."""
    result = await request_json("PUT", f"{BASE_URL}/stores/subcategories/{subcategory_id}/", json=data)
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"product_subcategory": result["data"]}


@app.tool
async def delete_product_subcategory_by_id(subcategory_id: int) -> dict:
    """Delete a specific product subcategory by its ID."""
    result = await request_json("DELETE", f"{BASE_URL}/stores/subcategories/{subcategory_id}/")
    if "error" in result:
        if result.get("status") == 404:
            return {"error": "Subcategory not found", "status": 404}
        return {"error": result["error"], "status": result.get("status")}
    return {"message": "Subcategory deleted successfully"}


@app.tool
async def get_product_subcategories_by_category_id(category_id: int) -> dict:
    """Retrieve all product subcategories for a specific category."""
    result = await request_json("GET", f"{BASE_URL}/stores/subcategories/category/{category_id}/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"product_subcategories": result["data"]}


# === Inventory ===

@app.tool
async def get_inventory_items() -> dict:
    """Retrieve all inventory items."""
    result = await request_json("GET", f"{BASE_URL}/stores/inventory/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"inventory_items": result["data"]}


@app.tool
async def create_inventory_item(data: dict) -> dict:
    """Create a new inventory item."""
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
    print("Starting MCP server...")
    app.run(transport="streamable-http",port=9000, path = "/mcp")