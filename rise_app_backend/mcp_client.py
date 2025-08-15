import openai
import os
from dotenv import load_dotenv
import asyncio
import aiohttp
from fastmcp import FastMCP

# Load environment variables
load_dotenv()

# Retrieve OpenAI API Key from .env
openai.api_key = os.getenv("OPENAI_API_KEY")

if not openai.api_key:
    raise RuntimeError("OPENAI_API_KEY is not set in the environment.")

# Set up FastMCP client
app = FastMCP("openai-mcp-client")

# Shared session
_shared_session: aiohttp.ClientSession | None = None
_session_lock = asyncio.Lock()

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")  # Make sure the server's base URL is correct

async def get_session() -> aiohttp.ClientSession:
    """
    Ensure only one shared aiohttp.ClientSession is created and used.
    """
    global _shared_session
    async with _session_lock:
        if _shared_session is None or _shared_session.closed:
            timeout = aiohttp.ClientTimeout(total=10)  # 10s default timeout
            _shared_session = aiohttp.ClientSession(timeout=timeout)
        return _shared_session

async def call_openai(prompt: str) -> dict:
    """
    Function to call OpenAI API with a given prompt and return response.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # or "gpt-4" or another model
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
        )
        return {"response": response['choices'][0]['message']['content'].strip()}
    except Exception as e:
        return {"error": str(e)}

async def call_server_tool(url: str, method: str = "GET", json_data: dict = None) -> dict:
    """
    Make a request to the server to call the respective tool.
    """
    session = await get_session()
    try:
        async with session.request(method, url, json=json_data) as resp:
            if resp.status != 200:
                return {"error": f"Failed to connect: {resp.status}"}

            response_json = await resp.json()
            return response_json
    except Exception as e:
        return {"error": str(e)}

# Example: Call `add_store` on the server
async def add_store(data: dict) -> dict:
    url = f"{BASE_URL}/stores/add_stores/"  # This is the endpoint for adding a store
    return await call_server_tool(url, method="POST", json_data=data)

# Example: Call `get_store_by_id` on the server
async def get_store_by_id(store_id: int) -> dict:
    url = f"{BASE_URL}/stores/stores/{store_id}/"  # This is the endpoint for fetching store by ID
    return await call_server_tool(url)

async def handle_prompt(prompt: str) -> dict:
    """
    Handle different types of prompts (like generating OpenAI response or calling server tools).
    """
    if "Create a new store" in prompt:
        # Extract the store name from the prompt (e.g., "Store A")
        store_name = prompt.split("'")[1]
        data = {"name": store_name}
        result = await add_store(data)  # Call server's add_store tool
        return result

    elif prompt.startswith("Get store by ID"):
        store_id = int(prompt.split(" ")[-1])  # Extract the store ID
        result = await get_store_by_id(store_id)  # Call server's get_store_by_id tool
        return result
    
    # You can add more conditions for other types of prompts like updating inventory, etc.
    
    # If no special task is found, process with OpenAI
    return await call_openai(prompt)

@app.tool()
async def generate_openai_response(prompt: str) -> dict:
    """
    Tool that calls OpenAI API to generate a response for a given prompt.
    """
    result = await call_openai(prompt)
    return result

async def _shutdown():
    global _shared_session
    if _shared_session and not _shared_session.closed:
        await _shared_session.close()
        print("HTTP session closed.")

def main():
    """
    Main function to interact with the user and process the prompt.
    """
    print("MCP Client running. Type 'exit' to quit.")
    
    while True:
        prompt = input("Enter your prompt: ")  # Get prompt from user
        if prompt.lower() == 'exit':
            break
        
        # Handle the prompt (either by calling OpenAI or server tools)
        result = asyncio.run(handle_prompt(prompt))
        
        # Display the result
        print("Result:", result)

if __name__ == "__main__":
    try:
        main()  # Start the client interaction
    finally:
        asyncio.run(_shutdown())  # Cleanup
