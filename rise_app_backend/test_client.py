from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key="")

resp = client.responses.create(
    model="gpt-4o",
    tool_choice="required",
    tools=[{
        "type": "mcp",
        "server_label": "django-mcp-server",
        "server_url": "https://814ab68a7305.ngrok-free.app/sse",  # note the /sse
        "require_approval": "never",
        
    }],
    input="can i get inventory movements?",
)

print(resp.output_text)