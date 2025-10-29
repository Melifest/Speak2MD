from fastapi import FastAPI

app = FastAPI(title="Speak2MD API", version="0.1.0")

@app.get("/")
async def root():
    return {"message": "Speak2MD API is running!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}