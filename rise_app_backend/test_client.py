from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key="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")

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