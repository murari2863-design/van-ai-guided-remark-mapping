import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from server.config.config import Settings, load_settings
from server.routes import helloworld, taxonomy  # <--- 1. Import taxonomy
from server.classes.classifier import VariableDepthClassifier # <--- 2. Import Service
from server.classes.flat_classifier import FlatClassifier 
from server.classes.flat_classifier import ContextualDefectClassifier # <--- Use the new class

'''
ToDos:
- Frontend passwortabfrage
- Hello-World beispiel angleichen -> nicht über request.app.state.tree_data sondern mit Depends oder funktionsaufruf
'''

app = FastAPI(
    title="AI Guided Data Entry",
    description="Template for a cloudfoundry deployed full stack web app that uses React and FastAPI",
    version="0.1.0",
    swagger_ui_use_local_assets=True,
    redoc_use_local_assets=True,
)

settings: Settings = load_settings()

origins = [
    "https://localhost:5000",
    "https://127.0.0.1:5000",
    "http://localhost:5000",
    "http://127.0.0.1:5000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # List of allowed origins
    allow_credentials=True,  # Allow cookies and other credentials
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers
)


"""@app.on_event("startup")
async def startup_event():
    print("Loading Taxonomy Classifier & Tree...")
    
    # 1. Define paths (Assuming running from root)
    tree_path = "shrunken_tree.txt" 
    cache_path = "tree_embeddings_all_levels.pkl"
    
    if not os.path.exists(tree_path):
        print(f"WARNING: {tree_path} not found!")
        app.state.tree_data = {}
    else:
        # 2. Load raw tree for Frontend Dropdowns
        with open(tree_path, 'r', encoding='utf-8') as f:
            app.state.tree_data = json.load(f)
            
        # 3. Load Classifier for AI Logic
        app.state.classifier = VariableDepthClassifier(tree_path, cache_path)
        
    print("Startup complete.")
"""

@app.on_event("startup")
async def startup_event():
    print("Loading Contextual Classifiers...")
    
    # Tree Paths
    tree_path = "shrunken_tree.json" 
    tree_cache = "tree_embeddings_all_levels.pkl"
    
    # Defect Type Cache (No longer needs the separate text file)
    defect_cache = "defect_types_master_embeddings.pkl" # Renamed cache for clarity

    # Load Tree Data (for UI dropdowns)
    if os.path.exists(tree_path):
        with open(tree_path, 'r', encoding='utf-8') as f:
            app.state.tree_data = json.load(f)
    else:
        app.state.tree_data = {}

    # 1. Load Tree Classifier (This extracts all paths AND defects into its state)
    app.state.tree_classifier = VariableDepthClassifier(tree_path, tree_cache)
    
    # 2. Extract ALL unique defects from the loaded tree
    all_defects = app.state.tree_classifier.get_all_unique_defects()
    
    # 3. Initialize Contextual Defect Classifier with the Master List
    app.state.defect_classifier = ContextualDefectClassifier(all_defects, defect_cache)
        
    print("Startup complete.")
"""
@app.on_event("startup")
async def startup_event():
    print("Loading Classifiers...")
    
    # Tree Paths
    tree_path = "shrunken_tree.txt" 
    tree_cache = "tree_embeddings_all_levels.pkl"
    
    # Defect Type Paths
    defect_path = "defect_types.txt"
    defect_cache = "defect_types_embeddings.pkl"

    # Load Tree Data (for UI dropdowns)
    if os.path.exists(tree_path):
        with open(tree_path, 'r', encoding='utf-8') as f:
            app.state.tree_data = json.load(f)
    else:
        app.state.tree_data = {}

    # Load Classifiers
    app.state.tree_classifier = VariableDepthClassifier(tree_path, tree_cache)
    
    # 2. Initialize Flat Classifier
    app.state.defect_classifier = FlatClassifier(defect_path, defect_cache)
        
    print("Startup complete.")"""

@app.get("/health")
async def health_check():
    '''
    A simple health check endpoint.
    '''
    return {"status": "ok"}


app.include_router(helloworld.router)
app.include_router(taxonomy.router, prefix="/api") 


# We deploy a FastAPI server that serves static client files
# Therefore we don't need to set up a client serving application
# The client will be built before pushing to cloudfoundry and is included in the push

# Serve client
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(BASE_DIR, "..", "client", "dist")
INDEX_HTML_FILE = os.path.join(DIST_DIR, "index.html")

app.mount(
    "/assets",
    StaticFiles(directory=os.path.join(DIST_DIR, "assets")),
    name="vite-assets",
)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse(os.path.join(DIST_DIR, "favicon.ico"))


@app.get("/logo192.png", include_in_schema=False)
async def logo192():
    return FileResponse(os.path.join(DIST_DIR, "logo192.png"))


@app.get("/logo512.png", include_in_schema=False)
async def logo512():
    return FileResponse(os.path.join(DIST_DIR, "logo512.png"))


@app.get("/manifest.json", include_in_schema=False)
async def manifest():
    return FileResponse(os.path.join(DIST_DIR, "manifest.json"))


@app.get("/robots.txt", include_in_schema=False)
async def robots():
    return FileResponse(os.path.join(DIST_DIR, "robots.txt"))


@app.get("/", include_in_schema=False)
async def serve_root_index():
    if not os.path.exists(INDEX_HTML_FILE):
        raise HTTPException(status_code=404, detail="SPA index.html not found.")
    return FileResponse(INDEX_HTML_FILE)


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa_host(full_path: str):
    # Do not hijack FastAPI's docs/static paths
    if full_path.startswith(("docs", "redoc", "openapi.json", "static")):
        raise HTTPException(status_code=404, detail="Not found")
    if not os.path.exists(INDEX_HTML_FILE):
        raise HTTPException(
            status_code=404,
            detail="SPA index.html not found. Did you build the client?",
        )
    return FileResponse(INDEX_HTML_FILE)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", getattr(settings, "port", 8000)))
    uvicorn.run("server.main:app", host="0.0.0.0", port=port, reload=True)
