# client.py
import os
from openai import OpenAI

# 1) Configure
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
MCP_URL = os.getenv("MCP_URL", "https://127.0.0.1:6277/mcp")  # your FastMCP server URL
MCP_BEARER = os.getenv("MCP_BEARER")  # optional, if your server needs auth

client = OpenAI()

mcp_tool = {
    "type": "mcp",
    "server_label": "inventory",
    "server_url": MCP_URL,
    "allowed_tools": ["get_stores"],      # keep the surface small & fast
    "require_approval": "never",           # auto-approve tool calls in prod
}

if MCP_BEARER:
    mcp_tool["server_headers"] = {"Authorization": f"Bearer {MCP_BEARER}"}

INSTRUCTIONS = (
    "You are an inventory assistant.\n"
    "Whenever the user asks about stores, call the MCP tool 'list_stores'.\n"
    "Map the user's text into the tool argument 'query'. If the user wants all "
    "stores, call the tool with an empty or null 'query'. Render results as a neat table."
)

def ask(user_text: str):
    resp = client.responses.create(
        model="gpt-4.1-mini",  # or o4-mini for stronger tool use
        instructions=INSTRUCTIONS,
        tools=[mcp_tool],
        input=user_text,
        # Optional: ensure structured output if you want raw JSON instead of a table
        # response_format={"type":"json_schema","json_schema":{
        #   "name":"StoresPayload",
        #   "schema":{"type":"object","properties":{"stores":{"type":"array","items":{"type":"object"}}},"additionalProperties":False}
        # }}
    )
    print(resp.output_text)

if __name__ == "__main__":
    # Example prompt:
    # what are the all stores in the inventry
    ask(input("Ask › "))
