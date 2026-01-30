from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

router = APIRouter()

# 1. UPDATED Request Model to include optional constraint path
class AnalysisRequest(BaseModel):
    remark: str
    constraint_path: Optional[str] = None  # New field for "Re-evaluate"

# --- Shared Models (Kept as before) ---
class DefectCandidate(BaseModel):
    label: str
    score: float

class AnalysisResponse(BaseModel):
    path_list: List[str]
    full_path_str: str
    defect_candidates: List[DefectCandidate]

# --- Endpoints ---

@router.get("/tree")
async def get_taxonomy_tree(request: Request) -> Dict[str, Any]:
    """Retrieves the full taxonomy tree structure for frontend dropdown rendering."""
    return getattr(request.app.state, "tree_data", {})

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_remark(
    request: Request, 
    body: AnalysisRequest
):
    """
    Analyzes the remark to determine the location and then the defect type, 
    optionally constraining the location search space.
    """
    # Get Classifiers
    tree_clf = getattr(request.app.state, "tree_classifier", None)
    defect_clf = getattr(request.app.state, "defect_classifier", None)
    
    if not tree_clf or not defect_clf:
        # Check both are initialized as both are required for full functionality
        raise HTTPException(status_code=503, detail="Classifiers not initialized.")

    # --- 1. CLASSIFY PATH (Location) ---
    
    # 1a. Determine the classification method based on the request
    if body.constraint_path:
        # User manually corrected the path (e.g., "Car > Interior"). 
        # Find all valid paths under this constraint.
        print(f"Running restricted classification. Constraint: {body.constraint_path}")
        
        # Filter all known paths to only those starting with the constraint
        all_paths = tree_clf.paths
        allowed_paths = [p for p in all_paths if p.startswith(body.constraint_path)]
        
        # Run restricted search
        full_path_str = tree_clf.classify_restricted(body.remark, allowed_paths)
    else:
        # Standard full search
        full_path_str = tree_clf.classify(body.remark)
    
    # --- 2. HANDLE PATH RESULT ---
    
    # Check if the classification was successful
    if full_path_str in ["NONE", "UNCLASSIFIED", "ERROR_EMBED", "ERROR_GPT", "ERROR_NO_INDEX", "ERROR_NO_PATHS"]:
         path_list = []
         full_path_str = ""
         allowed_defects = []
         print(f"Path classification failed with: {full_path_str}")
    else:
        path_list = [p.strip() for p in full_path_str.split(">")]
        
        # 3. CONTEXTUAL DEFECT LOOKUP (New Logic)
        # Use the final path string to get the list of allowed defects for the defect classifier
        allowed_defects = tree_clf.defects_map.get(full_path_str, [])
        
        if not allowed_defects:
            print(f"WARNING: No '__defects__' found for path: {full_path_str}. Using empty list.")

    # --- 4. CLASSIFY DEFECT TYPE ---
    defect_candidates: List[DefectCandidate] = []
    
    if allowed_defects:
        # Run contextual prediction using the filtered list
        defect_candidates = defect_clf.predict(body.remark, allowed_defects, top_k=20)
    
    return {
        "path_list": path_list,
        "full_path_str": full_path_str,
        "defect_candidates": defect_candidates
    }