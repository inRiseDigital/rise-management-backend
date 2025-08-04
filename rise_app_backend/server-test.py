import aiohttp
from fastmcp import FastMCP, tool
import os
from dotenv import load_dotenv

load_dotenv()
BASE_URL = os.getenv("BASE_URL")

app = FastMCP("django-mcp-server")

# Fetch users from Django
@tool()
async def get_stores() -> dict:
    """
    Fetch the list of stores from the Django backend API.

    This tool sends a GET request to the Django endpoint
    `/stores/add_stores/` and returns all available store data
    as a dictionary.
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/stores/add_stores/") as resp:
            data = await resp.json()
            return {"users": data}

# Fetch orders from Django
@tool()
async def add_store() -> dict:
    """
    Create a new store entry and return the resulting orders payload.

    This tool makes a POST request to your Django backend to add a store
    (or trigger whatever logic lives at that endpoint) and then returns
    the server’s JSON response under the key "orders".

    Endpoint:
        POST http://127.0.0.1:8000/stores/add_stores/

    Returns:
        dict: {
            "orders": <The JSON-decoded response from the server>
        }

    Raises:
        aiohttp.ClientError: On network or protocol errors.
        asyncio.TimeoutError: If the request takes too long.
    """
       
        
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BASE_URL}/stores/add_stores/") as resp:
            data = await resp.json()
            return {"orders": data}
        
#retreve store by id
@tool()
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
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/stores/add_stores/{store_id}/") as resp:
            if resp.status == 404:
                return {"error": "Store not found"}
            data = await resp.json()
            return {"store": data}
        
#update store by id
@tool() 
async def update_store_by_id(store_id: int, data: dict) -> dict:
    """
    Update a specific store by its ID.

    This tool sends a PUT request to the Django endpoint
    `/stores/stores/{store_id}/` with the provided data
    and returns the updated store data as a dictionary.
    
    Args:
        store_id (int): The ID of the store to update.
        data (dict): The data to update the store with.

    Returns:
        dict: The updated store data.
    """
    async with aiohttp.ClientSession() as session:
        async with session.put(f"{BASE_URL}/stores/add_stores/{store_id}/", json=data) as resp:
            if resp.status == 404:
                return {"error": "Store not found"}    
            data = await resp.json()
            return {"store": data}
        
# Delete store by ID
@tool()
async def delete_store_by_id(store_id: int) -> dict:
    """
    Delete a specific store by its ID.

    This tool sends a DELETE request to the Django endpoint
    `/stores/stores/{store_id}/` and returns a confirmation message.
    
    Args:
        store_id (int): The ID of the store to delete.

    Returns:
        dict: Confirmation message or error if not found.
    """
    async with aiohttp.ClientSession() as session:
        async with session.delete(f"{BASE_URL}/stores/add_stores/{store_id}/") as resp:
            if resp.status == 404:
                return {"error": "Store not found"}
            return {"message": "Store deleted successfully"}
        
#create a new product category
@tool()
async def add_product_category(data: dict) -> dict:
    """
    Create a new product category for a specific store.

    Sends a POST request to the Django endpoint `/stores/categories/`
    with the provided category name and store ID (foreign key), and
    returns the newly created category.

    Args:
        data (dict): Dictionary containing:
            - name (str): The name of the product category.
            - store (int): The ID of the store this category belongs to.

    Returns:
        dict: On success, the created product category, e.g.:
            {
                "id": 9,
                "name": "pumpkin",
                "store": 4
            }
        dict: {"error": "Invalid data"} if the server responds with HTTP 400.
    """
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BASE_URL}/stores/categories/", json=data) as resp:
            if resp.status == 400:
                return {"error": "Invalid data"}
            data = await resp.json()
            return {"product_category": data}
        
#Retrieve all product category 
@tool()
async def get_product_categories() -> dict:
    """
    Retrieve all product categories from the Django backend.

    Sends a GET request to the endpoint `/stores/categories/` and returns
    all available product categories as a dictionary.

    Returns:
        dict: A dictionary containing all product categories.
        e.g.:
        
    {
        "id": 7,
        "name": "rise",
        "store": 4
    },
    {
        "id": 8,
        "name": "pumkin",
        "store": 4
    }
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/stores/categories/") as resp:
            data = await resp.json()
            return {"product_categories": data}
        
# Retrieve a product category by ID
@tool()
async def get_product_category_by_id(category_id: int) -> dict:
    """
    Retrieve a specific product category by its ID.

    Sends a GET request to the Django endpoint `/stores/categories/{category_id}/`
    and returns the product category data as a dictionary.

    Args:
        category_id (int): The ID of the product category to retrieve.

    Returns:
        dict: The product category data.
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/stores/categories/{category_id}/") as resp:
            data = await resp.json()
            return {"product_category": data}
    
    
# Update a product category by ID
@tool()
async def update_product_category_by_id(category_id: int, data: dict) -> dict:
    """
    Update a specific product category by its ID.

    Sends a PUT request to the Django endpoint `/stores/categories/{category_id}/`
    with the provided data and returns the updated product category data as a dictionary.

    Args:
        category_id (int): The ID of the product category to update.
        data (dict): The data to update the product category with.

    Returns:
        dict: The updated product category data.
    """
    async with aiohttp.ClientSession() as session:
        async with session.put(f"{BASE_URL}/stores/categories/{category_id}/", json=data) as resp:
            data = await resp.json()
            return {"product_category": data}
        
        
        
# Delete a product category by ID
@tool()
async def delete_product_category_by_id(category_id: int) -> dict:    
    """    Delete a specific product category by its ID.

    Sends a DELETE request to the Django endpoint `/stores/categories/{category_id}/`
    and returns a confirmation message or an error message if the category is not found.

    Args:
        category_id (int): The ID of the product category to delete.

    Returns:
        dict: The confirmation message or error message.
    """
    async with aiohttp.ClientSession() as session:
        async with session.delete(f"{BASE_URL}/stores/categories/{category_id}/") as resp:
            if resp.status == 404:
                return {"error": "Category not found"}
            return {"message": "Category deleted successfully"}
        
#Retrieve all product subcategory
@tool()
async def get_product_subcategories() -> dict:
    """
    Retrieve all product subcategories from the Django backend.

    Sends a GET request to the endpoint `/stores/subcategories/` and returns
    all available product subcategories as a dictionary.

    Returns:
        dict: A dictionary containing all product subcategories.
        e.g.:
        
    {
        "id": 1,
        "name": "electronics",
        "category": 2
    },
    {
        "id": 2,
        "name": "furniture",
        "category": 3
    }
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/stores/subcategories/") as resp:
            data = await resp.json()
            return {"product_subcategories": data}
        
# Create a new product subcategory
@tool()
async def create_product_subcategory(data: dict) -> dict:
    """
    Create a new product subcategory.

    This tool sends a POST request to the Django endpoint `/stores/subcategories/`
    with the provided data. The request must include:
        - category (int): The ID of the parent category.
        - name (str): The name of the new subcategory.

    If successfully created, the API will return the created subcategory
    in the following format:
        {
            "id": <int>,        # Subcategory ID
            "name": <str>,      # Subcategory name
            "category": <int>   # Parent category ID
        }

    Args:
        data (dict): A dictionary containing the subcategory details.
                     Example: {"name": "qqqqq", "category": 7}

    Returns:
        dict: The created product subcategory data.
    """
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BASE_URL}/stores/subcategories/", json=data) as resp:
            data = await resp.json()
            return {"product_subcategory": data}
        
# Retrieve a product subcategory by ID
@tool()
async def get_product_subcategory_by_id(subcategory_id: int) -> dict:    
    """Retrieve a specific product subcategory by its ID.

    Sends a GET request to the Django endpoint `/stores/subcategories/{subcategory_id}/`
    and returns the product subcategory data as a dictionary.

    Args:
        subcategory_id (int): The ID of the product subcategory to retrieve.

    Returns:
        dict: The product subcategory data.
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/stores/subcategories/{subcategory_id}/") as resp:
            data = await resp.json()
            return {"product_subcategory": data}
        
# Update a product subcategory by ID
@tool()
async def update_product_subcategory_by_id(subcategory_id: int, data: dict) -> dict:
    """
    Update a specific product subcategory by its ID.

    Sends a PUT request to the Django endpoint `/stores/subcategories/{subcategory_id}/`
    with the provided data and returns the updated product subcategory data as a dictionary.

    Args:
        subcategory_id (int): The ID of the product subcategory to update.
        data (dict): The data to update the product subcategory with.

    Returns:
        dict: The updated product subcategory data.
    """
    async with aiohttp.ClientSession() as session:
        async with session.put(f"{BASE_URL}/stores/subcategories/{subcategory_id}/", json=data) as resp:
            data = await resp.json()
            return {"product_subcategory": data}
        
# Delete a product subcategory by ID
@tool()    
async def delete_product_subcategory_by_id(subcategory_id: int) -> dict:
    """
    Delete a specific product subcategory by its ID.

    Sends a DELETE request to the Django endpoint `/stores/subcategories/{subcategory_id}/`
    and returns a confirmation message or an error message if the subcategory is not found.

    Args:
        subcategory_id (int): The ID of the product subcategory to delete.

    Returns:
        dict: The confirmation message or error message.
    """
    async with aiohttp.ClientSession() as session:
        async with session.delete(f"{BASE_URL}/stores/subcategories/{subcategory_id}/") as resp:
            if resp.status == 404:
                return {"error": "Subcategory not found"}
            return {"message": "Subcategory deleted successfully"}
        
# Retrieve product subcategories by category ID
@tool()
async def get_product_subcategories_by_category_id(category_id: int) -> dict:
    """
    Retrieve all product subcategories for a specific category ID.

    Sends a GET request to the Django endpoint `/stores/subcategories/category/{category_id}/`
    and returns the subcategories associated with that category.

    Args:
        category_id (int): The ID of the product category to filter by.

    Returns:
        dict: A dictionary containing all product subcategories for the specified category.
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/stores/subcategories/category/{category_id}/") as resp:
            data = await resp.json()
            return {"product_subcategories": data}
        
#Retrieve all Inventory items
@tool()
async def get_inventory_items() -> dict:
    """
    Retrieve all inventory items from the Django backend.

    Sends a GET request to the endpoint `/stores/inventory/` and returns
    all available inventory items as a dictionary.

    Returns:
        dict: A dictionary containing all inventory items.
        e.g.:
        
    {
        "id": 1,
        "store": 2,
        "category": 3,
        "subcategory": 4,
        "units_in_stock": 100,
        "unit_cost": 10.00,
        "total_cost": 1000.00,
        "updated_at": "2023-10-01T12:00:00Z"
    }
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/stores/inventory/") as resp:
            data = await resp.json()
            return {"inventory_items": data}
        
# Create a new inventory item
@tool()
async def create_inventory_item(data: dict) -> dict:
    """
    Create a new inventory item in the Django backend.

    Sends a POST request to the endpoint `/stores/inventory/` with the provided data
    and returns the created inventory item as a dictionary.

    Returns:
        dict: A dictionary containing the created inventory item.
    """
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BASE_URL}/stores/inventory/", json=data) as resp:
            data = await resp.json()
            return {"inventory_item": data}
        
# Retrieve an inventory item by ID
@tool()
async def get_inventory_item_by_id(item_id: int) -> dict:
    """
    Retrieve a specific inventory item by its ID.

    Sends a GET request to the Django endpoint `/stores/inventory/{item_id}/`
    and returns the inventory item data as a dictionary.

    Args:
        item_id (int): The ID of the inventory item to retrieve.

    Returns:
        dict: The inventory item data.
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/stores/inventory/{item_id}/") as resp:
            data = await resp.json()
            return {"inventory_item": data}
        
# Update an inventory item by ID
@tool()
async def update_inventory_item_by_id(item_id: int, data: dict) -> dict: 
    """
    Update a specific inventory item by its ID.

    Sends a PUT request to the Django endpoint `/stores/inventory/{item_id}/`
    with the provided data and returns the updated inventory item data as a dictionary.

    Args:
        item_id (int): The ID of the inventory item to update.
        data (dict): The data to update the inventory item with.

    Returns:
        dict: The updated inventory item data.
    """
    async with aiohttp.ClientSession() as session:
        async with session.put(f"{BASE_URL}/stores/inventory/{item_id}/", json=data) as resp:
            data = await resp.json()
            return {"inventory_item": data}
        
# Delete an inventory item by ID
@tool()
async def delete_inventory_item_by_id(item_id: int) -> dict:
    """
    Delete a specific inventory item by its ID.

    Sends a DELETE request to the Django endpoint `/stores/inventory/{item_id}/`
    and returns a confirmation message or an error message if the item is not found.

    Args:
        item_id (int): The ID of the inventory item to delete.

    Returns:
        dict: The confirmation message or error message.
    """
    async with aiohttp.ClientSession() as session:
        async with session.delete(f"{BASE_URL}/stores/inventory/{item_id}/") as resp:
            if resp.status == 404:
                return {"error": "Item not found"}
            return {"message": "Item deleted successfully"}
# Inventory receive operation
@tool()
async def inventory_receive(data: dict) -> dict:
    """
    Receive inventory items and update the stock.

    Sends a POST request to the Django endpoint `/stores/inventory/receive/{item_id}/`
    with the provided data to update the inventory item stock.

    Args:
        data (dict): A dictionary containing:
            - item_id (int): The ID of the inventory item.
            - units (int): The number of units to add.
            - cost_per_unit (float): The cost per unit.

    Returns:
        dict: The updated inventory item data.
    """
    item_id = data.pop("item_id")
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BASE_URL}/stores/inventory/receive/{item_id}/", json=data) as resp:
            data = await resp.json()
            return {"inventory_item": data}
        
# Inventory issue operation
@tool()
async def inventory_issue(data: dict) -> dict:
    """
    Issue inventory items and update the stock.

    Sends a POST request to the Django endpoint `/stores/inventory/issue/{item_id}/`
    with the provided data to update the inventory item stock.

    Args:
        data (dict): A dictionary containing:
            - item_id (int): The ID of the inventory item.
            - units (int): The number of units to remove.

    Returns:
        dict: The updated inventory item data.
    """
    item_id = data.pop("item_id")
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BASE_URL}/stores/inventory/issue/{item_id}/", json=data) as resp:
            data = await resp.json()
            return {"inventory_item": data}
   
#InventoryFilterView
@tool()
async def filter_inventory_items(store_id: int = None, category_id: int = None, subcategory_id: int = None) -> dict:
    """
        Retrieve filtered inventory items for a given store.

        This endpoint allows clients to filter inventory items by store, category,
        and optionally by subcategory. The `store` parameter is required, while
        `category` and `sub` are optional.

        Filtering logic:
            - If only `store` is provided → return all inventory items for that store.
            - If `store` + `category` are provided → return all items under that category.
                - If `sub` is also provided → return items matching the specific subcategory.
                - If `sub` is not provided:
                    - If the category has subcategories → return items belonging to any subcategory in that category.
                    - If the category has no subcategories → return items with no subcategory.

        Args:
            request (HttpRequest): The HTTP request object containing query parameters:
                - store (int): Store ID (required)
                - category (int): Category ID (optional)
                - sub (int): Subcategory ID (optional)

        Returns:
            Response: A JSON response containing:
                - store (str): Store name
                - items (list): Serialized inventory items matching the filter criteria

        Example:
            GET /api/inventory/filter?store=1&category=3&sub=5

            Response:
            {
                "store": "Main Store",
                "items": [
                    {
                        "id": 10,
                        "category": 3,
                        "subcategory": 5,
                        "units_in_stock": "100.00",
                        "unit_cost": "12.5000",
                        "updated_at": "2025-07-29T12:00:00Z"
                    },
                    ...
                ]
            }
"""
    async with aiohttp.ClientSession() as session:
        params = {}
        if store_id:
            params['store'] = store_id
        if category_id:
            params['category'] = category_id
        if subcategory_id:
            params['sub'] = subcategory_id

        async with session.get(f"{BASE_URL}/stores/inventory/filter/", params=params) as resp:
            data = await resp.json()
            return {"filtered_inventory": data}
if __name__ == "__main__":
    app.run()
