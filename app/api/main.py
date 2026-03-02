from fastapi import FastAPI, HTTPException, Depends
from app.api import router_1_ingest_document

app = FastAPI(title = "AI Knowledge System API", version = 1.0)

app.include_router(router_1_ingest_document.router, prefix = "/api", tags = ["ingest_document"])
 
