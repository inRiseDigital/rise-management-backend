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

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

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
async def test_connection() -> dict:
    """Simple test to verify MCP server connectivity."""
    try:
        import datetime
        return {
            "success": True,
            "message": "MCP server is working correctly",
            "timestamp": datetime.datetime.now().isoformat(),
            "base_url": BASE_URL
        }
    except Exception as e:
        return {"error": f"Test failed: {str(e)}"}


@app.tool()
async def generate_kitchen_report_json(start_date: str, end_date: str) -> dict:
    """Generate a Kitchen Expenses report in JSON format for debugging.

    Args:
        start_date: Inclusive start date in YYYY-MM-DD format.
        end_date: Inclusive end date in YYYY-MM-DD format.

    Returns:
        dict: Report data in JSON format
    """
    url = f"{BASE_URL}/kitchen/report/"
    params = {"start_date": start_date, "end_date": end_date, "format": "json"}

    session = await get_session()
    try:
        logger.info(f"Requesting kitchen report JSON from: {url} with params: {params}")

        async with session.get(url, params=params) as resp:
            logger.info(f"Response status: {resp.status}")

            if resp.status != 200:
                error_text = await resp.text()
                return {"error": f"Failed to generate kitchen report. Status: {resp.status}. Response: {error_text}"}

            payload = await resp.json()
            logger.info(f"JSON response received: {type(payload)}")

            return {
                "success": True,
                "data": payload,
                "message": f"Kitchen expense report generated for {start_date} to {end_date}"
            }

    except Exception as e:
        logger.error(f"JSON report error: {str(e)}", exc_info=True)
        return {"error": f"JSON report error: {str(e)}"}


@app.tool()
async def generate_kitchen_report(start_date: str, end_date: str) -> dict:
    """Generate and download a Kitchen Expenses PDF report for a date range.

    Args:
        start_date: Inclusive start date in YYYY-MM-DD format.
        end_date: Inclusive end date in YYYY-MM-DD format.

    Returns:
        dict: PDF download information with base64 encoded PDF data
    """
    import base64

    url = f"{BASE_URL}/kitchen/report/"
    params = {"start_date": start_date, "end_date": end_date}  # No format param = PDF by default

    session = await get_session()
    try:
        logger.info(f"Requesting kitchen report PDF from: {url} with params: {params}")

        async with session.get(url, params=params) as resp:
            logger.info(f"Response status: {resp.status}")
            logger.info(f"Response headers: {dict(resp.headers)}")

            if resp.status != 200:
                error_text = await resp.text()
                logger.error(f"Non-200 response: {error_text}")
                return {"error": f"Failed to generate kitchen report PDF. Status code: {resp.status}. Response: {error_text}"}

            # Check content type
            content_type = resp.headers.get('Content-Type', '')
            logger.info(f"Content-Type: {content_type}")

            if 'application/pdf' not in content_type:
                logger.warning(f"Expected PDF but got content type: {content_type}")
                # Try to read as text to see what we actually got
                try:
                    text_content = await resp.text()
                    logger.error(f"Non-PDF response content: {text_content[:500]}...")
                    return {"error": f"Expected PDF but received {content_type}. Content: {text_content[:200]}..."}
                except Exception as text_error:
                    logger.error(f"Could not read response as text: {text_error}")
                    return {"error": f"Expected PDF but received {content_type}. Could not read response."}

            # Get the PDF binary content
            try:
                pdf_content = await resp.read()
                logger.info(f"PDF content read successfully. Size: {len(pdf_content)} bytes")

                # Verify it starts with PDF header
                if not pdf_content.startswith(b'%PDF-'):
                    logger.error(f"Content doesn't start with PDF header. First 50 bytes: {pdf_content[:50]}")
                    return {"error": "Response doesn't appear to be a valid PDF file"}

            except Exception as read_error:
                logger.error(f"Error reading PDF content: {read_error}")
                return {"error": f"Error reading PDF content: {str(read_error)}"}

            # Convert to base64 for frontend
            try:
                pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
                logger.info(f"PDF converted to base64. Base64 length: {len(pdf_base64)}")
            except Exception as b64_error:
                logger.error(f"Error encoding PDF to base64: {b64_error}")
                return {"error": f"Error encoding PDF to base64: {str(b64_error)}"}

            # Extract filename from header
            content_disposition = resp.headers.get("Content-Disposition", "")
            filename = f"kitchen_expense_report_{start_date}_to_{end_date}.pdf"
            if "filename=" in content_disposition:
                filename = content_disposition.split("filename=")[-1].strip('"')

            logger.info(f"Generated kitchen PDF report: {filename}, size: {len(pdf_content)} bytes")

            return {
                "filename": filename,
                "pdf_data": pdf_base64,
                "message": f"Kitchen expense report PDF generated successfully",
                "file_size": len(pdf_content)
            }

    except Exception as e:
        logger.error(f"PDF generation error: {str(e)}", exc_info=True)
        return {"error": f"PDF generation error: {str(e)}"}


@app.tool()
async def download_kitchen_report_pdf(start_date: str, end_date: str) -> dict:
    """Download a Kitchen Expenses PDF report for a date range to Downloads folder.

    Args:
        start_date: Inclusive start date in YYYY-MM-DD format.
        end_date: Inclusive end date in YYYY-MM-DD format.

    Returns:
        dict: Filename and file path of downloaded PDF
    """
    import os
    from pathlib import Path

    url = f"{BASE_URL}/kitchen/report/"
    params = {"start_date": start_date, "end_date": end_date, "format": "pdf"}

    session = await get_session()
    try:
        async with session.get(url, params=params) as resp:
            if resp.status != 200:
                return {"error": f"Failed to generate kitchen report PDF. Status code: {resp.status}"}

            content_disposition = resp.headers.get("Content-Disposition", "")
            filename = f"kitchen_expense_report_{start_date}_to_{end_date}.pdf"
            if "filename=" in content_disposition:
                filename = content_disposition.split("filename=")[-1].strip('"')

            # Save to Downloads folder
            downloads_path = Path.home() / "Downloads"
            output_path = downloads_path / filename

            with open(output_path, "wb") as f:
                f.write(await resp.read())

            return {
                "filename": filename,
                "file_path": str(output_path),
                "message": f"Kitchen expense report PDF successfully downloaded to Downloads folder as {filename}"
            }

    except Exception as e:
        return {"error": str(e)}


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
    Create a new store product category.

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
async def get_subcategories() -> dict:
    """Retrieve all housekeeping subcategories from the Django backend API.

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
    """Create a new housekeeping subcategory for a specific location.

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
    """Retrieve a specific housekeeping subcategory by its ID.

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
    """Update an existing housekeeping subcategory in the Django backend API.

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
    """Delete a housekeeping subcategory from the Django backend API.

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
    """Create a new task for a specific housekeeping location and subcategory.

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
    """Update an existing task in housekeeping the Django backend API.

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
    """Delete a housekeeping task from the Django backend API.

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
    """Retrieve housekeeping all tasks for a specific location.

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
    """Retrieve housekeeping tasks done in a selected time period.

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
    """Retrieve housekeeping all subcategories for a specific location.

    This tool sends a GET request to the Django endpoint
    `/housekeeping/locations/subcategories/<location_id>/` and returns all
    subcategories associated with the specified location.
    """
    result = await request_json("GET", f"{BASE_URL}/housekeeping/locations/subcategories/{location_id}/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"subcategories": result["data"]}

#-- Oil extraction tools ---

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
async def add_new_oil_extraction_detail(machine_id: int, date: str, leaf_type: str, input_weight: str, output_volume: str, on_time: str, on_by: str, off_time: str, off_by: str, run_duration: str, remarks: str = "") -> dict:
    """Add a new oil extraction detail to the Django backend API.

    Args:
        machine_id (int): The ID of the machine associated with the oil extraction detail.
        date (str): The date of the oil extraction detail in YYYY-MM-DD format.
        leaf_type (str): The type of leaf used in the oil extraction detail.
        input_weight (str): The input weight of the oil extraction detail as decimal string.
        output_volume (str): The output volume of the oil extraction detail as decimal string.
        on_time (str): The time when extraction started (HH:MM format).
        on_by (str): Person who started the extraction.
        off_time (str): The time when extraction ended (HH:MM format).
        off_by (str): Person who ended the extraction.
        run_duration (str): Duration of extraction (HH:MM:SS format).
        remarks (str): Optional remarks about the extraction process.

    Returns:
        dict: The added oil extraction detail data or an error message.
    """
    data = {
        "machine": machine_id,
        "date": date,
        "leaf_type": leaf_type,
        "input_weight": input_weight,
        "output_volume": output_volume,
        "on_time": on_time,
        "on_by": on_by,
        "off_time": off_time,
        "off_by": off_by,
        "run_duration": run_duration,
        "remarks": remarks
    }
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
async def update_oil_extraction_detail(
    id: int,
    machine_id: int = None,
    date: str = None,
    leaf_type: str = None,
    input_weight: str = None,
    output_volume: str = None,
    on_time: str = None,
    on_by: str = None,
    off_time: str = None,
    off_by: str = None,
    run_duration: str = None,
    remarks: str = None
) -> dict:
    """Update an existing oil extraction detail in the Django backend API.

    Only provide the fields you want to update. All parameters except 'id' are optional.

    Args:
        id (int): The ID of the oil extraction detail to update (REQUIRED).
        machine_id (int): Optional. The ID of the machine associated with the oil extraction detail.
        date (str): Optional. The date of the oil extraction detail in YYYY-MM-DD format.
        leaf_type (str): Optional. The type of leaf used in the oil extraction detail.
        input_weight (str): Optional. The input weight of the oil extraction detail as decimal string.
        output_volume (str): Optional. The output volume of the oil extraction detail as decimal string.
        on_time (str): Optional. The time when extraction started (HH:MM format).
        on_by (str): Optional. Person who started the extraction.
        off_time (str): Optional. The time when extraction ended (HH:MM format).
        off_by (str): Optional. Person who ended the extraction.
        run_duration (str): Optional. Duration of extraction (HH:MM:SS format).
        remarks (str): Optional. Remarks about the extraction process.

    Returns:
        dict: The updated oil extraction detail data or an error message.

    Example:
        # Update only the remarks field
        await update_oil_extraction_detail(id=1, remarks="no issues")

        # Update multiple fields
        await update_oil_extraction_detail(id=1, leaf_type="Citronella", remarks="Good quality")
    """
    # Build data dict with only provided fields
    data = {}
    if machine_id is not None:
        data["machine"] = machine_id
    if date is not None:
        data["date"] = date
    if leaf_type is not None:
        data["leaf_type"] = leaf_type
    if input_weight is not None:
        data["input_weight"] = input_weight
    if output_volume is not None:
        data["output_volume"] = output_volume
    if on_time is not None:
        data["on_time"] = on_time
    if on_by is not None:
        data["on_by"] = on_by
    if off_time is not None:
        data["off_time"] = off_time
    if off_by is not None:
        data["off_by"] = off_by
    if run_duration is not None:
        data["run_duration"] = run_duration
    if remarks is not None:
        data["remarks"] = remarks

    if not data:
        return {"error": "No fields provided to update", "status": 400}

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
async def get_inventory_report_details() -> dict:
    """
    Get comprehensive inventory details for report generation.

    This tool fetches detailed inventory information from the stores app including:
    - Summary statistics (total items, total value, low stock count, etc.)
    - Items breakdown by store
    - Items breakdown by category
    - Low stock items (units < 10)
    - High value items (top 10 by total cost)

    The tool calls the Django endpoint `/stores/inventory/report-details/`
    which provides aggregated inventory data useful for generating reports.

    Returns:
        dict: Comprehensive inventory report data containing:
            - summary: Basic statistics
            - stores_breakdown: Items count and value per store
            - categories_breakdown: Items count and value per category
            - low_stock_items: Items with less than 10 units
            - high_value_items: Top 10 items by total cost

    Example:
        >>> await get_inventory_report_details()
        {
          "summary": {
            "total_items": 45,
            "total_inventory_value": 12500.75,
            "low_stock_count": 8,
            "stores_count": 3,
            "categories_count": 5
          },
          "stores_breakdown": [
            {"store_name": "Main Store", "item_count": 25, "total_value": 8000.50}
          ],
          "categories_breakdown": [
            {"category_name": "Electronics", "item_count": 15, "total_value": 5000.25}
          ],
          "low_stock_items": [...],
          "high_value_items": [...]
        }
    """
    url = f"{BASE_URL}/stores/inventory/report-details/"
    return await _get_and_normalize(url)


@app.tool()
async def generate_inventory_report_pdf() -> dict:
    """
    Generate a comprehensive PDF report of current inventory.

    This tool generates a PDF document containing detailed inventory information including:
    - Summary statistics (total items, total value, low stock count, etc.)
    - Items breakdown by store with detailed tables
    - Items breakdown by category
    - Low stock items section (highlighted in red)
    - Professional formatting with tables and proper pagination

    The PDF is saved to the Downloads folder and includes:
    - Professional header with report title and generation timestamp
    - Summary section with key metrics
    - Detailed inventory by store (up to 10 items per store shown)
    - Low stock alerts section if applicable
    - Proper table formatting with headers and styling

    Returns:
        dict: Success confirmation with filename and file path

    Example:
        >>> await generate_inventory_report_pdf()
        {
          "success": True,
          "message": "Inventory report PDF generated successfully and saved to Downloads folder",
          "filename": "inventory_report_20250926_140530.pdf",
          "file_path": "/Users/username/Downloads/inventory_report_20250926_140530.pdf"
        }
    """
    import os
    url = f"{BASE_URL}/stores/inventory/report-pdf/"
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(url)
            if response.status_code == 200:
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"inventory_report_{timestamp}.pdf"

                # Save to Downloads folder
                downloads_folder = os.path.join(os.path.expanduser("~"), "Downloads")
                os.makedirs(downloads_folder, exist_ok=True)
                file_path = os.path.join(downloads_folder, filename)

                with open(file_path, 'wb') as f:
                    f.write(response.content)

                return {
                    "success": True,
                    "message": "Inventory report PDF generated successfully and saved to Downloads folder",
                    "filename": filename,
                    "file_path": file_path,
                    "file_size": f"{len(response.content)} bytes"
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to generate PDF. Status: {response.status_code}"
                }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error generating inventory PDF: {str(e)}"
        }


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


@app.tool()
async def generate_document_with_data(report_type: str, start_date: str = "", end_date: str = "", subtype: str = "records") -> dict:
    """
    Universal document/report generator that retrieves data first, then generates PDF.

    This tool is designed to handle ANY type of report request. When a user asks
    "generate report" or "create document", this tool:
    1. Detects the report type and subtype
    2. Retrieves the appropriate data using existing tools
    3. Generates a PDF document with that data

    Args:
        report_type: Type of report to generate. Options:
            - "kitchen" or "kitchen_expenses": Kitchen expense report
            - "milk" or "cattle_hut": Milk collection report
            - "housekeeping" or "tasks": Housekeeping tasks report
            - "inventory" or "stores": Inventory report
            - "oil" or "oil_extraction": Oil extraction report
        start_date: Start date in YYYY-MM-DD format (e.g., "2025-09-01"). Optional for list-type reports.
        end_date: End date in YYYY-MM-DD format (e.g., "2025-09-30"). Optional for list-type reports.
        subtype: Subtype of report within the domain. Options:
            - "records": Transaction/record data (expenses, extractions, etc.) - DEFAULT
            - "list": List/inventory data (machines, items, categories)
            - "summary": Aggregate/summary data (totals, statistics)

    Returns:
        dict: Contains retrieved data and PDF information:
            - success: Boolean indicating success
            - report_type: Type of report generated
            - subtype: Subtype of report
            - data: The retrieved data
            - pdf_data: Base64-encoded PDF (if applicable)
            - filename: PDF filename
            - message: Success message with summary
            - file_size: PDF size in bytes

    Examples:
        User: "Generate kitchen report for September"
        >>> await generate_document_with_data("kitchen", "2025-09-01", "2025-09-30")

        User: "Generate PDF of available oil extraction machines"
        >>> await generate_document_with_data("oil", subtype="list")
    """
    try:
        import base64

        logger.info(f"Universal document generator called: type={report_type}, dates={start_date} to {end_date}")

        report_type_lower = report_type.lower()

        # Route to appropriate report generator based on type
        if report_type_lower in ["kitchen", "kitchen_expenses", "kitchen_expense"]:
            logger.info("Routing to kitchen expense report generator")

            # Step 1: Retrieve kitchen expense data (call endpoint directly, not other tools)
            logger.info("Step 1: Retrieving kitchen expense data...")

            # Call the backend API directly instead of calling other tools
            session = await get_session()
            url = f"{BASE_URL}/kitchen/report/"
            params = {"start_date": start_date, "end_date": end_date, "format": "json"}

            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    return {
                        "success": False,
                        "report_type": "kitchen_expenses",
                        "error": f"Failed to retrieve kitchen data: HTTP {resp.status}",
                        "step": "data_retrieval"
                    }
                expense_data = await resp.json()

            total_expenses = expense_data.get("total_expenses", 0)
            expense_count = expense_data.get("expense_count", 0)

            logger.info(f"Retrieved {expense_count} expenses, total: Rs. {total_expenses}")

            # Step 2: Generate PDF (call endpoint directly)
            logger.info("Step 2: Generating PDF document...")

            # Call PDF endpoint directly
            url_pdf = f"{BASE_URL}/kitchen/report/"
            params_pdf = {"start_date": start_date, "end_date": end_date}  # No format param = PDF by default

            async with session.get(url_pdf, params=params_pdf) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    return {
                        "success": False,
                        "report_type": "kitchen_expenses",
                        "data": expense_data,
                        "error": f"Data retrieved but PDF generation failed: HTTP {resp.status}",
                        "step": "pdf_generation"
                    }

                # Check content type
                content_type = resp.headers.get('Content-Type', '')
                if 'application/pdf' not in content_type:
                    return {
                        "success": False,
                        "report_type": "kitchen_expenses",
                        "data": expense_data,
                        "error": f"Expected PDF but received {content_type}",
                        "step": "pdf_generation"
                    }

                # Get PDF content
                pdf_content = await resp.read()

                # Verify PDF header
                if not pdf_content.startswith(b'%PDF-'):
                    return {
                        "success": False,
                        "report_type": "kitchen_expenses",
                        "data": expense_data,
                        "error": "Response doesn't appear to be a valid PDF file",
                        "step": "pdf_generation"
                    }

            # Convert to base64
            pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
            filename = f"kitchen_expense_report_{start_date}_to_{end_date}.pdf"

            logger.info(f"Generated kitchen PDF report: {filename}, size: {len(pdf_content)} bytes")

            return {
                "success": True,
                "report_type": "kitchen_expenses",
                "data": expense_data,
                "pdf_data": pdf_base64,
                "filename": filename,
                "message": f"Kitchen expense report generated successfully with {expense_count} expenses totaling Rs. {total_expenses:,.2f}",
                "file_size": len(pdf_content),
                "date_range": {"start": start_date, "end": end_date}
            }

        elif report_type_lower in ["milk", "cattle_hut", "milk_collection"]:
            logger.info("Routing to milk collection report generator")

            # Step 1: Retrieve milk collection data
            logger.info("Step 1: Retrieving milk collection data...")
            data_result = await get_all_milk_entries_in_time_period(start_date, end_date)

            if "error" in data_result:
                return {
                    "success": False,
                    "report_type": "milk_collection",
                    "error": f"Failed to retrieve milk data: {data_result['error']}",
                    "step": "data_retrieval"
                }

            milk_data = data_result.get("data", [])
            entry_count = len(milk_data) if isinstance(milk_data, list) else 0

            logger.info(f"Retrieved {entry_count} milk collection entries")

            # Step 2: Generate PDF
            logger.info("Step 2: Generating PDF document...")
            pdf_result = await export_milk_collection_pdf(start_date, end_date)

            if "error" in pdf_result:
                return {
                    "success": False,
                    "report_type": "milk_collection",
                    "data": milk_data,
                    "error": f"Data retrieved but PDF generation failed: {pdf_result['error']}",
                    "step": "pdf_generation"
                }

            return {
                "success": True,
                "report_type": "milk_collection",
                "data": milk_data,
                "filename": pdf_result.get("filename"),
                "file_path": pdf_result.get("file_path"),
                "message": f"Milk collection report generated successfully with {entry_count} entries",
                "date_range": {"start": start_date, "end": end_date}
            }

        elif report_type_lower in ["housekeeping", "tasks", "housekeeping_tasks"]:
            logger.info("Routing to housekeeping tasks report generator")

            # Step 1: Retrieve housekeeping tasks data
            logger.info("Step 1: Retrieving housekeeping tasks data...")
            data_result = await get_tasks_by_period(start_date, end_date)

            if "error" in data_result:
                return {
                    "success": False,
                    "report_type": "housekeeping_tasks",
                    "error": f"Failed to retrieve housekeeping data: {data_result['error']}",
                    "step": "data_retrieval"
                }

            tasks_data = data_result.get("data", [])
            task_count = len(tasks_data) if isinstance(tasks_data, list) else 0

            logger.info(f"Retrieved {task_count} housekeeping tasks")

            # Step 2: Generate PDF
            logger.info("Step 2: Generating PDF document...")
            pdf_result = await generate_task_report_pdf(start_date, end_date)

            if "error" in pdf_result:
                return {
                    "success": False,
                    "report_type": "housekeeping_tasks",
                    "data": tasks_data,
                    "error": f"Data retrieved but PDF generation failed: {pdf_result['error']}",
                    "step": "pdf_generation"
                }

            return {
                "success": True,
                "report_type": "housekeeping_tasks",
                "data": tasks_data,
                "filename": pdf_result.get("filename"),
                "file_path": pdf_result.get("file_path"),
                "message": f"Housekeeping tasks report generated successfully with {task_count} tasks",
                "date_range": {"start": start_date, "end": end_date}
            }

        elif report_type_lower in ["inventory", "stores", "inventory_report"]:
            logger.info("Routing to inventory report generator")

            # Step 1: Retrieve inventory data
            logger.info("Step 1: Retrieving inventory data...")
            data_result = await get_inventory_items()

            if "error" in data_result:
                return {
                    "success": False,
                    "report_type": "inventory",
                    "error": f"Failed to retrieve inventory data: {data_result['error']}",
                    "step": "data_retrieval"
                }

            inventory_data = data_result.get("data", [])
            item_count = len(inventory_data) if isinstance(inventory_data, list) else 0

            logger.info(f"Retrieved {item_count} inventory items")

            # Step 2: Generate PDF
            logger.info("Step 2: Generating PDF document...")
            pdf_result = await generate_inventory_report_pdf()

            if not pdf_result.get("success"):
                return {
                    "success": False,
                    "report_type": "inventory",
                    "data": inventory_data,
                    "error": f"Data retrieved but PDF generation failed: {pdf_result.get('error')}",
                    "step": "pdf_generation"
                }

            return {
                "success": True,
                "report_type": "inventory",
                "data": inventory_data,
                "filename": pdf_result.get("filename"),
                "file_path": pdf_result.get("file_path"),
                "message": f"Inventory report generated successfully with {item_count} items",
                "file_size": pdf_result.get("file_size")
            }

        elif report_type_lower in ["oil", "oil_extraction", "oil_extraction_report"]:
            logger.info(f"Routing to oil extraction report generator - subtype: {subtype}")

            session = await get_session()

            # Handle different subtypes
            if subtype.lower() in ["list", "machines", "machine_list"]:
                # Machine list report (no date range needed)
                logger.info("Generating machine list report...")

                # Step 1: Retrieve machine data
                url = f"{BASE_URL}/oil/machines-report/"
                params = {"format": "json"}

                async with session.get(url, params=params) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        return {
                            "success": False,
                            "report_type": "oil_extraction",
                            "subtype": "machine_list",
                            "error": f"Failed to retrieve machine list: HTTP {resp.status}",
                            "step": "data_retrieval"
                        }

                    machine_data = await resp.json()
                    machine_count = machine_data.get("total_machines", 0)

                # Step 2: Generate PDF
                url_pdf = f"{BASE_URL}/oil/machines-report/"
                async with session.get(url_pdf) as resp:
                    if resp.status != 200:
                        return {
                            "success": False,
                            "report_type": "oil_extraction",
                            "subtype": "machine_list",
                            "data": machine_data,
                            "error": f"Data retrieved but PDF generation failed: HTTP {resp.status}",
                            "step": "pdf_generation"
                        }

                    pdf_content = await resp.read()

                # Convert to base64 and return
                pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
                return {
                    "success": True,
                    "report_type": "oil_extraction",
                    "subtype": "machine_list",
                    "data": machine_data,
                    "pdf_data": pdf_base64,
                    "filename": "oil_extraction_machines_list.pdf",
                    "message": f"Oil extraction machines report generated successfully with {machine_count} machines",
                    "file_size": len(pdf_content)
                }

            else:
                # Default: extraction records report (requires date range)
                if not start_date or not end_date:
                    return {
                        "success": False,
                        "report_type": "oil_extraction",
                        "subtype": "records",
                        "error": "start_date and end_date are required for extraction records report",
                        "step": "validation"
                    }

                # Step 1: Retrieve oil extraction data (call endpoint directly)
                logger.info("Step 1: Retrieving oil extraction records...")

                url = f"{BASE_URL}/oil/report/"
                params = {"start_date": start_date, "end_date": end_date, "format": "json"}

                async with session.get(url, params=params) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        return {
                            "success": False,
                            "report_type": "oil_extraction",
                            "subtype": "records",
                            "error": f"Failed to retrieve oil extraction data: HTTP {resp.status}",
                            "step": "data_retrieval"
                        }
                    oil_data = await resp.json()

                record_count = oil_data.get("total_records", 0)
                total_input = oil_data.get("total_input_weight", 0)
                total_output = oil_data.get("total_output_volume", 0)

                logger.info(f"Retrieved {record_count} oil extraction records")

                # Step 2: Generate PDF
                logger.info("Step 2: Generating PDF document...")

                url_pdf = f"{BASE_URL}/oil/report/"
                params_pdf = {"start_date": start_date, "end_date": end_date}  # No format param = PDF by default

                async with session.get(url_pdf, params=params_pdf) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        return {
                            "success": False,
                            "report_type": "oil_extraction",
                            "subtype": "records",
                            "data": oil_data,
                            "error": f"Data retrieved but PDF generation failed: HTTP {resp.status}",
                            "step": "pdf_generation"
                        }

                    # Check content type
                    content_type = resp.headers.get('Content-Type', '')
                    if 'application/pdf' not in content_type:
                        return {
                            "success": False,
                            "report_type": "oil_extraction",
                            "subtype": "records",
                            "data": oil_data,
                            "error": f"Expected PDF but received {content_type}",
                            "step": "pdf_generation"
                        }

                    # Get PDF content
                    pdf_content = await resp.read()

                # Verify PDF header
                if not pdf_content.startswith(b'%PDF-'):
                    return {
                        "success": False,
                        "report_type": "oil_extraction",
                        "subtype": "records",
                        "data": oil_data,
                        "error": "Response doesn't appear to be a valid PDF file",
                        "step": "pdf_generation"
                    }

                # Convert to base64
                pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
                filename = f"oil_extraction_report_{start_date}_to_{end_date}.pdf"

                logger.info(f"Generated oil extraction PDF report: {filename}, size: {len(pdf_content)} bytes")

                return {
                    "success": True,
                    "report_type": "oil_extraction",
                    "subtype": "records",
                    "data": oil_data,
                    "pdf_data": pdf_base64,
                    "filename": filename,
                    "message": f"Oil extraction report generated successfully with {record_count} records. Input: {total_input:.2f} kg, Output: {total_output:.2f} L",
                "file_size": len(pdf_content),
                "date_range": {"start": start_date, "end": end_date}
            }

        else:
            return {
                "success": False,
                "error": f"Unknown report type: {report_type}",
                "supported_types": [
                    "kitchen/kitchen_expenses",
                    "milk/cattle_hut/milk_collection",
                    "housekeeping/tasks",
                    "inventory/stores",
                    "oil/oil_extraction"
                ]
            }
    except Exception as e:
        logger.error(f"Error in generate_document_with_data: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": f"Unexpected error generating document: {str(e)}",
            "report_type": report_type if 'report_type' in locals() else "unknown"
        }


@app.tool()
async def generate_pdf_from_data(title: str, data: list, description: str = "") -> dict:
    """
        Generate PDF from already-retrieved data.

        This tool takes data you've already fetched using other tools (get_stores, get_machines, etc.)
        and generates a PDF report.

        WORKFLOW:
        1. User asks: "generate report for stores"
        2. You call: get_stores() to retrieve data
        3. You call: generate_pdf_from_data(title="Store List", data=result_from_get_stores)
        4. PDF is generated and returned!

        Args:
            title: Report title (e.g., "Store List Report", "Machine List")
            data: The data to include in PDF - should be a list of dictionaries
            description: Optional subtitle/description

        Returns:
            dict with success, pdf_data (base64), filename, message

        Examples:
            # After calling get_stores():
            >>> stores_data = await get_stores()
            >>> await generate_pdf_from_data("Store List Report", stores_data)

            # After calling get_oil_extraction_machines():
            >>> machines = await get_oil_extraction_machines()
            >>> await generate_pdf_from_data("Oil Extraction Machines", machines)
    """  
    try:
        import base64
        import json
        from datetime import datetime

        logger.info(f"Generating PDF from data: title={title}, {len(data) if isinstance(data, list) else 0} items")

        # Prepare the data for PDF generation
        # Convert data to proper format if needed
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except:
                return {
                    "success": False,
                    "error": "Data must be a list or valid JSON string"
                }

        if not isinstance(data, list):
            return {
                "success": False,
                "error": "Data must be a list of items"
            }

        if len(data) == 0:
            return {
                "success": False,
                "error": "No data provided to generate PDF"
            }

        # Use the universal PDF generator utility
        session = await get_session()

        # We'll send the data to a special endpoint that generates PDF from provided data
        url = f"{BASE_URL}/api/universal-report-from-data/"
        payload = {
            "title": title,
            "data": data,
            "description": description,
            "metadata": {
                "total_records": len(data),
                "generated_at": datetime.now().isoformat()
            }
        }

        logger.info(f"Calling PDF generation endpoint with {len(data)} records")

        async with session.post(url, json=payload) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                logger.error(f"PDF generation failed: HTTP {resp.status}, {error_text}")
                return {
                    "success": False,
                    "error": f"Failed to generate PDF: HTTP {resp.status}",
                    "details": error_text
                }

            result = await resp.json()

            if not result.get("success"):
                return result

            logger.info(f"PDF generated successfully: {result.get('filename')}, size: {result.get('file_size')} bytes")

            return {
                "success": True,
                "pdf_data": result.get("pdf_data"),
                "filename": result.get("filename"),
                "file_size": result.get("file_size"),
                "message": f"PDF report '{title}' generated successfully with {len(data)} records"
            }

    except Exception as e:
        logger.error(f"Error in generate_pdf_from_data: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


@app.tool()
async def generate_universal_report(app_name: str, model_name: str, title: str = "", start_date: str = "", end_date: str = "") -> dict:
    """
    🌟 UNIVERSAL PDF REPORT GENERATOR 🌟

    This is a completely generic tool that can generate PDF reports for ANY Django model
    without needing hardcoded logic for each model type.

    Use this tool when:
    - User asks for a report about data you're not familiar with
    - User requests reports for stores, machines, categories, or any other data
    - You want to generate a PDF for ANY model in the system

    Args:
        app_name: Django app name (e.g., "oil_extraction", "stores", "kitchen", "cattle_hut")
        model_name: Model name (e.g., "Machine", "Store", "KitchenExpense", "Category")
        title: Custom report title (optional, auto-generated if not provided)
        start_date: Filter by date >= start_date (optional, format: YYYY-MM-DD)
        end_date: Filter by date <= end_date (optional, format: YYYY-MM-DD)

    Returns:
        dict: Contains PDF data and metadata:
            - success: Boolean
            - pdf_data: Base64-encoded PDF
            - filename: PDF filename
            - file_size: Size in bytes
            - model: Model name
            - app: App name

    Examples:
        User: "Generate PDF of oil extraction machines"
        >>> await generate_universal_report("oil_extraction", "Machine", "Oil Extraction Machines")

        User: "Show me store data as PDF"
        >>> await generate_universal_report("stores", "Store")

        User: "Generate kitchen expense report for September"
        >>> await generate_universal_report("kitchen", "Expense", start_date="2025-09-01", end_date="2025-09-30")

        User: "PDF of all product categories"
        >>> await generate_universal_report("stores", "ProductCategory")

    Model Name Mapping (common models):
        - Oil Extraction:
            * Machine → "Machine"
            * Extraction records → "ExtractionRecord"
            * Oil purchases → "OilPurchase"

        - Stores/Inventory:
            * Stores → "Store"
            * Categories → "ProductCategory"
            * Subcategories → "ProductSubcategory"
            * Inventory items → "InventoryItem"

        - Kitchen:
            * Expenses → "Expense"
            * Categories → "Category"

        - Cattle Hut:
            * Cattle → "Cattle"
            * Milk collection → "MilkCollection"

        - Housekeeping:
            * Tasks → "Task"
    """
    try:
        import base64

        logger.info(f"Universal report generator called: app={app_name}, model={model_name}, dates={start_date} to {end_date}")

        # Build URL with parameters
        session = await get_session()
        url = f"{BASE_URL}/api/universal-report-base64/"
        params = {
            "app": app_name,
            "model": model_name,
            "format": "pdf"
        }

        if title:
            params["title"] = title

        if start_date:
            params["start_date"] = start_date

        if end_date:
            params["end_date"] = end_date

        logger.info(f"Calling universal report endpoint: {url} with params: {params}")

        async with session.get(url, params=params) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                logger.error(f"Universal report failed: HTTP {resp.status}, {error_text}")

                # Try to parse error JSON
                try:
                    import json
                    error_data = json.loads(error_text)
                    return {
                        "success": False,
                        "error": error_data.get("error", f"HTTP {resp.status}"),
                        "tip": error_data.get("tip", ""),
                        "app": app_name,
                        "model": model_name
                    }
                except:
                    return {
                        "success": False,
                        "error": f"Failed to generate universal report: HTTP {resp.status}",
                        "details": error_text,
                        "app": app_name,
                        "model": model_name
                    }

            result = await resp.json()

            if not result.get("success"):
                return result

            logger.info(f"Universal report generated successfully: {result.get('filename')}, size: {result.get('file_size')} bytes")

            return {
                "success": True,
                "pdf_data": result.get("pdf_data"),
                "filename": result.get("filename"),
                "file_size": result.get("file_size"),
                "model": model_name,
                "app": app_name,
                "message": f"Universal report generated successfully for {model_name} ({app_name})"
            }

    except Exception as e:
        logger.error(f"Error in generate_universal_report: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "app": app_name,
            "model": model_name
        }


#-- MEP Projects (for future multi-project support) --#

@app.tool()
async def project_create() -> dict:
    """Create new project  from the Django backend API.

    This tool sends a POST request to the Django endpoint
    `/mep/MEP_projects/` and create new MEP project.
    """
    result = await request_json("POST", f"{BASE_URL}/mep/MEP_projects/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"stores": result["data"]}

@app.tool()
async def project_list() -> dict:
    """List all MEP projects from the Django backend API.

    This tool sends a GET request to the Django endpoint
    `/mep/MEP_projects/` and retrieves all MEP projects.
    """
    result = await request_json("GET", f"{BASE_URL}/mep/MEP_projects/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"stores": result["data"]}

@app.tool()
async def project_delete(project_id: str) -> dict:
    """Delete a MEP project by ID from the Django backend API.

    This tool sends a DELETE request to the Django endpoint
    `/mep/MEP_projects/<project_id>/` to delete the specified project.
    """
    result = await request_json("DELETE", f"{BASE_URL}/mep/MEP_projects/{project_id}/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"message": "Project deleted successfully"}  

@app.tool()
async def project_get(project_id: str) -> dict:
    """Get a MEP project by ID from the Django backend API.

    This tool sends a GET request to the Django endpoint
    `/mep/MEP_projects/<project_id>/` to retrieve the specified project.
    """
    result = await request_json("GET", f"{BASE_URL}/mep/MEP_projects/{project_id}/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"project": result["data"]}

@app.tool()
async def project_update(project_id: int, data: dict) -> dict:
    """Update a MEP project by ID from the Django backend API.

    This tool sends a PUT request to the Django endpoint
    `/mep/MEP_projects/<project_id>/` to update the specified project with new data.
    """
    result = await request_json("PUT", f"{BASE_URL}/mep/MEP_projects/{project_id}/", json=data)
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"project": result["data"]}

@app.tool()
async def create_new_task(project_id: int, task_data: dict) -> dict:
    """Create a new task in a MEP project.

    This tool sends a POST request to the Django endpoint
    `/mep/MEP_projects/<project_id>/tasks/` to create a new task in the specified project.
    """
    result = await request_json("POST", f"{BASE_URL}/mep/MEP_projects/{project_id}/tasks/", json=task_data)
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"task": result["data"]}

@app.tool()
async def list_tasks(task_id: str) -> dict:
    """List all tasks in a MEP project.

    This tool sends a GET request to the Django endpoint
    `/mep/MEP_projects/<project_id>/tasks/` to retrieve all tasks in the specified project.
    """
    result = await request_json("GET", f"{BASE_URL}/mep/MEP_projects/{task_id}/tasks/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"tasks": result["data"]}

@app.tool()
async def delete_task(id: int) -> dict:
    """Delete a task by ID from a MEP project.

    This tool sends a DELETE request to the Django endpoint
    `/mep/MEP_projects/<project_id>/tasks/<task_id>/` to delete the specified task.
    """
    result = await request_json("DELETE", f"{BASE_URL}/mep/MEP_projects/{id}/tasks/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"message": "Task deleted successfully"}

@app.tool()
async def get_task(id: int) -> dict:
    """Get a task by ID from a MEP project.

    This tool sends a GET request to the Django endpoint
    `/mep/MEP_projects/<project_id>/tasks/<task_id>/` to retrieve the specified task.
    """
    result = await request_json("GET", f"{BASE_URL}/mep/MEP_projects/{id}/tasks/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"task": result["data"]}

@app.tool()
async def get_ongoin_task(project_id: int) -> dict:
    """Get all ongoing tasks from the MEP project.

    This tool sends a GET request to the Django endpoint
    `/mep/MEP_projects/<int:project_id>/tasks/ongoing/` to retrieve all ongoing tasks.
    """
    result = await request_json("GET", f"{BASE_URL}/mep/MEP_projects/{project_id}/tasks/ongoing/")
    if "error" in result:
        return {"error": result["error"], "status": result.get("status")}
    return {"tasks": result["data"]}


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
