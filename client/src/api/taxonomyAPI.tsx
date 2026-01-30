import { apiURL } from "../data/settings";
import { parseJSON } from "./utils";

const cleanBase = apiURL.replace(/\/+$/, "");

// Helper to build URLs cleanly
const getEndpoint = (path: string) => 
  cleanBase.endsWith("/api") ? `${cleanBase}/${path}` : `${cleanBase}/api/${path}`;

export interface DefectCandidate {
  label: string;
  score: number;
}

export interface TaxonomyResponse {
  path_list: string[];
  full_path_str: string;
  defect_candidates: DefectCandidate[]; 
}

// 1. Define the type for the request body payload
interface AnalyzePayload {
    remark: string;
    constraint_path?: string; // Optional constraint for re-evaluation
}

const taxonomyAPI = {
  // Fetch the full tree structure
  getTree(): Promise<any> {
    const url = getEndpoint("tree");
    return fetch(url, { method: "GET" })
      .then(parseJSON)
      .catch((error) => {
        console.error("Tree Fetch Error:", error);
        throw error;
      });
  },

  // 2. Updated analyze signature to accept optional constraintPath
  analyze(remark: string, constraintPath?: string): Promise<TaxonomyResponse> {
    const url = getEndpoint("analyze");
    
    // 3. Construct the payload
    const payload: AnalyzePayload = { remark };
    if (constraintPath) {
        payload.constraint_path = constraintPath;
    }

    const options: RequestInit = {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      // 4. Stringify the dynamically built payload
      body: JSON.stringify(payload), 
      credentials: "include",
    };
        
    return fetch(url, options)
      .then(parseJSON)
      .catch((error) => {
        console.error("Taxonomy API Error:", error);
        throw error;
      });
  },
};

export { taxonomyAPI };