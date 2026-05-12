import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.api import analysis, match, predict, score, strategy


load_dotenv()


def get_cors_origins() -> list[str]:
    origins = os.getenv("CORS_ORIGINS", "")
    return [origin.strip() for origin in origins.split(",") if origin.strip()]


app = FastAPI(title=os.getenv("APP_NAME", "Subscription Strategy API"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(score.router, prefix="/score", tags=["score"])
app.include_router(predict.router, prefix="/predict", tags=["prediction"])
app.include_router(match.router, prefix="/match", tags=["matching"])
app.include_router(strategy.router, prefix="/strategy", tags=["strategy"])
app.include_router(analysis.router, prefix="/analysis", tags=["analysis"])


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
