from mangum import Mangum
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.router import *
from api.router.trader import trader_route

app = FastAPI(title="Perp connect - partial backend", openapi_prefix="/main")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Declare Routers
app.include_router(tokens.router)
app.include_router(trader_route, prefix="/trader")

handler = Mangum(app=app)
