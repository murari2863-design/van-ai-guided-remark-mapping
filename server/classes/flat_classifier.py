import os
import pickle
import numpy as np
import openai
from typing import List, Dict

# Load config from env in real app
AZURE_CONFIG = {
    "api_key": os.getenv("API_KEY"),
    "api_version": "2025-03-01-preview",
    "azure_endpoint": os.getenv("AZURE_ENDPOINT"),
    "deployment_chat": "gpt-4o",
    "deployment_embed": "text-embedding-3-large"
}

os.environ["AZURE_TENANT_ID"] = os.getenv("AZURE_TENANT_ID")


class ContextualDefectClassifier:
    def __init__(self, all_unique_defects: List[str], cache_path: str):
        self.client = openai.AzureOpenAI(
            api_key=AZURE_CONFIG["api_key"],
            api_version=AZURE_CONFIG["api_version"],
            azure_endpoint=AZURE_CONFIG["azure_endpoint"]
        )
        
        # Master Index of all possible defects
        self.master_categories = sorted(list(set(all_unique_defects)))
        print(f"Defect Classifier: Loaded {len(self.master_categories)} unique defect types.")

        # Map label -> Index in the master matrix (for fast lookup)
        self.label_to_index = {label: i for i, label in enumerate(self.master_categories)}

        # Build Global Vectors (The Master Index)
        self.master_vectors = self._load_or_build_vectors(self.master_categories, cache_path)

    def _load_or_build_vectors(self, categories, cache_path):
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'rb') as f:
                    data = pickle.load(f)
                if len(data) == len(categories):
                    print("Loaded defect embeddings from cache.")
                    return data
            except:
                print("Defect cache error. Rebuilding...")
                pass 
        
        print("Embedding defect types (Master Index)...")
        vectors = self._embed_batch(categories)
        
        # Normalize vectors
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1
        vectors = vectors / norms
        
        with open(cache_path, 'wb') as f:
            pickle.dump(vectors, f)
        return vectors

    def _embed_batch(self, text_list):
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
                print(f"Embed Error: {e}")
                vectors.append(np.zeros((len(batch), 3072)))
        return np.vstack(vectors).astype(np.float32)

    def predict(self, remark: str, allowed_defects: List[str], top_k: int = 5) -> List[Dict]:
        """
        Predicts defect by performing a search strictly against 'allowed_defects'.
        """
        if self.master_vectors is None or not allowed_defects: 
            return []

        # 1. Identify indices for the allowed subset
        valid_indices = []
        valid_labels = []
        for d in allowed_defects:
            if d in self.label_to_index:
                valid_indices.append(self.label_to_index[d])
                valid_labels.append(d)
        
        if not valid_indices:
            return []

        # 2. Embed Query
        try:
            resp = self.client.embeddings.create(input=remark, model=AZURE_CONFIG["deployment_embed"])
            q_vec = np.array(resp.data[0].embedding, dtype=np.float32)
            norm = np.linalg.norm(q_vec)
            if norm > 0: q_vec = q_vec / norm
        except Exception as e:
            print(f"Embedding API Error: {e}")
            return []

        # 3. MASKED Vector Search
        # Slice the master matrix to only include allowed rows
        subset_vectors = self.master_vectors[valid_indices]
        
        scores = subset_vectors @ q_vec
        
        # Sort results
        top_k = min(top_k, len(scores))
        top_local_indices = np.argsort(scores)[::-1][:top_k]
        
        candidates = []
        for local_idx in top_local_indices:
            candidates.append({
                "label": valid_labels[local_idx],
                "score": float(scores[local_idx])
            })
            
        # 4. GPT Reranking
        best_label = self._rerank_with_gpt(remark, [c['label'] for c in candidates])
        
        if best_label and best_label != "NONE":
            # Reorder list: Put winner first
            candidates.sort(key=lambda x: x['label'] == best_label, reverse=True)
            # Boost score of winner visually for the frontend
            if candidates[0]['label'] == best_label:
                candidates[0]['score'] = max(candidates[0]['score'], 0.99)

        return candidates[:10]

    def _rerank_with_gpt(self, remark, candidate_labels):
        cand_str = "\n".join([f"- {c}" for c in candidate_labels])
        system = "You are a QA expert. Pick the SINGLE best defect category from the list. If the remark is vague, pick the most likely one based on automotive context. Return ONLY the category name."
        user = f"Remark: \"{remark}\"\nCandidates:\n{cand_str}\nBest Category:"
        
        try:
            resp = self.client.chat.completions.create(
                model=AZURE_CONFIG["deployment_chat"],
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.0
            )
            choice = resp.choices[0].message.content.strip().replace("'", "").replace('"', "")
            
            if choice in candidate_labels: return choice
            for c in candidate_labels:
                if choice.lower() == c.lower(): return c
            return "NONE"
        except Exception as e:
            print(f"GPT Rerank Error: {e}")
            return "ERROR_GPT"

class FlatClassifier:
    def __init__(self, file_path, cache_path):
        self.client = openai.AzureOpenAI(
            api_key=AZURE_CONFIG["api_key"],
            api_version=AZURE_CONFIG["api_version"],
            azure_endpoint=AZURE_CONFIG["azure_endpoint"]
        )
        
        # 1. Load Categories
        if not os.path.exists(file_path):
            print(f"WARNING: {file_path} not found.")
            self.categories = []
            self.vectors = None
            return

        with open(file_path, 'r', encoding='utf-8') as f:
            self.categories = [line.strip() for line in f.readlines() if line.strip()]
            
        print(f"Flat Classifier: Loaded {len(self.categories)} types.")

        # 2. Build/Load Vectors
        self.vectors = self._load_or_build_vectors(self.categories, cache_path)

    def _load_or_build_vectors(self, categories, cache_path):
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'rb') as f:
                    data = pickle.load(f)
                if len(data) == len(categories):
                    return data
            except:
                pass 
        
        print("Embedding defect types...")
        vectors = self._embed_batch(categories)
        
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1
        vectors = vectors / norms
        
        with open(cache_path, 'wb') as f:
            pickle.dump(vectors, f)
        return vectors

    def _embed_batch(self, text_list):
        vectors = []
        batch_size = 100
        for i in range(0, len(text_list), batch_size):
            batch = text_list[i : i + batch_size]
            try:
                resp = self.client.embeddings.create(input=batch, model=AZURE_CONFIG["deployment_embed"])
                vecs = [d.embedding for d in resp.data]
                vectors.append(vecs)
            except Exception as e:
                print(f"Embed Error: {e}")
                vectors.append(np.zeros((len(batch), 3072)))
        return np.vstack(vectors).astype(np.float32)

    def predict(self, remark: str, top_k: int = 20) -> List[Dict]: # Increased k for better context
        """
        1. Semantic Search (Top K)
        2. GPT Rerank (Pick Winner)
        """
        if self.vectors is None: return []

        # 1. Vector Search
        try:
            resp = self.client.embeddings.create(input=remark, model=AZURE_CONFIG["deployment_embed"])
            q_vec = np.array(resp.data[0].embedding, dtype=np.float32)
            norm = np.linalg.norm(q_vec)
            if norm > 0: q_vec = q_vec / norm
        except:
            return []

        scores = self.vectors @ q_vec
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        candidates = []
        for i in top_indices:
            candidates.append({
                "label": self.categories[i],
                "score": float(scores[i])
            })
            
        # 2. GPT Reranking
        # We ask GPT to pick the best fit from the candidates.
        # We then move that winner to the top of the list with a boosted score.
        best_label = self._rerank_with_gpt(remark, [c['label'] for c in candidates])
        
        if best_label and best_label != "NONE":
            # Reorder list: Put winner first
            candidates.sort(key=lambda x: x['label'] == best_label, reverse=True)
            # Boost score of winner visually
            if candidates[0]['label'] == best_label:
                candidates[0]['score'] = 0.99

        return candidates

    def _rerank_with_gpt(self, remark, candidate_labels):
        cand_str = "\n".join([f"- {c}" for c in candidate_labels])
        system = "You are a QA expert. Pick the SINGLE best defect category from the list. If the remark is vague, pick the most likely one based on automotive context. Return ONLY the category name."
        user = f"Remark: \"{remark}\"\nCandidates:\n{cand_str}\nBest Category:"
        
        try:
            resp = self.client.chat.completions.create(
                model=AZURE_CONFIG["deployment_chat"],
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.0
            )
            choice = resp.choices[0].message.content.strip().replace("'", "").replace('"', "")
            
            if choice in candidate_labels: return choice
            for c in candidate_labels:
                if choice.lower() == c.lower(): return c
            return None
        except:
            return None