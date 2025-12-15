from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.api.routes import router

app = FastAPI(title="ModelGuard AI", version="1.0")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Include the routes from the API folder
app.include_router(router, prefix="/api")

@app.get("/")
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})