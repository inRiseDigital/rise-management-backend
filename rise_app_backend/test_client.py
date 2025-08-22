from dotenv import load_dotenv
from openai import OpenAI
load_dotenv()
client = OpenAI() 


url = 'https://410837ae44c0.ngrok-free.app/mcp'


client = OpenAI(api_key="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")


resp = client.responses.create(
    model="gpt-4.1",
    tools=[
        {
            "type": "mcp",
            "server_label": "mcp_server",
            "server_url": f"{url}",
            "require_approval": "never",
        },
    ],
    input="what can you do?",
)

print(resp.output_text)