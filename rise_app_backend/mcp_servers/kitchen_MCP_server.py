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


# --- Tools: kitchen expense API wrappers ---
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
async def get_all_kitchen_expense_categories() -> dict:
    """
    Retrieve all kitchen expense categories from the backend API.

    This helper calls the backend GET endpoint at:
        {BASE_URL}/kitchen/category/

    It relies on a shared HTTP helper `_get_and_normalize(url)` which should:
      - Perform the HTTP GET (async),
      - Return {"data": <json>} on successful 2xx responses,
      - Or return {"error": <payload>, "status": <int>} on non-2xx or network errors.

    Returns:
        dict: Normalized response from `_get_and_normalize`.
          - Success example:
              {"data": [
                  {"id": 1, "name": "Food", "description": "...", "updated_at": "..."},
                  ...
              ], "status": 200}
          - Error example:
              {"error": {"name": ["This field is required."]}, "status": 400}

    Notes:
        - `BASE_URL` must be set in the environment and reachable.
        - The tool should not raise; instead return error objects so the calling agent can
          surface them to users.
    """
    url = f"{BASE_URL}/kitchen/category/"
    return await _get_and_normalize(url)


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


@app.tool()
async def delete_kitchen_expense_category(category_id: int) -> dict:
    """
    Delete a kitchen expense category by ID.

    HTTP endpoint called:
        DELETE {BASE_URL}/kitchen/category/{category_id}/

    Args:
        category_id (int): ID of the category to delete.

    Returns:
        dict: Normalized result from `_delete_and_normalize`.
            - On success (204 or 2xx with empty body): {"data": "Category deleted successfully", "status": 204}
            - If not found: {"error": {"detail": "Not found."}, "status": 404}
            - For validation/network errors: {"error": <payload_or_string>, "status": <int|null>}

    Notes:
        * This tool calls a helper `_delete_and_normalize(url)` which should:
            - perform an async DELETE to `url`
            - return `{"data": <parsed-json-or-message>, "status": status_code}` for success (2xx)
            - return `{"error": <payload-or-text>, "status": status_code}` for non-2xx or network errors
        * Treat 204/no-body as success and return a simple success message (don't treat as error).
    """
    url = f"{BASE_URL}/kitchen/category/{category_id}/"
    return await _delete_and_normalize(url)


@app.tool()
async def create_kitchen_expense(category_id: int, amount: float, date: str,
                                responsible_person: str, description: str = "",
                                bill_no: str = "", image: str = "") -> dict:
    
    """
    Create a kitchen expense entry by calling the backend POST /kitchen/expense/.

    Args:
        category_id (int):
            Primary key of the kitchen expense category (must exist).
        amount (float):
            Expense amount. Should be numeric (e.g., 1250.00).
        date (str):
            Date of expense in ISO format "YYYY-MM-DD" (e.g., "2025-07-20").
        responsible_person (str):
            Person responsible for the expense (name).
        description (str, optional):
            Optional free-text description of the expense.
        bill_no (str, optional):
            Bill number or reference string.
        image (str, optional):
            A string representing the image. NOTE: The backend `Expense.image`
            field is an ImageField and typically expects multipart/form-data file
            upload. If the MCP tool cannot perform multipart uploads, pass an
            accessible image URL or base64 string only if the backend accepts it.
            Otherwise, omit `image` and upload through the backend UI or extend
            this tool to support multipart/form-data.

    Behavior:
        - Calls helper `_post_and_normalize(url, data, success_status=201)` which:
            * performs an async HTTP POST to `{BASE_URL}/kitchen/expense/`
            * returns a normalized dict: on success {"data": <resource>, "status": 201}
              or on failure {"error": <payload_or_text>, "status": <int|null>}.

    Returns:
        dict:
            - Success: {"data": <created_expense_object>, "status": 201}
            - Validation error: {"error": {"field": ["error message", ...], ...}, "status": 400}
            - Not found or other HTTP error: {"error": <payload_or_text>, "status": <int>}
            - Network/timeout: {"error": "Request timed out" or str(e), "status": None}

    Notes & validation:
        - Do not provide extra fields that the backend does not accept.
        - Date must be exactly "YYYY-MM-DD" — the server validates this.
        - Backend will store `amount` as Decimal, so pass as float or numeric string.
        - If image upload fails due to format, the backend will return a validation error.

    Example payload:
        {
          "category": 3,
          "amount": 1250.00,
          "date": "2025-07-20",
          "responsible_person": "John Doe",
          "description": "Vegetables for kitchen",
          "bill_no": "BILL-20250720-001",
          "image": "https://example.com/receipts/2025-07-20-001.jpg"
        }

    Example success return:
        {"data": {
            "id": 101,
            "category": 3,
            "amount": "1250.00",
            "date": "2025-07-20",
            "responsible_person": "John Doe",
            "description": "Vegetables for kitchen",
            "bill_no": "BILL-20250720-001",
            "image": "/media/images/kitchen/bills/2025/07/receipt.jpg",
            "created_at": "2025-07-20T10:12:34.123456Z",
            "updated_at": "2025-07-20T10:12:34.123456Z"
          }, "status": 201}
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
    return await _post_and_normalize(url, data, success_status=201)


@app.tool()
async def get_all_kitchen_expenses() -> dict:
    """
    Retrieve all kitchen expense records from the backend.

    Calls:
        GET {BASE_URL}/kitchen/expense/

    Returns:
        On success:
            {"data": [<expense objects>], "status": 200}

        On HTTP error:
            {"error": <payload_or_text>, "status": <http_status_code>}

        On network/timeout:
            {"error": "Request timed out" | str(exception), "status": None}

    Behavior / Notes:
      - Uses helper `_get_and_normalize(url)` to perform the HTTP GET and convert
        success responses to {"data": <payload>} and failures to {"error": ..., "status": ...}.
      - The returned "data" is expected to be a JSON array of serialized Expense objects,
        as produced by the DRF view/serializer on the backend.
      - If the backend supports pagination, `_get_and_normalize` should surface the
        paginated payload as returned (e.g., {"results": [...], "count": N}) — be aware
        and handle that in the caller if needed.
      - Caller should treat HTTP 2xx as success and any non-2xx as an error.
    """
    url = f"{BASE_URL}/kitchen/expense/"
    return await _get_and_normalize(url)


@app.tool()
async def get_kitchen_expense_details_by_id(expense_id: int) -> dict:
    """
    Retrieve a single kitchen expense record by its ID.

    Calls:
        GET {BASE_URL}/kitchen/expense/{expense_id}/

    Args:
        expense_id (int): Primary key of the expense to retrieve.

    Returns:
        On success (HTTP 200):
            {"data": <expense_object>}  # expense_object is deserialized JSON from backend

        If not found (HTTP 404):
            {"error": <backend_payload_or_message>, "status": 404}

        On other HTTP or network errors:
            {"error": <payload_or_text>, "status": <http_status_or_None>}

    Behavior / Notes:
      - Uses helper `_get_and_normalize(url)` which should:
          * perform the GET request (aiohttp/httpx/etc.),
          * parse JSON on success and return {"data": payload},
          * return {"error": payload, "status": status} for non-2xx,
          * return {"error": "Request timed out", "status": None} on timeouts.
      - Caller should treat 200 as success and return the `data` for presentation.
      - If backend returns additional metadata (e.g. relations), that will be passed through.
    """
    url = f"{BASE_URL}/kitchen/expense/{expense_id}/"
    return await _get_and_normalize(url)


@app.tool()
async def update_kitchen_expense(expense_id: int, category_id: int, amount: float, date: str,
                                 responsible_person: str, description: str = "", bill_no: str = "", image: str = "") -> dict:
    """
    Update an existing kitchen expense.

    Calls:
        PUT {BASE_URL}/kitchen/expense/{expense_id}/

    Args:
        expense_id (int): ID of the expense to update.
        category_id (int): ID of the category (required).
        amount (float): Expense amount (required).
        date (str): Date in ISO format "YYYY-MM-DD" (required).
        responsible_person (str): Person responsible (required).
        description (str): Optional text description.
        bill_no (str): Optional bill number.
        image (str): Optional image path or URL (backend-dependent).

    Returns:
        On success: {"data": <updated_object>, "status": 200}
        On validation error: {"error": <validation_payload>, "status": 400}
        If not found: {"error": <payload>, "status": 404}
        On network/other errors: {"error": <message>, "status": <int|None>}

    Notes:
      - This tool uses helper `_put_and_normalize(url, data)` which should:
        * send the PUT request,
        * parse JSON on success and return {"data": payload},
        * return {"error": payload, "status": status} for non-2xx responses,
        * return {"error": "Request timed out", "status": None} for timeouts.
      - If your backend expects multipart for `image`, this tool must be adapted to send multipart.
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
    return await _put_and_normalize(url, data)


@app.tool()
async def delete_kitchen_expense(expense_id: int) -> dict:
    """
    Delete a kitchen expense by ID.

    Calls:
        DELETE {BASE_URL}/kitchen/expense/{expense_id}/

    Args:
        expense_id (int): Primary key of the expense to delete.

    Returns:
        On success (204 or empty body): {"data": "Expense deleted", "status": 204}
        If not found: {"error": "Not found", "status": 404}
        On validation / server error: {"error": <payload_or_message>, "status": <int>}
        On network/timeouts: {"error": <message>, "status": None}

    Notes:
      * Treat HTTP 204 / empty body as success.
      * The tool should not invent other details — return backend payload (or a short success message).
      * If deletion is irreversible or dangerous, consider requiring confirmation from user before calling.
    """
    url = f"{BASE_URL}/kitchen/expense/{expense_id}/"
    return await _delete_and_normalize(url)


@app.tool()
async def get_expenses_by_category(category_id: int) -> dict:
    """
    Retrieve all kitchen expenses for a given category.

    Calls:
        GET {BASE_URL}/kitchen/category/expenses/{category_id}/

    Args:
        category_id (int): Primary key of the category.

    Returns:
        On success:
            {
              "data": {
                "category_id": int,
                "category_name": str,
                "category_description": str,
                "total_amount": float,         # summed amount, two-decimal precision
                "expense_count": int,
                "expenses": [ ... ]           # list of expense objects (serialized)
              },
              "status": 200
            }
        On not found:
            {"error": "Category not found", "status": 404}
        On other failure:
            {"error": <payload_or_message>, "status": <int|null>}

    Notes:
      - The tool returns decimal amounts as floats rounded to 2 decimals for client convenience.
      - Do not invent data: return the backend payload or normalized message.
    """
    url = f"{BASE_URL}/kitchen/category/expenses/{category_id}/"
    return await _get_and_normalize(url)


@app.tool()
async def generate_kitchen_report(start_date: str, end_date: str) -> dict:
    url = f"{BASE_URL}/kitchen/report/?start_date={start_date}&end_date={end_date}"
    return await _get_and_normalize(url)


@app.tool()
async def get_all_milk_entries() -> dict:
    """
    Fetch all milk collection entries from the Django backend, including all fields.

    Sends a GET request to ``{BASE_URL}/cattle_hut/milk/`` (the list endpoint
    registered as ``path('milk/', MilkCollectionListCreateView.as_view(), name='milk_list_create')``)
    and returns the payload in a normalized structure.

    Returns:
        dict: One of the following shapes:

            - Success:
              ``{"stores": [<entry>, ...]}``, where each ``<entry>`` is a serialized
              ``MilkCollection`` with **all** fields:

              .. code-block:: json

                 {
                   "id": 1,
                   "date": "2025-08-20",
                   "local_sale_kg": 0.0,
                   "rise_kitchen_kg": 0.0,
                   "total_kg": 0.0,
                   "total_liters": 0.0,
                   "day_rate": 160.0,
                   "day_total_income": 0.0
                 }

              Notes on fields:
                - ``date`` (YYYY-MM-DD)
                - ``local_sale_kg`` (float)
                - ``rise_kitchen_kg`` (float)
                - ``total_kg`` (float; computed in model ``save()``)
                - ``total_liters`` (float; computed as ``total_kg * 1.027``)
                - ``day_rate`` (float; default 160.0)
                - ``day_total_income`` (float; computed as ``total_kg * day_rate``)

            - Error:
              ``{"error": <str>, "status": <int | None>}`` when the HTTP call fails
              or the backend signals an error.

    Behavior:
        * Read-only and idempotent.
        * Assumes authentication/headers/retries are managed by ``request_json``.
        * This calls the **list** endpoint (``/cattle_hut/milk/``) and not a detail
          endpoint like ``/cattle_hut/milk/<id>/``.

    Example:
        >>> await get_all_milk_entries()
        {"stores": [
            {
              "id": 42,
              "date": "2025-08-20",
              "local_sale_kg": 12.5,
              "rise_kitchen_kg": 2.0,
              "total_kg": 14.5,
              "total_liters": 14.5 * 1.027,
              "day_rate": 160.0,
              "day_total_income": 14.5 * 160.0
            }
        ]}
    """
    result = await request_json("GET", f"{BASE_URL}/cattle_hut/milk/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"stores": result["data"]}

@app.tool()
async def get_all_milk_entrys_in_time_period(start_date: str, end_date: str) -> dict:
    """
    Fetch milk collection entries within a specific date range from the Django backend.

    Issues a GET request to:
        ``{BASE_URL}/cattle_hut/milk/?start_date=<YYYY-MM-DD>&end_date=<YYYY-MM-DD>``

    Args:
        start_date (str): Inclusive start of the range in ISO format ``YYYY-MM-DD``.
        end_date   (str): Inclusive end of the range in ISO format ``YYYY-MM-DD``.

    Returns:
        dict: One of the following shapes:

            - Success:
              ``{"stores": [<entry>, ...]}``, where each entry is a serialized
              ``MilkCollection`` with all fields (schema determined by the backend
              serializer, typically):
                - ``id`` (int)
                - ``date`` (str, YYYY-MM-DD)
                - ``local_sale_kg`` (float)
                - ``rise_kitchen_kg`` (float)
                - ``total_kg`` (float, computed = local_sale_kg + rise_kitchen_kg)
                - ``total_liters`` (float, computed = total_kg * 1.027)
                - ``day_rate`` (float)
                - ``day_total_income`` (float, computed = total_kg * day_rate)

            - Error:
              ``{"error": <str>, "status": <int | None>}`` when the HTTP request fails
              or the backend responds with an error (e.g., 400 on invalid dates).

    Notes:
        - The date range is **inclusive** on both ends (Django ``date__range``).
        - This tool is read-only and idempotent; authentication/retries are handled by
          ``request_json``.
        - Endpoint is the list view registered as:
          ``path('milk/', MilkCollectionListCreateView.as_view(), name='milk_list_create')``.

    Examples:
        >>> await get_all_milk_entrys_in_time_period("2025-08-01", "2025-08-31")
        {"stores": [
            {
              "id": 42,
              "date": "2025-08-20",
              "local_sale_kg": 12.5,
              "rise_kitchen_kg": 2.0,
              "total_kg": 14.5,
              "total_liters": 14.8865,
              "day_rate": 160.0,
              "day_total_income": 2320.0
            },
            ...
        ]}

        >>> await get_all_milk_entrys_in_time_period("bad", "date")
        {"error": "Invalid date format. Use YYYY-MM-DD.", "status": 400}
    """
    result = await request_json("GET", f"{BASE_URL}/cattle_hut/milk/?start_date={start_date}&end_date={end_date}")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"stores": result["data"]}

@app.tool()
async def create_milk_entry(data: dict) -> dict:
    """
    POST /cattle_hut/milk/ -> normalized response:
      {"ok": True, "milk_entry": {...}} on success
      {"ok": False, "status": <int>, "error": <str>, "detail": <any>} on failure
    """
    url = f"{BASE_URL}/cattle_hut/milk/"
    headers = {"Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            resp = await client.post(url, json=data, headers=headers)
        except httpx.RequestError as exc:
            return {"ok": False, "status": 0, "error": f"request error: {exc}"}

    # try parse JSON body (if any)
    try:
        body = resp.json()
    except ValueError:
        body = resp.text

    # success status
    if resp.status_code in (200, 201):
        # try common shapes: {"ok":..}, {"milk_entry":..}, {"data": ..}, serializer data directly
        if isinstance(body, dict):
            if "milk_entry" in body:
                entry = body["milk_entry"]
            elif "data" in body and isinstance(body["data"], dict):
                # data may wrap the object; try to find the entry
                candidate = body["data"]
                # e.g. candidate may be the serialized entry or contain it
                entry = candidate.get("milk_entry") or candidate
            else:
                entry = body
        else:
            # non-json success
            return {"ok": True, "milk_entry": None, "raw": body}

        return {"ok": True, "milk_entry": entry}

    # non-success status: return parsed error if possible
    return {"ok": False, "status": resp.status_code, "error": getattr(body, "get", lambda k: body)("detail", str(body)), "detail": body}

@app.tool()
async def get_milk_entry_by_id(id: int) -> dict:

    """
    Retrieve a single milk collection entry by its identifier.

    Issues a GET request to:
        ``{BASE_URL}/cattle_hut/milk/<id>/``

    Args:
        id (int): Primary key of the milk collection entry to fetch.

    Returns:
        dict: One of the following shapes:

            - Success:
              ``{"milk_entry": <entry>}``
              where ``<entry>`` is the serialized object including all fields, typically:
              ``id``, ``date``, ``local_sale_kg``, ``rise_kitchen_kg``,
              ``total_kg``, ``total_liters``, ``day_rate``, ``day_total_income``.

            - Error:
              ``{"error": <str>, "status": <int | None>}``
              when the HTTP call fails or the backend returns a non-2xx status
              (e.g., ``404`` if the entry does not exist).

    Notes:
        - Read-only and idempotent.
        - Authentication, headers, and retries are handled by ``request_json``.
        - This calls the **detail** endpoint (``/cattle_hut/milk/<id>/``), not the list endpoint.

    Example:
        >>> await get_milk_entry_by_id(42)
        {
          "milk_entry": {
            "id": 42,
            "date": "2025-08-20",
            "local_sale_kg": 12.5,
            "rise_kitchen_kg": 2.0,
            "total_kg": 14.5,
            "total_liters": 14.8915,
            "day_rate": 160.0,
            "day_total_income": 2320.0
          }
        }
    """
    result = await request_json("GET", f"{BASE_URL}/cattle_hut/milk/{id}/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"milk_entry": result["data"]}

@app.tool()
async def update_milk_entry(id: int, date: str, local_sale_kg: float, rise_kitchen_kg: float, day_rate: float) -> dict:
    data = {
        "id": id,
        "date": date,
        "local_sale_kg": local_sale_kg,
        "rise_kitchen_kg": rise_kitchen_kg,
        "day_rate": day_rate,
    }
    """
    Update an existing milk collection entry by its identifier.

    Sends a PUT request to:
        ``{BASE_URL}/cattle_hut/milk/<id>/``

    Args:
        id (int): Primary key of the entry to update.
        data (dict): JSON-serializable payload for a **full** update. Provide all
            writable fields (use PATCH server-side for partial updates if supported).

            Expected keys:
                - ``date`` (str, required): ``YYYY-MM-DD``.
                - ``local_sale_kg`` (float, required)
                - ``rise_kitchen_kg`` (float, required)
                - ``day_rate`` (float, required)

            Notes:
                The backend model recomputes and persists:
                  - ``total_kg = local_sale_kg + rise_kitchen_kg``
                  - ``total_liters = total_kg * 1.027``
                  - ``day_total_income = total_kg * day_rate``
                Values for these computed fields in ``data`` (if any) may be ignored.

    Returns:
        dict:
            - Success:
              ``{"milk_entry": <entry>}`` where ``<entry>`` includes all fields:
              ``id``, ``date``, ``local_sale_kg``, ``rise_kitchen_kg``,
              ``total_kg``, ``total_liters``, ``day_rate``, ``day_total_income``.
            - Error:
              ``{"error": <str>, "status": <int | None>}`` when the HTTP call fails
              or the backend returns a non-2xx status (e.g., 400 validation error, 404 not found).

    Example:
        >>> await update_milk_entry(42, {
        ...   "date": "2025-08-22",
        ...   "local_sale_kg": 10.0,
        ...   "rise_kitchen_kg": 3.0,
        ...   "day_rate": 160.0
        ... })
        {
          "milk_entry": {
            "id": 42,
            "date": "2025-08-22",
            "local_sale_kg": 10.0,
            "rise_kitchen_kg": 3.0,
            "total_kg": 13.0,
            "total_liters": 13.351,
            "day_rate": 160.0,
            "day_total_income": 2080.0
          }
        }
    """
    result = await request_json("PUT", f"{BASE_URL}/cattle_hut/milk/{id}/", json=data)
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"milk_entry": result["data"]}

@app.tool() # tool is work correctly but bot output is wrong
async def delete_milk_entry(id: int) -> dict:
    """Delete a milk collection entry by its database ID.

    Sends a DELETE request to the backend endpoint
    ``{BASE_URL}/cattle_hut/milk/{id}/``. On success, returns a normalized
    confirmation message. If the backend returns an error payload, this function
    surfaces it along with the HTTP status code (when available).

    Args:
        id: Primary key of the ``MilkCollection`` row to delete.

    Returns:
        dict: On success: ``{"message": "Milk entry deleted successfully"}``.
              On failure: ``{"error": <str>, "status": <int | None>}``.

    Raises:
        Any exception raised by ``request_json`` (e.g., network errors) will
        propagate to the caller.

    Example:
        >>> await delete_milk_entry(123)
        {'message': 'Milk entry deleted successfully'}
    """
    result = await request_json("DELETE", f"{BASE_URL}/cattle_hut/milk/{id}/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"message": "Milk entry deleted successfully"}

@app.tool()
async def get_all_cost_entries() -> dict:

    """Fetch all cost entries from the backend service.

    Issues a GET request to ``{BASE_URL}/cattle_hut/costs/`` and returns a
    normalized payload. Errors from the backend are surfaced with the HTTP
    status code when available.

    Returns:
        dict: On success: ``{"costs": <list>}`` where each item is a cost entry.
              On failure: ``{"error": <str>, "status": <int | None>}``.

    Raises:
        Any exception raised by ``request_json`` (e.g., network errors) will
        propagate to the caller.

    Example:
        >>> await get_all_cost_entries()
        {'costs': [{'id': 1, 'amount': 2500.0, ...}, ...]}
    """
    result = await request_json("GET", f"{BASE_URL}/cattle_hut/costs/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"costs": result["data"]}

@app.tool()
async def create_cost_entry(data: dict) -> dict:
    """Create a new cost entry via the backend API.

    Issues a POST to ``{BASE_URL}/cattle_hut/costs/`` with a JSON payload,
    returning the created object on success. Backend validation errors are
    surfaced with the HTTP status code when available.

    Args:
        data: The cost entry payload. Expected keys include:
            - ``cost_date`` (str, ISO date "YYYY-MM-DD")
            - ``description`` (str)
            - ``amount`` (float)

    Returns:
        dict: On success: ``{"cost_entry": <dict>}`` (the created resource).
              On failure: ``{"error": <str>, "status": <int | None>}``.

    Raises:
        Any exception raised by ``request_json`` (e.g., network errors) will
        propagate to the caller.

    Example:
        >>> payload = {
        ...   "cost_date": "2025-08-31",
        ...   "description": "Veterinary supplies",
        ...   "amount": 1500.0
        ... }
        >>> await create_cost_entry(payload)
        {'cost_entry': {'id': 42, 'cost_date': '2025-08-31', 'description': 'Veterinary supplies', 'amount': 1500.0}}
    """
    result = await request_json("POST", f"{BASE_URL}/cattle_hut/costs/", json=data)
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"cost_entry": result["data"]}

@app.tool()
async def get_cost_entry_by_id(id: int) -> dict:
    """Fetch a single cost entry by its ID.

    Sends a GET request to ``{BASE_URL}/cattle_hut/costs/{id}/`` and returns a
    normalized payload. Backend errors are surfaced with the HTTP status code
    when available.

    Args:
        id: Primary key of the cost entry to retrieve.

    Returns:
        dict: On success: ``{"cost_entry": <dict>}``.
              On failure: ``{"error": <str>, "status": <int | None>}``.

    Raises:
        Any exception raised by ``request_json`` (e.g., network errors) will
        propagate to the caller.

    Example:
        >>> await get_cost_entry_by_id(7)
        {'cost_entry': {'id': 7, 'cost_date': '2025-08-31', 'description': 'Feed', 'amount': 950.0}}
    """
    result = await request_json("GET", f"{BASE_URL}/cattle_hut/costs/{id}/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"cost_entry": result["data"]}

@app.tool()
async def update_cost_entry(id: int, data: dict) -> dict:
    """Update an existing cost entry by ID via the backend API.

    Issues a PUT to ``{BASE_URL}/cattle_hut/costs/{id}/`` with a JSON payload,
    returning the updated object on success. Backend validation errors are
    surfaced with the HTTP status code when available.

    Args:
        id: Primary key of the cost entry to update.
        data: Full replacement payload for the entry, e.g.:
            - ``cost_date`` (str, ISO date "YYYY-MM-DD")
            - ``description`` (str)
            - ``amount`` (float)

    Returns:
        dict: On success: ``{"cost_entry": <dict>}`` (the updated resource).
              On failure: ``{"error": <str>, "status": <int | None>}``.

    Raises:
        Any exception raised by ``request_json`` (e.g., network errors) will
        propagate to the caller.

    Example:
        >>> payload = {
        ...   "cost_date": "2025-09-01",
        ...   "description": "Fence repair",
        ...   "amount": 3200.0
        ... }
        >>> await update_cost_entry(7, payload)
        {'cost_entry': {'id': 7, 'cost_date': '2025-09-01', 'description': 'Fence repair', 'amount': 3200.0}}
    """
    result = await request_json("PUT", f"{BASE_URL}/cattle_hut/costs/{id}/", json=data)
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"cost_entry": result["data"]}

@app.tool()
async def delete_cost_entry(id: int) -> dict:
    """Delete a cost entry by its ID via the backend API.

    Sends a DELETE request to ``{BASE_URL}/cattle_hut/costs/{id}/``.
    On success, returns a confirmation message. If the backend responds
    with an error, this function surfaces it along with the HTTP status
    (when available).

    Args:
        id: Primary key of the cost entry to delete.

    Returns:
        dict: On success: ``{"message": "Cost entry deleted successfully"}``.
              On failure: ``{"error": <str>, "status": <int | None>}``.

    Raises:
        Any exception raised by ``request_json`` (e.g., network issues) will
        propagate to the caller.

    Example:
        >>> await delete_cost_entry(17)
        {'message': 'Cost entry deleted successfully'}
    """
    result = await request_json("DELETE", f"{BASE_URL}/cattle_hut/costs/{id}/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"message": "Cost entry deleted successfully"}

@app.tool()
async def export_milk_collection_pdf(start_date: str, end_date: str) -> dict:
    """Download the Milk Collection PDF report for a date range.

    Sends a GET request to the backend export endpoint with the provided
    ``start_date`` and ``end_date`` (``YYYY-MM-DD``). On success, saves the
    returned PDF to the current working directory and returns the filename and
    local file path.

    Args:
        start_date: Inclusive start date in ``YYYY-MM-DD`` format.
        end_date: Inclusive end date in ``YYYY-MM-DD`` format.

    Returns:
        dict: One of
            - Success:
              ``{"filename": <str>, "file_path": <str>, "message": <str>}``
            - Failure:
              ``{"error": <str>}`` (includes HTTP status if non-200)

    Example:
        >>> await export_milk_collection_pdf("2025-08-01", "2025-08-31")
        {
          "filename": "milk_report_2025-08-01_2025-08-31.pdf",
          "file_path": "./milk_report_2025-08-01_2025-08-31.pdf",
          "message": "Milk report PDF successfully downloaded as milk_report_2025-08-01_2025-08-31.pdf"
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

@app.tool() # not work correctly
async def get_latest_milk_collection() -> dict:
    """Fetch the most recent milk collection entry.

    Sends a GET request to ``{BASE_URL}/cattle_hut/milk_collection/latest/`` and normalizes the
    response. If the backend returns 404, a friendlier error message is
    provided.

    Returns:
        dict:
            - Success: ``{"latest_milk_collection": <dict>}``.
            - Not found: ``{"error": "No milk collection entry found", "status": 404}``.
            - Other error: ``{"error": <str>, "status": <int | None>}``.

    Raises:
        Any exception raised by ``request_json`` (e.g., network errors) will
        propagate to the caller.

    Example:
        >>> await get_latest_milk_collection()
        {'latest_milk_collection': {
            'id': 101,
            'date': '2025-09-01',
            'local_sale_kg': 22.5,
            'rise_kitchen_kg': 8.0,
            'total_kg': 30.5,
            'total_liters': 31.33,
            'day_rate': 160.0,
            'day_total_income': 4880.0
        }}
    """
    result = await request_json("GET", f"{BASE_URL}/cattle_hut/milk_collection/latest/")
    if "error" in result:
        if result.get("status") == 404:
            return {"error": "No milk collection entry found", "status": 404}
        return {"error": result["error"], "status": result.get("status")}
    return {"latest_milk_collection": result["data"]}

@app.tool()
async def get_month_to_date_income(date: str = None) -> dict:
    """Fetch month-to-date milk collection income (and totals).

    Calls ``{BASE_URL}/milk/month_to_date_income/``. Optionally accepts a
    reference ``date`` (``YYYY-MM-DD``); if omitted, the backend uses today.
    The backend computes aggregates from the first day of the reference month
    up to (and including) the reference date.

    Args:
        date: Optional ISO date string (``YYYY-MM-DD``) to override "today".

    Returns:
        dict:
            - Success: ``{"month_to_date_income": { "reference_date": <str>,
                                                    "period_start": <str>,
                                                    "period_end": <str>,
                                                    "total_income": <float>,
                                                    "total_kg": <float>,
                                                    "total_liters": <float> }}``
            - Failure: ``{"error": <str>, "status": <int | None>}``.

    Raises:
        Any exception raised by ``request_json`` (e.g., network errors) will
        propagate to the caller.

    Example:
        >>> await get_month_to_date_income()
        {'month_to_date_income': {'reference_date': '2025-09-02',
                                  'period_start': '2025-09-01',
                                  'period_end': '2025-09-02',
                                  'total_income': 6480.0,
                                  'total_kg': 40.5,
                                  'total_liters': 41.55}}

        >>> await get_month_to_date_income("2025-08-15")
        {'month_to_date_income': {...}}
    """
    url = f"{BASE_URL}/milk/month_to_date_income/"
    params = {}
    if date:
        params["date"] = date

    result = await request_json("GET", url, params=params)
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"month_to_date_income": result["data"]}

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
    Simple wrapper for GET {BASE_URL}/stores/by_name/?name=<name>

    Returns:
      {"store": <object>} on 200,
      {"error": "name required", "status": 400} if input is empty,
      {"error": "Store not found", "status": 404} if backend returns 404,
      {"error": <text>, "status": <int>} for other failures.
    """
    # mirror the APIView behavior: require non-empty name
    if not name or str(name).strip() == "":
        return {"error": "name query param required", "status": 400}

    url = f"{BASE_URL}/stores/by_name/"
    params = {"name": name}

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            resp = await client.get(url, params=params)
        except httpx.RequestError as exc:
            return {"error": f"request failed: {exc}", "status": 0}

    if resp.status_code == 200:
        try:
            return {"store": resp.json()}
        except ValueError:
            return {"error": "invalid JSON response", "status": resp.status_code}

    if resp.status_code == 404:
        return {"error": "Store not found", "status": 404}

    # fallback: return server response text for debugging
    return {"error": resp.text, "status": resp.status_code}

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
    
    """Fetch a single inventory item by its ID.

    Sends a GET request to ``{BASE_URL}/stores/inventory/{item_id}/`` and
    returns a normalized payload. If the backend returns 404, a friendly
    "Item not found" message is included.

    Args:
        item_id: Primary key of the inventory item to retrieve.

    Returns:
        dict:
            - Success: ``{"inventory_item": <dict>}``.
            - Not found: ``{"error": "Item not found", "status": 404}``.
            - Other error: ``{"error": <str>, "status": <int | None>}``.

    Raises:
        Any exception raised by ``request_json`` (e.g., network errors) will
        propagate to the caller.

    Example:
        >>> await get_inventory_item_by_id(12)
        {'inventory_item': {'id': 12, 'name': 'Mineral Mix', 'sku': 'MM-001', ...}}
    """
    result = await request_json("GET", f"{BASE_URL}/stores/inventory/{item_id}/")
    if "error" in result:
        if result.get("status") == 404:
            return {"error": "Item not found", "status": 404}
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


@app.tool
async def filter_inventory_items(
    store_id: int | None = None,
    category_id: int | None = None,
    subcategory_id: int | None = None,
) -> dict:

    """Retrieve inventory items filtered by store, category, and subcategory.

    Sends a GET request to ``{BASE_URL}/stores/inventory/filter/`` with query
    parameters mapped as:
      - ``store``     ← ``store_id`` (required by backend)
      - ``category``  ← ``category_id`` (optional)
      - ``sub``       ← ``subcategory_id`` (optional)

    Although the function parameters are optional, the backend **requires**
    ``store`` and will return ``400 {"error": "store param required"}`` if it is
    missing.

    Args:
        store_id: Store primary key. **Required by backend.**
        category_id: Product category primary key (optional).
        subcategory_id: Product subcategory primary key (optional).

    Returns:
        dict:
            - Success:
              ``{"filtered_inventory": {"store": <str>, "items": <list>}}``,
              where ``items`` is a list of serialized ``InventoryItem`` objects.
            - Failure:
              ``{"error": <str|dict>, "status": <int|None>}``.

    Raises:
        Any exception raised by ``request_json`` (e.g., network errors) will
        propagate to the caller.

    Examples:
        >>> await filter_inventory_items(store_id=3)
        {'filtered_inventory': {'store': 'Main Barn', 'items': [...]}}

        >>> await filter_inventory_items(store_id=3, category_id=10)
        {'filtered_inventory': {'store': 'Main Barn', 'items': [...]}}

        >>> await filter_inventory_items(store_id=3, category_id=10, subcategory_id=2)
        {'filtered_inventory': {'store': 'Main Barn', 'items': [...]}}

        >>> await filter_inventory_items()  # missing store_id
        {'error': {'error': 'store param required'}, 'status': 400}
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
async def get_subcategories() -> dict:
    """Retrieve all subcategories from the Django backend API.

    This tool sends a GET request to the Django endpoint
    `/housekeeping/sub/` and returns all available subcategories
    as a dictionary.
    """
    result = await request_json("GET", f"{BASE_URL}/housekeeping/sub/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"subcategories": result["data"]}


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

@app.tool()
async def create_new_tasks(subcategory: int, location: int, cleaning_type: str, ) -> dict:
    """Create a new task for a specific location and subcategory.

    This tool sends a POST request to the Django endpoint
    `/housekeeping/daily_task/` with the provided task details.
    Returns the created task details as a dictionary.
    """
    data = {
        "subcategory": subcategory,
        "location": location,
        "cleaning_type": cleaning_type
        
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


if __name__ == "__main__":
    if not BASE_URL:
        logger.error("BASE_URL not set. Please set BASE_URL in .env or environment.")
        # don't raise on import; print message and still run (tools will error until BASE_URL set)
    logger.info("Starting MCP SSE server on http://127.0.0.1:9000 (SSE transport)")
    try:
        app.run(transport="sse", host="127.0.0.1", port=9000)
    finally:
        # when app.run returns (server stops), close session
        asyncio.run(_shutdown())
