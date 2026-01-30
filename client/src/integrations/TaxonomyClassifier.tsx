import { useState, useMemo, useEffect, useCallback } from 'react';
import { 
    Trash2, ChevronDown, Loader2, CheckCircle2, Search, Tag, Copy, 
    Check, ArrowRight, MapPin, RefreshCw, ClipboardCopy, FileText 
} from 'lucide-react';
import { taxonomyAPI, type DefectCandidate } from '../api/taxonomyAPI'; 

export default function TaxonomyClassifier() {
  const [remark, setRemark] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  
  // State
  const [selectedPath, setSelectedPath] = useState<string[]>([]);
  const [selectedDefectType, setSelectedDefectType] = useState<string>("");
  const [aiDefectCandidates, setAiDefectCandidates] = useState<DefectCandidate[]>([]);
  
  const [treeData, setTreeData] = useState<any>({});
  const [isTreeLoading, setIsTreeLoading] = useState(true);
  
  // Track which button currently shows "Copied!"
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // 1. Load Tree
  useEffect(() => {
    const loadTree = async () => {
      try {
        const data = await taxonomyAPI.getTree();
        setTreeData(data);
      } catch (e) {
        console.error(e);
      } finally {
        setIsTreeLoading(false);
      }
    };
    loadTree();
  }, []);

  // 2. Derive Data
  const availableDefects = useMemo(() => {
    if (selectedPath.length === 0) return [];
    let node = treeData;
    for (const step of selectedPath) {
      if (node && node[step]) node = node[step];
      else return [];
    }
    return node["__defects__"] || []; 
  }, [selectedPath, treeData]);

  // Derive the SPASS code for the CURRENT leaf node (last selected path)
  const currentSpassCode = useMemo(() => {
    if (selectedPath.length === 0) return null;
    let node = treeData;
    for (const step of selectedPath) {
      if (node && node[step]) node = node[step];
      else return null;
    }
    return node["__spass_code__"];
  }, [selectedPath, treeData]);

  // Full Formatted String Logic (Remark | Path | Defect)
  const getFormattedString = () => {
    return `${remark} | ${selectedPath.join(" > ")} | ${selectedDefectType}`;
 };

  // 3. Reset or Validate Defect
  useEffect(() => {
    if (selectedDefectType && availableDefects.length > 0) {
        const isValid = availableDefects.includes(selectedDefectType);
        if (!isValid) setSelectedDefectType(""); 
    }
  }, [selectedPath, availableDefects, selectedDefectType]);

  // Analysis Logic
  const runAnalysis = useCallback(async (constraintPath: string | undefined) => {
    if (!remark.trim()) return;
    setIsLoading(true);
    setAiDefectCandidates([]); 
    setSelectedDefectType("");
    setCopiedId(null);
    
    try {
      const data = await taxonomyAPI.analyze(remark, constraintPath); 
      setSelectedPath(data.path_list);
      setAiDefectCandidates(data.defect_candidates);
      if (data.defect_candidates.length > 0) {
        setSelectedDefectType(data.defect_candidates[0].label);
      }
    } catch (e) {
      console.error(e);
      alert("Error analyzing text.");
    } finally {
      setIsLoading(false);
    }
  }, [remark]);

  const handleAnalyze = () => runAnalysis(undefined);

  const handleReEvaluate = (levelIndex: number) => {
      const partialPath = selectedPath.slice(0, levelIndex + 1);
      const constraintString = partialPath.join(" > ");
      runAnalysis(constraintString);
  };

  const handleLevelChange = (levelIndex: number, newValue: string) => {
    const newPath = selectedPath.slice(0, levelIndex);
    if (newValue !== "") newPath.push(newValue);
    setSelectedPath(newPath);
  };

  const handleDeleteLevel = (levelIndex: number) => {
    const newPath = selectedPath.slice(0, levelIndex);
    setSelectedPath(newPath);
  };

  const handleNextRemark = () => {
    setRemark("");
    setSelectedPath([]);
    setAiDefectCandidates([]);
    setSelectedDefectType("");
    setCopiedId(null);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Generalized Copy Handler
  const handleCopy = (text: string, id: string) => {
    if (!text) return;
    navigator.clipboard.writeText(text).then(() => {
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    });
  };

  // --- Render Helpers ---
  const renderDropdowns = useMemo(() => {
    const dropdowns: any[] = [];
    
    const getOptions = (n: any) => 
      n ? Object.keys(n).filter(k => !["__defects__", "__spass_code__"].includes(k)).sort() : [];

    if (Object.keys(treeData).length === 0) return [];

    let currentNode: any = treeData;

    selectedPath.forEach((selection, index) => {
      dropdowns.push({
        level: index,
        value: selection,
        options: getOptions(currentNode),
        node: currentNode 
      });

      if (currentNode && currentNode[selection]) {
        currentNode = currentNode[selection];
      } else {
        currentNode = {};
      }
    });

    const nextOptions = getOptions(currentNode);
    if (nextOptions.length > 0) {
      dropdowns.push({
        level: selectedPath.length,
        value: "",
        options: nextOptions,
        node: currentNode 
      });
    }
    return dropdowns;
  }, [selectedPath, treeData]);

  // Reusable Copy Button for the Sidebar
  const SidebarButton = ({ label, value, id, icon: Icon, disabled = false }: any) => {
    const isSuccess = copiedId === id;
    
    // Use the full string if available, otherwise show the code/label
    const displayValue = (id === 'copy-full-result') ? "Full String" : (value || "Wait for input...");
    
    return (
        <div className="space-y-1">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                {label}
            </span>
            <button
                onClick={() => handleCopy(value, id)}
                disabled={disabled || !value}
                className={`w-full flex items-center justify-between p-3 rounded-lg border transition-all duration-200 group
                    ${disabled || !value 
                        ? 'bg-slate-50 border-slate-200 text-slate-300 cursor-not-allowed' 
                        : isSuccess
                            ? 'bg-green-50 border-green-200 text-green-700'
                            : 'bg-white border-slate-200 text-slate-600 hover:border-black hover:shadow-sm'
                    }
                `}
            >
                <div className="flex items-center gap-2 overflow-hidden">
                    <Icon className={`w-4 h-4 shrink-0 ${!disabled && value && !isSuccess ? 'group-hover:text-black' : ''}`} />
                    <span className="truncate text-sm font-medium">
                        {isSuccess ? "Copied!" : (value || "Wait for input...")}
                    </span>
                </div>
                {isSuccess ? <Check className="w-4 h-4 shrink-0" /> : <Copy className="w-4 h-4 shrink-0 opacity-50 group-hover:opacity-100" />}
            </button>
        </div>
    );
  };

  return (
    <div className="min-h-screen bg-slate-50 p-8 font-sans text-slate-800">
      <div className="max-w-5xl mx-auto bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden flex flex-col">
        
        {/* Header */}
        <div className="bg-black p-6 text-white flex items-center gap-3">
            <Search className="w-6 h-6 text-gray-300" />
            <div>
                <h1 className="text-xl font-bold">AI Defect Classifier</h1>
                <p className="text-gray-400 text-sm opacity-90">Mercedes-Benz — Made by MBMC</p>
            </div>
        </div>

        {/* Main Content Area (Two-Column Split) */}
        <div className="flex flex-col lg:flex-row">
            
            {/* LEFT COLUMN: Controls & Input (Flex-1) */}
            <div className="flex-1 p-6 space-y-8 lg:border-r border-slate-100">
                
                {/* 1. Remark Input */}
                <div className="space-y-3">
                    <label className="block text-sm font-semibold text-slate-700 uppercase tracking-wider">Defect Remark</label>
                    <div className="relative">
                        <textarea
                            value={remark}
                            onChange={(e) => setRemark(e.target.value)}
                            placeholder="e.g., Deep scratch on the front left door panel..."
                            className="w-full p-4 rounded-lg border border-slate-300 focus:ring-2 focus:ring-black outline-none h-32 resize-none"
                        />
                        <button
                            onClick={handleAnalyze}
                            disabled={isLoading || !remark || isTreeLoading}
                            className={`absolute bottom-3 right-3 px-4 py-2 rounded-md text-sm font-medium flex items-center gap-2
                            ${isLoading || !remark || isTreeLoading ? 'bg-slate-100 text-slate-400' : 'bg-black text-white hover:bg-gray-800'}`}
                        >
                            {isLoading && <Loader2 className="w-4 h-4 animate-spin" />}
                            {isLoading ? 'Analyzing...' : 'Analyze'}
                        </button>
                    </div>
                </div>

                {/* 2. Path & Defect Selection (Only show if path exists) */}
                {(selectedPath.length > 0) && (
                    <div className="space-y-6 bg-slate-50 p-6 rounded-xl border border-slate-200">
                        
                        <div className="space-y-3 pb-6 border-b border-slate-200">
                            <div className="text-xs font-bold text-slate-400 uppercase flex items-center gap-2">
                                <MapPin className="w-3 h-3" />
                                Defect Location
                            </div>
                            
                            {/* Dropdown Rendering with SPASS Code Prefix */}
                            {renderDropdowns.map((item, i) => (
                                <div key={item.level} className="flex items-start gap-3 relative">
                                    {i !== renderDropdowns.length - 1 && (
                                        <div className="absolute left-4 top-10 bottom-[-12px] w-0.5 bg-slate-200"></div>
                                    )}
                                    <div className={`w-8 h-8 shrink-0 rounded-full flex items-center justify-center z-10 ${item.value ? 'bg-black text-white' : 'bg-slate-200 text-slate-400'}`}>
                                        {item.value ? <CheckCircle2 className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                                    </div>
                                    <div className="flex-1 flex gap-2">
                                        <select
                                            value={item.value}
                                            onChange={(e) => handleLevelChange(item.level, e.target.value)}
                                            className="block w-full rounded-md border-0 py-2.5 pl-3 pr-10 ring-1 ring-inset ring-slate-300 focus:ring-2 focus:ring-black sm:text-sm sm:leading-6 bg-white shadow-sm"
                                        >
                                            <option value="" disabled>{item.value ? "Select option..." : "Select location..."}</option>
                                            {item.options.map((opt: string) => {
                                                const spassCode = item.node[opt]?.["__spass_code__"];
                                                // Retains the requested [SPASS_CODE] Category Name format
                                                const label = spassCode ? `[${spassCode}] ${opt}` : opt;
                                                return <option key={opt} value={opt}>{label}</option>;
                                            })}
                                        </select>
                                        
                                        {item.value && (
                                            <button onClick={() => handleDeleteLevel(item.level)} className="p-2.5 text-slate-400 hover:text-red-500 transition-colors">
                                                <Trash2 className="w-4 h-4" />
                                            </button>
                                        )}

                                        {item.value && item.options.length > 0 && (
                                            <button 
                                                onClick={() => handleReEvaluate(item.level)}
                                                disabled={isLoading}
                                                title="Re-classify from here"
                                                className={`p-2.5 rounded-md border transition-colors ${isLoading ? 'text-slate-400' : 'text-blue-500 hover:bg-blue-50'}`}
                                            >
                                                <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
                                            </button>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>

                        {/* Defect Type */}
                        <div className="space-y-3">
                            <div className="text-xs font-bold text-slate-400 uppercase flex items-center gap-2">
                                <Tag className="w-3 h-3" />
                                Defect Type
                            </div>
                            <div className="flex items-start gap-3">
                                <div className={`w-8 h-8 shrink-0 rounded-full flex items-center justify-center z-10 ${selectedDefectType ? 'bg-black text-white' : 'bg-slate-200 text-slate-400'}`}>
                                    <Tag className="w-4 h-4" />
                                </div>
                                <div className="flex-1">
                                    <select
                                        value={selectedDefectType}
                                        onChange={(e) => setSelectedDefectType(e.target.value)}
                                        className="block w-full rounded-md border-0 py-2.5 pl-3 pr-10 ring-1 ring-inset ring-slate-300 focus:ring-2 focus:ring-black sm:text-sm sm:leading-6 bg-white shadow-sm"
                                        disabled={availableDefects.length === 0} 
                                    >
                                        <option value="" disabled>
                                            {availableDefects.length === 0 ? "No defects defined for this location" : "Select defect type..."}
                                        </option>

                                        {aiDefectCandidates.length > 0 && aiDefectCandidates.every(c => availableDefects.includes(c.label)) && (
                                            <optgroup label="AI Recommendation">
                                                {aiDefectCandidates.map((cand) => (
                                                    <option key={cand.label} value={cand.label}>
                                                        {cand.label} ({Math.round(cand.score * 100)}%)
                                                    </option>
                                                ))}
                                            </optgroup>
                                        )}

                                        {availableDefects.length > 0 && (
                                            <optgroup label="All Valid Types">
                                                {availableDefects.map(d => (
                                                    <option key={d} value={d}>{d}</option>
                                                ))}
                                            </optgroup>
                                        )}
                                    </select>
                                </div>
                            </div>
                        </div>

                    </div>
                )}
            </div>

            {/* RIGHT COLUMN: Sidebar Actions */}
            <div className="bg-white w-full lg:w-72 p-6 border-t lg:border-t-0 lg:border-l border-slate-200 flex flex-col gap-6">
                
                {true && (
                    <div className="space-y-6">
                        <div className="mb-2">
                            <h3 className="font-bold text-slate-800">Copy Data Workflow</h3>
                            <p className="text-xs text-slate-500">Steps to transfer results to the system.</p>
                        </div>

                        {/* Step 1: SPASS Code */}
                        <SidebarButton 
                            label="1. SPASS Code" 
                            value={currentSpassCode} 
                            id="copy-spass"
                            icon={ClipboardCopy}
                            disabled={!currentSpassCode}
                        />

                        {/* Step 2: Defect Place (Only Leaf Node) */}
                        <SidebarButton 
                            label="2. Defect Place" 
                            // CHANGE: selectedPath[selectedPath.length - 1] gets only the leaf
                            value={selectedPath.length > 0 ? selectedPath[selectedPath.length - 1] : ""} 
                            id="copy-place"
                            icon={MapPin}
                            disabled={selectedPath.length === 0}
                        />

                        {/* Step 3: Defect Type Name */}
                        <SidebarButton 
                            label="3. Defect Type Name" 
                            value={selectedDefectType} 
                            id="copy-defect"
                            icon={Tag}
                            disabled={!selectedDefectType}
                        />

                        {/* Step 4: Full Formatted String (Remark | Path | Defect) */}
                        <SidebarButton 
                            label="4. Full Result String" 
                            value={getFormattedString()} 
                            id="copy-full-result"
                            icon={FileText} 
                        />
                    </div>
                )}

                <div className="flex-1"></div>
                
                <button 
                    onClick={handleNextRemark} 
                    className="w-full bg-black hover:bg-gray-800 text-white px-4 py-3 rounded-lg font-medium shadow-sm flex items-center justify-center gap-2 transition-transform active:scale-95 mt-auto"
                >
                    <span>Next Remark</span>
                    <ArrowRight className="w-4 h-4" />
                </button>

            </div>
        </div>

      </div>
    </div>
  );
}