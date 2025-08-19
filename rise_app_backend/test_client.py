from dotenv import load_dotenv
from openai import OpenAI
load_dotenv()
client = OpenAI() 


url = 'https://f59d5dc9a634.ngrok-free.app/mcp/'


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
    input="hi",
)

print(resp.output_text)