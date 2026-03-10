from fastapi import FastAPI, HTTPException, Depends
from app.api import router_1_ingest_document, router_3_ask_question, router_2_add_organization

app = FastAPI(title = "AI Knowledge System API", version = "1.0")

app.include_router(router_1_ingest_document.router, prefix = "/api", tags = ["ingest_document"])
app.include_router(router_2_add_organization.router, prefix = "/api", tags = ["new_organization"])
app.include_router(router_3_ask_question.router, prefix = "/api", tags = ["ask_question"])


#uvicorn launch is: 