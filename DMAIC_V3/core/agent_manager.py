"""DMAIC 3.4 Agent Management System.

Discovers the established 12-agent population and provides a bounded execution
contract. Discovery may report missing agents but never creates source files.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from ..config import VERSION
__version__ = VERSION

@dataclass
class AgentConfig:
    name: str
    category: str
    version: str
    path: Path
    enabled: bool = True
    config: Optional[Dict[str, Any]] = None
    def __post_init__(self):
        if self.config is None: self.config = {}

class AgentManager:
    """Manage the 12-agent architecture without establishing engineering authority."""
    def __init__(self, workspace_root: Path, output_root: Path):
        self.workspace_root=Path(workspace_root); self.output_root=Path(output_root); self.agents={}
        self.agent_architecture={"analysis":["cryo_dm","document_consumer","artifact_analyzer","smoke_test"],"documentation":["framework","style_extractor"],"recursive":["self_ranking","iteration_tracker"],"knowledge":["context_manager","dependency_graph"],"monitoring":["health_checker","performance_tracker"]}
    def initialize_all_agents(self)->Dict[str,Any]:
        status={}
        for category,names in self.agent_architecture.items():
            status[category]={}
            for name in names:
                agent=self._initialize_agent(category,name); self.agents[f"{category}_{name}"]=agent
                status[category][name]={"available":agent.enabled,"version":agent.version,"path":str(agent.path)}
        self._save_agent_registry(); return status
    def _initialize_agent(self,category:str,agent_name:str)->AgentConfig:
        patterns=[f"{category}_{agent_name}_v2.3_OPTIMIZED.py",f"{agent_name}_v2.3_OPTIMIZED.py",f"{category}_{agent_name}_OPTIMIZED.py",f"{agent_name}_OPTIMIZED.py"]
        candidates=[self.workspace_root/"local_mcp"/"agents"/p for p in patterns]
        path=next((p for p in candidates if p.exists()),candidates[0]); enabled=path.exists()
        return AgentConfig(agent_name,category,"2.3.0" if enabled else "missing",path,enabled,self._load_agent_config(category,agent_name))
    def _load_agent_config(self,category:str,agent_name:str)->Dict[str,Any]:
        path=self.workspace_root/"config"/"agents"/f"{category}_{agent_name}.json"
        if path.exists():
            with path.open("r",encoding="utf-8") as handle: return json.load(handle)
        return {}
    def _save_agent_registry(self)->None:
        path=self.output_root/"agent_registry.json"; path.parent.mkdir(parents=True,exist_ok=True)
        registry={"version":__version__,"authority":"ANALYTICAL_RUNTIME_ONLY","agents":{k:{"name":a.name,"category":a.category,"version":a.version,"enabled":a.enabled,"path":str(a.path)} for k,a in sorted(self.agents.items())}}
        path.write_text(json.dumps(registry,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    def get_agents_for_phase(self,phase_name:str)->List[AgentConfig]:
        mapping={"phase1_define":["analysis.cryo_dm","analysis.document_consumer"],"phase2_measure":["analysis.artifact_analyzer","monitoring.performance_tracker"],"phase3_analyze":["analysis.smoke_test","recursive.self_ranking"],"phase4_improve":["documentation.framework","documentation.style_extractor"],"phase5_control":["monitoring.health_checker","recursive.iteration_tracker"],"phase6_knowledge":["knowledge.context_manager","knowledge.dependency_graph"]}
        out=[]
        for key in mapping.get(phase_name,[]):
            category,name=key.split("."); agent=self.agents.get(f"{category}_{name}")
            if agent is not None: out.append(agent)
        return out
    @staticmethod
    def _receipt_digest(receipt:Dict[str,Any])->str:
        return hashlib.sha256(json.dumps(receipt,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()).hexdigest()
    def execute_callable(self,agent_key:str,runner:Callable[[Dict[str,Any]],Any],payload:Dict[str,Any])->Dict[str,Any]:
        if agent_key not in self.agents: raise KeyError(f"unknown agent: {agent_key}")
        agent=self.agents[agent_key]
        if not agent.enabled: raise RuntimeError(f"agent disabled or missing: {agent_key}")
        try: result,status,error=runner(payload),"success",None
        except Exception as exc: result,status,error=None,"failed",f"{type(exc).__name__}: {exc}"
        receipt={"agent":agent_key,"agent_version":agent.version,"status":status,"result":result,"error":error,"authority":"ANALYTICAL_FINDING_ONLY"}
        receipt["sha256"]=self._receipt_digest(receipt); return receipt
    def orchestrate_phase(self,phase_name:str,phase_data:Dict[str,Any])->Dict[str,Any]:
        """Compatibility readiness view; actual execution requires execute_callable()."""
        agents=self.get_agents_for_phase(phase_name)
        results={a.name:{"status":"ready" if a.enabled else "skipped","version":a.version,"reason":None if a.enabled else "disabled or missing"} for a in agents}
        return {"agents_executed":0,"agents_ready":sum(1 for r in results.values() if r["status"]=="ready"),"results":results,"authority":"ANALYTICAL_RUNTIME_ONLY"}
