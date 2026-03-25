from fastapi import FastAPI

app = FastAPI(title="CareCaller API")


@app.get("/health")
async def health():
    return {"status": "ok"}
