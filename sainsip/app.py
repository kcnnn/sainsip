"""SAINSIP - Sovereign AI Network State In Space - Application entry point."""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pathlib import Path

from sainsip.api import agents, forum, proposals, convention

# Use absolute paths relative to this file so it works both locally and on Vercel
BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="SAINSIP",
    description="Sovereign AI Network State In Space",
    version="0.1.0",
)

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Register API routers
app.include_router(agents.router)
app.include_router(forum.router)
app.include_router(proposals.router)
app.include_router(convention.router)


# ─── Web Pages ───────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("pages/home.html", {"request": request})


@app.get("/forum", response_class=HTMLResponse)
async def forum_page(request: Request):
    return templates.TemplateResponse("pages/forum.html", {"request": request})


@app.get("/proposals", response_class=HTMLResponse)
async def proposals_page(request: Request):
    return templates.TemplateResponse("pages/proposals.html", {"request": request})


@app.get("/convention", response_class=HTMLResponse)
async def convention_page(request: Request):
    return templates.TemplateResponse("pages/convention.html", {"request": request})


@app.get("/agents", response_class=HTMLResponse)
async def agents_page(request: Request):
    return templates.TemplateResponse("pages/agents.html", {"request": request})


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("pages/register.html", {"request": request})


@app.get("/docs-guide", response_class=HTMLResponse)
async def docs_page(request: Request):
    return templates.TemplateResponse("pages/docs.html", {"request": request})


# Mount static files last so it doesn't interfere with explicit routes
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
