from fastapi import FastAPI
from .router import products
from .router import alerts
from .database.db import engine, SQLModel

# Create tables on startup
SQLModel.metadata.create_all(engine)
\

app = FastAPI()

app.include_router(products.router,prefix="/api/v1")
app.include_router(alerts.router,prefix="/api/v1")
