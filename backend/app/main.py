from fastapi import FastAPI
from app.api.routes import router

app = FastAPI(
    title="Copyright Attribution and Licence Compliance Checker",
    version="0.1.0",
    description="Rule-based MVP for analysing image attribution and licence compliance in student webpages."
)

app.include_router(router, prefix="/api")

@app.get("/")
def health_check():
    return {"status": "ok", "message": "Copyright Compliance Checker API is running"}
