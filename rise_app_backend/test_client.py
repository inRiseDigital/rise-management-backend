from dotenv import load_dotenv
from openai import OpenAI
load_dotenv()
client = OpenAI() 


url = 'https://410837ae44c0.ngrok-free.app/mcp'


client = OpenAI(api_key="")


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