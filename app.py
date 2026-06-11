from __future__ import annotations

import os
import asyncio
import difflib
import concurrent.futures
from functools import lru_cache
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import httpx
import networkx as nx

from streaming_client import fetch_repository_archive
from graph_engine import build_dependency_graph, get_impacted_files
from parser import extract_functions, find_functions_using_symbol, extract_api_routes

app = FastAPI(title="Diff-Guard Risk Engine")

# Fetch token from environment variable
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# ---------------------------------------------------------------------------
# Custom Exceptions
# ---------------------------------------------------------------------------

class RepoBuildError(Exception):
    """Raised when the dependency graph cannot be built from the fetched archive."""
    pass

class RateLimitError(Exception):
    """Raised when GitHub returns 403/429 indicating API rate limiting."""
    pass

class UnsupportedRepoError(Exception):
    """Raised when the repository URL is invalid or unsupported."""
    pass

# ---------------------------------------------------------------------------
# SHA-keyed LRU Cache for Repository Fetching
# ---------------------------------------------------------------------------

@lru_cache(maxsize=50)
def _cached_fetch(owner: str, repo: str, sha: str, token: str | None) -> dict:
    """
    Thin LRU-cached wrapper around fetch_repository_archive.
    Since commit SHAs are immutable, caching by (owner, repo, sha, token)
    is safe and avoids redundant downloads of the same snapshot.
    """
    return fetch_repository_archive(owner, repo, sha, token)

# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

def get_changed_line_numbers(base_code: bytes, head_code: bytes) -> tuple[set[int], set[int]]:
    """
    Returns (base_changed_lines, head_changed_lines) as 1-indexed line numbers
    by computing a diff between the two file contents.
    """
    base_lines = base_code.decode("utf-8", errors="replace").splitlines()
    head_lines = head_code.decode("utf-8", errors="replace").splitlines()
    
    sm = difflib.SequenceMatcher(None, base_lines, head_lines)
    base_changed = set()
    head_changed = set()
    
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("replace", "delete"):
            for idx in range(i1, i2):
                base_changed.add(idx + 1)
        if tag in ("replace", "insert"):
            for idx in range(j1, j2):
                head_changed.add(idx + 1)
                
    return base_changed, head_changed

# ---------------------------------------------------------------------------
# Multi-Factor Risk Score
# ---------------------------------------------------------------------------

def compute_risk_score(
    graph: nx.DiGraph,
    modified_files: list,
    modified_functions_by_file: dict,
    all_impacted_files: set,
    impacted_apis: list
) -> int:
    """
    Computes an architectural risk score (0-100) across four weighted factors:
      1. Betweenness centrality of modified files → 0–40 pts
      2. Blast radius breadth                     → 0–30 pts
      3. Public API endpoints hit                 → 0–20 pts
      4. Deleted functions count                  → 0–10 pts
    
    Returns a dict with 'total' and individual factor breakdowns.
    """
    # 1. Betweenness centrality (how central the modified files are in the graph)
    centrality = nx.betweenness_centrality(graph) if len(graph) > 0 else {}
    centrality_sum = sum(centrality.get(f, 0) for f in modified_files)
    centrality_pts = min(int(centrality_sum * 200), 40)
    
    # 2. Blast radius breadth
    blast_pts = min(len(all_impacted_files) * 3, 30)
    
    # 3. Public API endpoints hit
    api_pts = min(len(impacted_apis) * 10, 20)
    
    # 4. Deleted functions
    deletion_count = 0
    for funcs in modified_functions_by_file.values():
        for _, change_type in funcs:
            if change_type in ("deleted", "file_deleted"):
                deletion_count += 1
    deletion_pts = min(deletion_count * 5, 10)
    
    total = min(centrality_pts + blast_pts + api_pts + deletion_pts, 100)
    
    return {
        "total": total,
        "centrality_pts": centrality_pts,
        "blast_pts": blast_pts,
        "api_pts": api_pts,
        "deletion_pts": deletion_pts,
        "deletion_count": deletion_count,
    }


def _build_summary_text(
    risk_score: int,
    breakdown: dict,
    modified_files: list,
    modified_functions_by_file: dict,
    all_impacted_files: set,
    at_risk_functions: dict,
    impacted_apis: list,
) -> str:
    """
    Builds a detailed, human-readable summary paragraph explaining the risk
    score, the contributing factors, and actionable next steps.
    """
    if risk_score == 0:
        return (
            "No architectural risk detected. The modified files are isolated leaf "
            "nodes with zero downstream consumers in the dependency graph. No "
            "functions, modules, or public API endpoints are affected by this change. "
            "This diff is safe to merge with minimal review."
        )

    # Count total modified and at-risk functions
    total_modified_funcs = sum(len(v) for v in modified_functions_by_file.values())
    total_at_risk_funcs = sum(len(v) for v in at_risk_functions.values())

    # Opening sentence based on severity tier
    if risk_score >= 80:
        opening = (
            f"Critical architectural risk detected (score: {risk_score}/100). "
            f"This change touches core infrastructure that is deeply interconnected "
            f"within the codebase."
        )
    elif risk_score >= 50:
        opening = (
            f"High architectural risk detected (score: {risk_score}/100). "
            f"The modified code is centrally positioned in the dependency graph "
            f"and has a wide downstream impact."
        )
    elif risk_score >= 20:
        opening = (
            f"Moderate architectural risk detected (score: {risk_score}/100). "
            f"While the change is not to core infrastructure, it ripples into "
            f"several downstream consumers that should be verified."
        )
    else:
        opening = (
            f"Low architectural risk detected (score: {risk_score}/100). "
            f"The modified files have limited connectivity in the dependency graph, "
            f"but a small number of downstream modules are still affected."
        )

    # Impact details
    impact_detail = (
        f" {len(modified_files)} file(s) containing {total_modified_funcs} "
        f"semantic entities (functions/methods) were modified, impacting "
        f"{len(all_impacted_files)} downstream module(s) through transitive "
        f"dependency chains."
    )

    # At-risk functions detail
    risk_detail = ""
    if total_at_risk_funcs > 0:
        risk_detail = (
            f" {total_at_risk_funcs} function(s) in direct consumer files "
            f"actively reference the modified symbols and are at risk of "
            f"behavioral regression."
        )

    # API impact detail
    api_detail = ""
    if impacted_apis:
        api_detail = (
            f" {len(impacted_apis)} public API endpoint(s) are in the blast "
            f"radius — these are user-facing routes that may exhibit changed "
            f"behavior or break client contracts."
        )

    # Score breakdown sentence
    factor_parts = []
    if breakdown["centrality_pts"] > 0:
        factor_parts.append(f"graph centrality (+{breakdown['centrality_pts']})")
    if breakdown["blast_pts"] > 0:
        factor_parts.append(f"blast radius breadth (+{breakdown['blast_pts']})")
    if breakdown["api_pts"] > 0:
        factor_parts.append(f"API surface exposure (+{breakdown['api_pts']})")
    if breakdown["deletion_pts"] > 0:
        factor_parts.append(
            f"deleted functions ({breakdown['deletion_count']} removed, "
            f"+{breakdown['deletion_pts']})"
        )
    breakdown_sentence = ""
    if factor_parts:
        breakdown_sentence = (
            f" Score contributors: {', '.join(factor_parts)}."
        )

    # Recommendation
    if risk_score >= 50:
        recommendation = (
            " A senior engineer review is strongly recommended. Run the full "
            "regression test suite and validate all impacted API contracts "
            "before merging."
        )
    elif risk_score >= 20:
        recommendation = (
            " Ensure integration tests cover the affected downstream modules. "
            "Review the dependency paths to confirm no unintended side effects."
        )
    else:
        recommendation = (
            " Standard code review is sufficient. Spot-check the listed "
            "downstream consumers for any unexpected behavioral changes."
        )

    return (
        opening + impact_detail + risk_detail + api_detail
        + breakdown_sentence + recommendation
    )

# ---------------------------------------------------------------------------
# Unified Analysis Pipeline
# ---------------------------------------------------------------------------

def run_analysis_pipeline(base_files: dict, head_files: dict) -> dict:
    """
    Core analysis pipeline shared by both the webhook handler and the API endpoint.
    
    Takes two file snapshots (base and head) and returns a dict containing:
      graph, modified_files, modified_functions_by_file, all_impacted_files,
      impact_paths, at_risk_functions, impacted_apis, risk_score, status, summary_text
    """
    # Build dependency graph from the base state
    graph = build_dependency_graph(base_files)
    
    # Compare base and head files to locate structural changes
    modified_files = []
    modified_functions_by_file = {}
    
    for file_path, base_code in base_files.items():
        if file_path not in head_files:
            # File deleted completely
            modified_files.append(file_path)
            modified_functions_by_file[file_path] = [("All", "file_deleted")]
        else:
            head_code = head_files[file_path]
            if base_code != head_code:
                # Ingest code and extract function boundary definitions
                base_funcs = extract_functions(base_code, file_path=file_path)
                head_funcs = extract_functions(head_code, file_path=file_path)
                
                # Calculate exact line changes between base and head
                base_changed, head_changed = get_changed_line_numbers(base_code, head_code)
                
                changed_funcs = []
                
                # Check for modified or deleted functions based on coordinate intersections
                for f_name, (start_b, end_b) in base_funcs.items():
                    if f_name not in head_funcs:
                        changed_funcs.append((f_name, "deleted"))
                    else:
                        # Intersection: Did any of the changed base lines fall within this function?
                        # We check both base and head coordinates.
                        start_h, end_h = head_funcs[f_name]
                        
                        b_intersect = any(line in base_changed for line in range(start_b, end_b + 1))
                        h_intersect = any(line in head_changed for line in range(start_h, end_h + 1))
                        
                        if b_intersect or h_intersect:
                            changed_funcs.append((f_name, "modified"))
                            
                # Check for newly added functions
                for f_name, (start_h, end_h) in head_funcs.items():
                    if f_name not in base_funcs:
                        changed_funcs.append((f_name, "added"))
                        
                if changed_funcs:
                    modified_files.append(file_path)
                    modified_functions_by_file[file_path] = changed_funcs
                    
    # Trace impacted modules upward via DiGraph BFS
    all_impacted_files = set()
    impact_paths = {}
    at_risk_functions = {}
    
    for m_file in modified_files:
        impacted = get_impacted_files(graph, m_file)
        all_impacted_files.update(impacted)
        
        paths_dict = {}
        for imp_file in impacted:
            try:
                path = nx.shortest_path(graph, source=m_file, target=imp_file)
                paths_dict[imp_file] = path
            except nx.NetworkXNoPath:
                paths_dict[imp_file] = [m_file, imp_file]
        impact_paths[m_file] = paths_dict
        
    # Identify AT RISK functions in direct consumers
    for m_file in modified_files:
        changed_entities = modified_functions_by_file.get(m_file, [])
        for imp_file, path in impact_paths.get(m_file, {}).items():
            if len(path) == 2:  # Direct consumer
                # Scan the consumer for usage of the modified symbols
                code_bytes = head_files.get(imp_file)
                if code_bytes:
                    for c_func_name, c_type in changed_entities:
                        if c_type in ("modified", "deleted"):
                            found_funcs = find_functions_using_symbol(code_bytes, c_func_name, file_path=imp_file)
                            if found_funcs:
                                if imp_file not in at_risk_functions:
                                    at_risk_functions[imp_file] = []
                                at_risk_functions[imp_file].extend(found_funcs)
                                
    # Dedup at_risk_functions
    for k in at_risk_functions:
        at_risk_functions[k] = list(dict.fromkeys(at_risk_functions[k]))
        
    # Scan for impacted API routes
    all_api_routes = {}
    for f_path, h_code in head_files.items():
        routes = extract_api_routes(h_code, file_path=f_path)
        for f_name, r_info in routes.items():
            all_api_routes[(f_path, f_name)] = r_info
            
    impacted_apis = []
    for imp_file, funcs in at_risk_functions.items():
        for f in funcs:
            if (imp_file, f) in all_api_routes:
                route_info = all_api_routes[(imp_file, f)]
                impacted_apis.append({
                    "file": imp_file,
                    "function": f,
                    "method": route_info["method"],
                    "path": route_info["path"]
                })
    
    # Compute multi-factor risk score
    score_breakdown = compute_risk_score(
        graph, modified_files, modified_functions_by_file,
        all_impacted_files, impacted_apis
    )
    risk_score = score_breakdown["total"]
    
    if risk_score >= 50:
        status = "HIGH RISK"
    elif risk_score > 0:
        status = "MEDIUM RISK"
    else:
        status = "LOW RISK"
        
    # Generate detailed human-readable summary
    summary_text = _build_summary_text(
        risk_score, score_breakdown, modified_files,
        modified_functions_by_file, all_impacted_files,
        at_risk_functions, impacted_apis
    )
    
    return {
        "graph": graph,
        "modified_files": modified_files,
        "modified_functions_by_file": modified_functions_by_file,
        "all_impacted_files": all_impacted_files,
        "impact_paths": impact_paths,
        "at_risk_functions": at_risk_functions,
        "impacted_apis": impacted_apis,
        "risk_score": risk_score,
        "status": status,
        "summary_text": summary_text,
    }

# ---------------------------------------------------------------------------
# Webhook Background Worker
# ---------------------------------------------------------------------------

def analyze_diff_and_report(payload: dict):
    """
    Background worker that runs the full Diff-Guard pipeline:
    1. Downloads base & head commit snapshots.
    2. Runs the unified analysis pipeline.
    3. Formats and dispatches a markdown report to the PR thread.
    """
    try:
        pull_number = payload["pull_request"]["number"]
        base_sha = payload["pull_request"]["base"]["sha"]
        head_sha = payload["pull_request"]["head"]["sha"]
        
        repo_info = payload["repository"]
        owner = repo_info["owner"]["login"]
        repo_name = repo_info["name"]
        
        print(f"\n[Diff-Guard] Analyzing PR #{pull_number} ({base_sha} -> {head_sha})")
        
        # Fetch archive states concurrently using ThreadPoolExecutor
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_base = executor.submit(_cached_fetch, owner, repo_name, base_sha, GITHUB_TOKEN)
            future_head = executor.submit(_cached_fetch, owner, repo_name, head_sha, GITHUB_TOKEN)
            
            base_files = future_base.result()
            head_files = future_head.result()
        
        # Run unified analysis pipeline
        result = run_analysis_pipeline(base_files, head_files)
        
        # Format and Dispatch feedback
        report_md = format_markdown_report(
            pull_number,
            result["modified_files"],
            result["modified_functions_by_file"],
            result["all_impacted_files"],
            result["impact_paths"],
            result["at_risk_functions"],
            result["impacted_apis"],
            result["risk_score"],
        )
        
        print("\n--- Generated Architectural Risk Report ---")
        print(report_md)
        print("-------------------------------------------\n")
        
        if GITHUB_TOKEN:
            post_comment_to_github(owner, repo_name, pull_number, report_md)
        else:
            print("[Diff-Guard] GITHUB_TOKEN not configured. Skipping GitHub comment dispatch.")
            
    except Exception as e:
        print(f"[Diff-Guard] Error during PR analysis: {e}")

# ---------------------------------------------------------------------------
# Markdown Report Formatter
# ---------------------------------------------------------------------------

def format_markdown_report(
    pull_number: int,
    modified_files: list,
    modified_functions_by_file: dict,
    all_impacted_files: set,
    impact_paths: dict,
    at_risk_functions: dict,
    impacted_apis: list,
    risk_score: int = None,
    graph: nx.DiGraph = None,
) -> str:
    """
    Constructs a structured GitHub Markdown report with a Risk Score.
    Accepts a pre-computed risk_score. If not provided, falls back to the
    legacy formula for backward compatibility with cli.py.
    """
    if risk_score is None:
        # Legacy fallback for callers that don't pass risk_score
        risk_score = min(len(all_impacted_files) * 10, 100)
    
    if risk_score >= 50:
        status = "🔴 HIGH RISK"
    elif risk_score > 0:
        status = "🟡 MEDIUM RISK"
    else:
        status = "🟢 LOW RISK"
        
    md = f"## 🛡️ Diff-Guard Architectural Risk Report\n\n"
    md += f"**PR:** #{pull_number} | **Status:** {status} | **Risk Score:** {risk_score}/100\n\n"
    
    md += "### 🔍 Modified Semantic Entities\n"
    if not modified_files:
        md += "_No supported code modifications detected._\n"
    else:
        md += "| File | Entity | Change Type |\n"
        md += "| --- | --- | --- |\n"
        for m_file in modified_files:
            for f_name, change_type in modified_functions_by_file.get(m_file, []):
                md += f"| `{m_file}` | `{f_name}()` | {change_type.upper()} |\n"
                
    md += "\n### 🕸️ Architectural Blast Radius\n"
    if not all_impacted_files:
        md += "🟢 _No downstream modules are affected by these changes._\n"
    else:
        md += f"⚠️ **{len(all_impacted_files)} downstream files** are directly or transitively affected:\n\n"
        md += "| Modified File | Impacted Downstream Files (Dependency Path) |\n"
        md += "| --- | --- |\n"
        for m_file, paths_dict in impact_paths.items():
            if paths_dict:
                for imp_file, path in paths_dict.items():
                    path_str = " ➔ ".join(f"`{f}`" for f in path)
                    md += f"| `{m_file}` | {path_str} |\n"
            else:
                md += f"| `{m_file}` | _None (Terminal module)_ |\n"
                
    if at_risk_functions:
        md += "\n### 🔍 Downstream Functions at Risk\n"
        md += "The following specific functions in direct consumer files rely on the modified symbols and may be at risk:\n\n"
        md += "| Consumer File | At-Risk Functions |\n"
        md += "| --- | --- |\n"
        for imp_file, funcs in at_risk_functions.items():
            funcs_str = ", ".join(f"`{f}()`" for f in funcs)
            md += f"| `{imp_file}` | {funcs_str} |\n"
            
    if impacted_apis:
        md += "\n### 🚨 Impacted Public Entrypoints (QA Action Required)\n"
        md += "The following HTTP APIs and CLI commands are in the blast radius of this change:\n\n"
        md += "| Consumer File | Entrypoint |\n"
        md += "| --- | --- |\n"
        for api in impacted_apis:
            method_badge = f"**[{api['method']}]**"
            md += f"| `{api['file']}` | {method_badge} `{api['path']}` (via `{api['function']}`)| \n"
            
    return md

# ---------------------------------------------------------------------------
# GitHub Comment Dispatcher
# ---------------------------------------------------------------------------

def post_comment_to_github(owner: str, repo_name: str, pull_number: int, body: str):
    """
    Dispatches the generated markdown comment to the GitHub PR thread.
    """
    url = f"https://api.github.com/repos/{owner}/{repo_name}/issues/{pull_number}/comments"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"token {GITHUB_TOKEN}",
        "User-Agent": "Diff-Guard"
    }
    response = httpx.post(url, json={"body": body}, headers=headers)
    if response.status_code == 201:
        print("[Diff-Guard] Successfully posted comment back to GitHub PR.")
    else:
        print(f"[Diff-Guard] Failed to post comment: {response.status_code} - {response.text}")

# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def api_health():
    """Health check endpoint."""
    return {"status": "ok", "service": "diff-guard"}

@app.post("/webhook")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    event_type = request.headers.get("X-GitHub-Event")
    if not event_type:
        raise HTTPException(status_code=400, detail="Missing X-GitHub-Event header")
        
    if event_type != "pull_request":
        return JSONResponse(status_code=200, content={"status": f"Ignored event: {event_type}"})
        
    payload = await request.json()
    action = payload.get("action")
    if action not in ("opened", "synchronize", "reopened"):
        return JSONResponse(status_code=200, content={"status": f"Ignored action: {action}"})
        
    # Queue the analysis asynchronously to avoid blocking the webhook response
    background_tasks.add_task(analyze_diff_and_report, payload)
    
    return JSONResponse(status_code=202, content={"status": "Analysis queued"})

def parse_github_url(url: str) -> tuple[str, str]:
    url = url.strip()
    if url.endswith(".git"):
        url = url[:-4]
    if "github.com/" in url:
        parts = url.split("github.com/")[-1].split("/")
        if len(parts) >= 2:
            return parts[0], parts[1]
    parts = url.split("/")
    if len(parts) == 2:
        return parts[0], parts[1]
    raise UnsupportedRepoError("Invalid GitHub URL. Must be like 'https://github.com/owner/repo' or 'owner/repo'")

class AnalyzeRequest(BaseModel):
    repo_url: str
    base: str
    head: str

@app.get("/api/branches")
async def api_get_branches(repo_url: str):
    try:
        owner, repo_name = parse_github_url(repo_url)
        url = f"https://api.github.com/repos/{owner}/{repo_name}/branches"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Diff-Guard"
        }
        if GITHUB_TOKEN:
            headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
            
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, params={"per_page": 100})
            if resp.status_code in (403, 429):
                raise RateLimitError(f"GitHub API rate limit exceeded: {resp.text}")
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=f"Failed to fetch branches: {resp.text}")
                
            branches_data = resp.json()
            formatted_branches = [b["name"] for b in branches_data]
            return {"branches": formatted_branches}
    except (RateLimitError, UnsupportedRepoError, RepoBuildError):
        raise
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Diff-Guard API Error] {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/commits")
async def api_get_commits(repo_url: str, branch: str = None):
    try:
        owner, repo_name = parse_github_url(repo_url)
        url = f"https://api.github.com/repos/{owner}/{repo_name}/commits"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Diff-Guard"
        }
        if GITHUB_TOKEN:
            headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
            
        params = {"per_page": 50}
        if branch:
            params["sha"] = branch
            
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, params=params)
            if resp.status_code in (403, 429):
                raise RateLimitError(f"GitHub API rate limit exceeded: {resp.text}")
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=f"Failed to fetch commits: {resp.text}")
                
            commits_data = resp.json()
            formatted_commits = []
            for c in commits_data:
                formatted_commits.append({
                    "sha": c["sha"],
                    "message": c["commit"]["message"].split("\n")[0],
                    "author": c["commit"]["author"]["name"],
                    "date": c["commit"]["author"]["date"]
                })
            return {"commits": formatted_commits}
    except (RateLimitError, UnsupportedRepoError, RepoBuildError):
        raise
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Diff-Guard API Error] {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/analyze")
async def api_analyze(req: AnalyzeRequest):
    try:
        owner, repo_name = parse_github_url(req.repo_url)
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_base = loop.run_in_executor(executor, _cached_fetch, owner, repo_name, req.base, GITHUB_TOKEN)
            future_head = loop.run_in_executor(executor, _cached_fetch, owner, repo_name, req.head, GITHUB_TOKEN)
            base_files = await future_base
            head_files = await future_head
            
        # Run unified analysis pipeline
        result = run_analysis_pipeline(base_files, head_files)
        
        graph = result["graph"]
        modified_files = result["modified_files"]
        modified_functions_by_file = result["modified_functions_by_file"]
        all_impacted_files = result["all_impacted_files"]
        at_risk_functions = result["at_risk_functions"]
        impacted_apis = result["impacted_apis"]
        risk_score = result["risk_score"]
        status = result["status"]
        summary_text = result["summary_text"]
            
        nodes = []
        for n in graph.nodes():
            nodes.append({
                "id": n,
                "label": os.path.basename(n),
                "is_modified": n in modified_files,
                "is_impacted": n in all_impacted_files
            })
            
        edges = []
        for u, v in graph.edges():
            edges.append({
                "source": u,
                "target": v
            })
            
        formatted_mod_files = []
        for m_file in modified_files:
            changed_entities = []
            for f_name, change_type in modified_functions_by_file.get(m_file, []):
                changed_entities.append({
                    "entity": f_name,
                    "change_type": change_type
                })
            formatted_mod_files.append({
                "file": m_file,
                "changed_entities": changed_entities
            })
            
        return {
            "status": status,
            "risk_score": risk_score,
            "summary_text": summary_text,
            "modified_files": formatted_mod_files,
            "all_impacted_files": list(all_impacted_files),
            "at_risk_functions": at_risk_functions,
            "impacted_apis": impacted_apis,
            "graph_data": {
                "nodes": nodes,
                "edges": edges
            }
        }
    except UnsupportedRepoError as e:
        print(f"[Diff-Guard API Error] {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except RateLimitError as e:
        print(f"[Diff-Guard API Error] {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except RepoBuildError as e:
        print(f"[Diff-Guard API Error] {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Diff-Guard API Error] {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------------------------------
# Static Files & Root Redirect
# ---------------------------------------------------------------------------

@app.get("/")
async def root_redirect():
    return RedirectResponse(url="/dashboard/")

app.mount("/dashboard", StaticFiles(directory="frontend", html=True), name="frontend")
