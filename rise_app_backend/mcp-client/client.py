from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
import subprocess, asyncio, os
from agents import Agent, Runner, gen_trace_id, trace
from agents.mcp import MCPServerSse
from agents.model_settings import ModelSettings

app = FastAPI()

mcp_process = None
mcp_server = None
agent = None

@app.on_event("startup")
async def startup():
    global mcp_server, agent, mcp_process

    # Start your local MCP server
    mcp_process = subprocess.Popen(["uvicorn", "mcp_server:app", "--port", "6274"])
    await asyncio.sleep(3)  # wait for it to boot up

    # Connect to the running MCP server
    mcp_server = MCPServerSse(name="django-mcp-server", params={"url": "http://localhost:6274/sse"})
    await mcp_server.__aenter__()

    # Initialize the AI agent
    instructions = "You are an Inventory Assistant. Use the tools provided."
    agent = Agent(
        name="Inventory Assistant",
        model="gpt-4",  # or "gpt-3.5-turbo"
        instructions=instructions,
        mcp_server=[mcp_server],
        model_settings=ModelSettings(tool_choice="required")
    )

@app.on_event("shutdown")
async def shutdown():
    global mcp_server, mcp_process
    if mcp_server:
        await mcp_server.__aexit__(None, None, None)
    if mcp_process:
        mcp_process.terminate()

@app.get("/", response_class=HTMLResponse)
async def form():
    return """
    <form action="/ask" method="post">
        <input name="question" placeholder="Ask your inventory AI" />
        <button type="submit">Ask</button>
    </form>
    """

@app.post("/ask", response_class=HTMLResponse)
async def ask(question: str = Form(...)):
    global agent
    if not agent:
        return "Agent not initialized"
    
    trace_id = gen_trace_id()
    with trace(workflow_name="inventory-query", trace_id=trace_id):
        result = await Runner.run(starting_agent=agent, input=question)
        return f"<p><strong>Q:</strong> {question}</p><p><strong>A:</strong> {result.final_output}</p>"
