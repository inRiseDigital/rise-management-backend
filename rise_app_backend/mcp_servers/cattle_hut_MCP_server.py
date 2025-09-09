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
import httpx

load_dotenv()
BASE_URL = os.getenv("BASE_URL")
API_TOKEN = os.getenv("API_TOKEN")  # optional: e.g., Bearer token or similar

TIMEOUT = 10.0

if not BASE_URL:
    raise RuntimeError("BASE_URL is not set in environment")

# configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cattle-hut-mcp-server")

app = FastMCP("cattle-hut-mcp-server")

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

if __name__ == "__main__":
    #try:
    #    app.run(transport='sse')
    #finally:
        # best-effort cleanup; if event loop is still running, schedule close
    #    asyncio.run(_shutdown())
    print("Starting MCP SSE server on http://127.0.0.1:9000")
    app.run(transport="sse", host="127.0.0.1", port=9000)