import os
import json
import pickle
import numpy as np
import openai
from typing import List, Dict, Union

# --- CONFIGURATION ---
AZURE_CONFIG = {
    "api_key": os.getenv("API_KEY"),
    "api_version": "2025-03-01-preview",
    "azure_endpoint": os.getenv("AZURE_ENDPOINT"),
    "deployment_chat": "gpt-4o",
    "deployment_embed": "text-embedding-3-large"
}

# Ensure environment variables are set externally for security in production
os.environ["AZURE_TENANT_ID"] = os.getenv("AZURE_TENANT_ID") 

class VariableDepthClassifier:
    def __init__(self, tree_path, cache_path):
        # Initialize Azure Client
        self.client = openai.AzureOpenAI(
            api_key=AZURE_CONFIG["api_key"],
            api_version=AZURE_CONFIG["api_version"],
            azure_endpoint=AZURE_CONFIG["azure_endpoint"]
        )
        
        # Initialize the map for path -> defects
        self.defects_map: Dict[str, List[str]] = {} 
        
        # 1. Load & Flatten Tree
        if not os.path.exists(tree_path):
            print(f"ERROR: {tree_path} not found. Classifier cannot start.")
            self.paths = []
            self.vectors = None
            return

        # Populates self.paths AND self.defects_map
        self.paths = self._flatten_tree_all_levels(tree_path)
        print(f"Tree loaded: {len(self.paths)} categories.")
        
        # 2. Load or Build Vectors (NumPy Matrix)
        self.vectors = self._load_or_build_vectors(self.paths, cache_path)

    def _flatten_tree_all_levels(self, path) -> List[str]:
        """
        Parses the nested JSON tree into a flat list of strings (paths).
        Also populates self.defects_map with the '__defects__' lists.
        """
        with open(path, 'r', encoding='utf-8') as f:
            tree = json.load(f)
        
        flat_paths = set()
        
        def recurse(node, current_path_str):
            # 1. Check for Defects at this level
            if isinstance(node, dict) and "__defects__" in node:
                # Store the defects for this specific path
                self.defects_map[current_path_str] = node["__defects__"]
            
            # 2. Add path to set (if not empty root)
            if current_path_str:
                flat_paths.add(current_path_str)

            # 3. Recurse children
            if isinstance(node, dict):
                for key, child_node in node.items():
                    if key in ["__defects__", "__spass_code__"]:
                        continue
                        
                    new_path = f"{current_path_str} > {key}" if current_path_str else key
                    recurse(child_node, new_path)

        recurse(tree, "")
        return sorted(list(flat_paths))

    def _load_or_build_vectors(self, paths, cache_path) -> np.ndarray:
        """Loads vectors from pickle or calls Azure to embed and saves."""
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'rb') as f:
                    vectors = pickle.load(f)
                if len(vectors) == len(paths):
                    print("Loaded embeddings from cache.")
                    return vectors
                else:
                    print("Cache mismatch (tree changed). Rebuilding...")
            except Exception as e:
                print(f"Cache load error: {e}. Rebuilding...")
        
        print("Embedding tree (one-time operation)...")
        vectors = self._embed_all(paths)
        
        # NORMALIZE vectors
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1
        vectors = vectors / norms
        
        with open(cache_path, 'wb') as f:
            pickle.dump(vectors, f)
            
        return vectors

    def _embed_all(self, text_list):
        """Batched embedding of the entire list."""
        vectors = []
        batch_size = 100 
        
        for i in range(0, len(text_list), batch_size):
            batch = text_list[i : i + batch_size]
            try:
                resp = self.client.embeddings.create(input=batch, model=AZURE_CONFIG["deployment_embed"])
                vecs = [d.embedding for d in resp.data]
                vectors.append(vecs)
            except Exception as e:
                print(f"Embed Error at batch {i}: {e}")
                vectors.append(np.zeros((len(batch), 3072)))
                
        return np.vstack(vectors).astype(np.float32)

    # --- HELPER: CHECK IF PATH HAS DEFECTS ---
    def _has_defects(self, path: str) -> bool:
        """Returns True if the path has a non-empty list of defects associated."""
        return path in self.defects_map and len(self.defects_map[path]) > 0

    def classify(self, remark: str, top_k: int = 20) -> str:
        """Classifies the remark against only paths that have associated defects."""
        
        # FILTER: Only select paths that have defects
        valid_indices = [i for i, p in enumerate(self.paths) if self._has_defects(p)]
        
        if not valid_indices:
            return "ERROR_NO_DEFECT_PATHS"

        # Subset vectors and paths
        subset_vectors = self.vectors[valid_indices]
        candidates_subset = [self.paths[i] for i in valid_indices]

        return self._run_classification(remark, candidates_subset, subset_vectors, top_k)
    
    def classify_restricted(self, remark: str, allowed_paths: List[str], top_k: int = 20) -> str:
        """
        Classifies the remark against allowed_paths, but strictly filters out
        any allowed_path that does not have associated defects.
        """
        
        if not allowed_paths:
            return "ERROR_NO_PATHS"

        # --- 1. Identify and Validate Constraint Path ---
        constraint_path = ""
        if allowed_paths:
            path_segments = [p.split(" > ") for p in allowed_paths]
            first_segments = path_segments[0]
            for i in range(len(first_segments)):
                temp_path = " > ".join(first_segments[:len(first_segments) - i])
                is_ancestor = all(p.startswith(temp_path) for p in allowed_paths)
                if is_ancestor:
                    constraint_path = temp_path
                    break
        
        # Calculate Ancestors (paths that must NOT be returned)
        ancestor_segments = constraint_path.split(" > ")[:-1]
        ancestor_paths = [" > ".join(ancestor_segments[:i+1]) for i in range(len(ancestor_segments))]
        
        # 2. Add constraint path IF it has defects (Fix for "higher level" logic)
        # We only add the parent if it is a valid defect place itself.
        if constraint_path and constraint_path not in allowed_paths:
            if self._has_defects(constraint_path):
                allowed_paths.append(constraint_path)

        # --- 3. Vector Search with Strict Defect Filtering ---
        # Map global paths to indices
        path_to_index = {p: i for i, p in enumerate(self.paths)}
        
        # Only include paths that exist AND have defects
        valid_indices = [
            path_to_index[p] for p in allowed_paths 
            if p in path_to_index and self._has_defects(p)
        ]
        
        if not valid_indices:
            # If even the constraint path has no defects, and no children have defects, we can't classify.
            print("Restricted search: No allowed paths have associated defects.")
            return "NONE" # Or handle as error
        
        subset_vectors = self.vectors[valid_indices]
        candidates_subset = [self.paths[i] for i in valid_indices]

        # Run core classification
        result_path = self._run_classification(remark, candidates_subset, subset_vectors, top_k)

        # --- 4. Constraint Check and Fallback ---
        
        # A. Check for Ancestor Violation
        if result_path in ancestor_paths:
            # If reranker picked an invalid ancestor, fallback to constraint ONLY if it has defects
            if self._has_defects(constraint_path):
                print(f"Reranker violated constraint. Forcing result to: {constraint_path}")
                return constraint_path
            return "NONE"
            
        # B. Check for Failed Search
        if result_path == "NONE":
            # Fallback to constraint path ONLY if it has defects
            if self._has_defects(constraint_path):
                print(f"Restricted classification failed to find a fit. Falling back to: {constraint_path}")
                return constraint_path
            return "NONE"
            
        return result_path

    def _run_classification_old(self, remark: str, candidate_paths: List[str], candidate_vectors: np.ndarray, top_k: int = 20) -> str:
        """Core classification logic."""
        if candidate_vectors is None or len(candidate_vectors) == 0:
            return "ERROR_NO_INDEX"

        search_term = remark.lower().strip() 

        # 1. Embed User Remark
        try:
            resp = self.client.embeddings.create(input=search_term, model=AZURE_CONFIG["deployment_embed"])
            query_vec = np.array(resp.data[0].embedding, dtype=np.float32)
            
            norm = np.linalg.norm(query_vec)
            if norm > 0:
                query_vec = query_vec / norm
        except Exception as e:
            print(f"Embedding API Error: {e}")
            return "ERROR_EMBED"

        # 2. Vector Search
        scores = candidate_vectors @ query_vec
        k = min(top_k, len(scores))
        top_indices = np.argsort(scores)[::-1][:k]

        final_candidates = [candidate_paths[i] for i in top_indices]

        if not final_candidates:
            return "UNCLASSIFIED"
        
        # 3. Rerank with GPT
        return self._ask_gpt_best_fit(remark, final_candidates)
    
    def _run_classification(self, remark: str, candidate_paths: List[str], candidate_vectors: np.ndarray, top_k: int = 20) -> str:
        """Core classification logic shared between full and restricted search."""
        if candidate_vectors is None or len(candidate_vectors) == 0:
            return "ERROR_NO_INDEX"

        # --- FIX: Context Augmentation (The "Soft" Fix) ---
        # Instead of replacing text, we append the definition.
        # This biases the embedding vector towards "Left" if "Driver" is mentioned,
        # regardless of how the user spells "driver".
        search_context = f"{remark} (Context: Driver Side or d/s is Left, Passenger Side is Right)"
        
        # 1. Embed the Augmented Context
        try:
            # We embed 'search_context', not just 'remark'
            resp = self.client.embeddings.create(input=search_context, model=AZURE_CONFIG["deployment_embed"])
            query_vec = np.array(resp.data[0].embedding, dtype=np.float32)
            
            # Normalize query vector
            norm = np.linalg.norm(query_vec)
            if norm > 0:
                query_vec = query_vec / norm
        except Exception as e:
            print(f"Embedding API Error: {e}")
            return "ERROR_EMBED"

        # 2. Vector Search (Dot Product)
        scores = candidate_vectors @ query_vec
        
        k = min(top_k, len(scores))
        top_indices = np.argsort(scores)[::-1][:k]

        final_candidates = [candidate_paths[i] for i in top_indices]

        if not final_candidates:
            return "UNCLASSIFIED"
        
        # 3. Rerank with GPT
        # We pass the original remark to GPT, but we give it a strict rule in the prompt below.
        return self._ask_gpt_best_fit(remark, final_candidates)

    def _ask_gpt_best_fit(self, remark, candidates):
        cand_list_str = "\n".join([f"- {c}" for c in candidates])
        
        # --- UPDATED PROMPT: STRICTER RULES ---
        system = (
            "You are a strict classification assistant. Your Goal: Map the Remark to the most accurate category from the Candidates list below.\n"
            "Rules:\n"
            "1. You must strictly choose one of the provided candidates.\n"
            "2. Do NOT output a parent path or a path not listed in the Candidates.\n"
            "3. Only reply 'NONE' if the remark is completely unrelated (e.g., spam, wrong language).\n"
            "4. Output EXACTLY the category path string, nothing else."
        )
        user = f"Remark: \"{remark}\"\nCandidates:\n{cand_list_str}\nBest Fit:"

        try:
            resp = self.client.chat.completions.create(
                model=AZURE_CONFIG["deployment_chat"],
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.0
            )
            choice = resp.choices[0].message.content.strip().replace("'", "").replace('"', "")
            
            if choice in self.paths:
                return choice
            
            for c in candidates:
                if choice.lower() == c.lower():
                    return c
            
            return "VAN SSL defect places"
        except Exception as e:
            print(f"GPT Error: {e}")
            return "ERROR_GPT"
            
    def get_all_unique_defects(self) -> List[str]:
        unique_defects = set()
        for defects_list in self.defects_map.values():
            unique_defects.update(defects_list)
        return sorted(list(unique_defects))