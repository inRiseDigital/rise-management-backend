import os
import subprocess
import asyncio
import shutil
import time
import openai
from typing import Any
from fastapi import FastAPI,Request,Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from agents import Agent,Runner, gen_trace_id, trace
from agents.mcp import MCPServer, MCPServerSse
from agents.model_settings import ModelSettings
from dotenv import load_dotenv
import markdown


load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()

# Set up Jinja2 templates

async def ask_agent(question: str) -> str:
    this_dir = os.path.dirname(os.path.abspath(__file__))
    server_file = os.path.join(this_dir, "mcp_server.py")
    
    if not shutil.which("uv"):
        raise RuntimeError("uv command not found. Please install uv to run the MCP server.")
    
    print("Starting MCP server...")
    process: subprocess.Popen[any] = subprocess.Popen(["uv","run", server_file])
    time.sleep(3)  # Wait for server to start
    
    mcp_server = MCPServerSse(
        name="SSE mcp_server",
        params={"url": "http://localhost:6274/sse"},)
    
    try:
        await mcp_server.__aenter__()
        trace_id = gen_trace_id()
        with trace(workflow_name = "SSE Example", trace_id=trace_id):
            print(f"view trace: https://platform.openai.com/traces/trace?trace_id={trace_id}\n")
            instructions = '''
                You are an Inventory Management Assistant AI.  
                Your primary goal is to help users by accurately answering questions about the company's inventory.  
                You have access to the latest inventory database through provided tools and APIs.

                Guidelines:
                1. Always give clear, concise, and factual answers based on the inventory data.
                2. When giving quantities, include units (e.g., “120 units”, “15 kg”).
                3. If an item is out of stock, suggest alternatives or expected restock dates if available.
                4. If the question is unclear, ask clarifying questions before answering.
                5. Only answer within the scope of inventory management (e.g., stock levels, item details, restock dates, warehouse locations, product categories).
                6. Do not make assumptions or provide unverified information.
                7. Present information in a user-friendly and professional tone.
                8. If a calculation is needed (e.g., total value of items), show the steps clearly.
                9. Keep responses free from personal opinions, unless specifically asked for recommendations.
                10. If the information is unavailable, respond with: “I couldn’t find that information in the inventory records.”

                Example interactions:
                - User: “How many units of Product A are in stock?”  
                Agent: “Product A currently has 320 units available in Warehouse 1.”
                - User: “Do we have any size L t-shirts in blue?”  
                Agent: “Yes, we have 45 size L blue t-shirts in stock.”
                - User: “When will Product X be restocked?”  
                Agent: “Product X is expected to be restocked on September 15, 2025.”'''
            
            agent = Agent(
                name="Inventory Management Assistant",
                model="gpt-3.5-turbo",# additional
                instructions=instructions,
                #tools=[mcp_server],
                mcp_server=[mcp_server],
                model_settings=ModelSettings(
                    tool_choice="required",
                ),
            )
            result = await Runner.run(starting_agent = agent, input=question)
            return result.final_output
  
    finally:
        await mcp_server.__aexit__(None, None, None)
        process.terminate()
        
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return """
    <form action="/ask" method="post">
        <input name="question" placeholder="Ask your inventory AI">
        <button type="submit">Ask</button>
    </form>
    """

@app.post("/ask", response_class=HTMLResponse)
async def ask(request: Request, question: str = Form(...)):
    answer = await ask_agent(question)
    return f"<p><strong>Question:</strong> {question}</p><p><strong>Answer:</strong> {answer}</p>"
