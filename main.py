from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import contextlib
from database import engine
from routers import orders


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(
    title="Sallijang Order Service",
    description="Microservice for managing pickup reservations and orders.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.sallijang.shop"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(orders.router)


@app.get("/")
def read_root():
    return {"message": "Welcome to Sallijang Order Service API! Go to http://localhost:8002/docs to test endpoints."}


@app.get("/health")
def health():
    return {"status": "ok"}
