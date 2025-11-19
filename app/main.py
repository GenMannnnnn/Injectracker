from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from .deps import init_db
from .routers.auth import router as auth_router
from .routers.vendors import router as vendors_router
from .routers.products import router as products_router
from .utils import UPLOAD_DIR

BUILD_VERSION = "V2.2.0"

app = FastAPI(title="ERP Mobile API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True
)

app.include_router(auth_router)
app.include_router(vendors_router)
app.include_router(products_router)

@app.on_event("startup")
def on_startup():
    init_db()
    os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/__version")
def version():
    return {"build": BUILD_VERSION}

# serve product photos
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# serve SPA
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(os.path.dirname(BASE_DIR), "static_site")
if not os.path.isdir(STATIC_DIR):
    os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

@app.get("/")
def root():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))
