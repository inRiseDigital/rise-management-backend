import requests


res=requests.get("http://127.0.0.1:8000/stores/add_stores/")

res=res.json()

print(res)