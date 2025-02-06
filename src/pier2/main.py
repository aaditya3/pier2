from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "All you touch and all you see is all your life will ever be."}