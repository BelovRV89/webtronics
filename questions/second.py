from fastapi import FastAPI
from urllib.parse import quote_plus

app = FastAPI()

@app.get("/encode_url/")
async def encode_url(url: str):
    encoded_url = quote_plus(url)
    return {"encoded_url": encoded_url}