from fastapi import FastAPI
from mangum import Mangum
from api.router import *
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title="Perp connect - partial backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Declare Routers
app.include_router(tokens.router)

handler = Mangum(app=app)
