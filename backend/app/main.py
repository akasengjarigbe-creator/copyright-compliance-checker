from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router


app = FastAPI(
    title="Copyright Compliance Checker API",
    version="1.0.0",
)


allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(
    router,
    prefix="/api",
)


@app.get("/")
def root():
    return {
        "message": (
            "Copyright Compliance Checker API is running."
        )
    }