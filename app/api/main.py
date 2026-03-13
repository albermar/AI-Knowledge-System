print("main: before fastapi import", flush=True)
from fastapi import FastAPI
print("main: fastapi imported", flush=True)

print("main: before router 1 import")
from app.api import router_1_ingest_document
print("main: router 1 imported", flush=True)

print("main: before router 2 import")
from app.api import router_2_add_organization
print("main: router 2 imported", flush=True)

print("main: before router 3 import")
from app.api import router_3_ask_question
print("main: router 3 imported", flush=True)

print("main: before router 4 import")
from app.api import router_4_dashboard
print("main: router 4 imported", flush=True)

app = FastAPI(title="AI Knowledge System API", version="1.0")

@app.get("/")
def root():
    return {"status": "ok"}

'''
app.include_router(router_1_ingest_document.router, prefix = "/api", tags = ["ingest_document"])
app.include_router(router_2_add_organization.router, prefix = "/api", tags = ["new_organization"])
app.include_router(router_3_ask_question.router, prefix = "/api", tags = ["ask_question"])
app.include_router(router_4_dashboard.router, prefix="/api", tags=["dashboard"])

'''