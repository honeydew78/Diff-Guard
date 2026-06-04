import os
import asyncio
import difflib
import concurrent.futures
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
import httpx

from streaming_client import fetch_repository_archive
from graph_engine import build_dependency_graph, get_impacted_files
from parser import extract_functions

app = FastAPI(title="Diff-Guard Risk Engine")

# Fetch token from environment variable
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

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

def analyze_diff_and_report(payload: dict):
    """
    Background worker that runs the full Diff-Guard pipeline:
    1. Downloads base & head commit snapshots.
    2. Builds a codebase dependency graph.
    3. Resolves modified functions/entities.
    4. Computes upstream blast radius.
    5. Formats and dispatches a markdown report to the PR thread.
    """
    try:
        pull_number = payload["pull_request"]["number"]
        base_sha = payload["pull_request"]["base"]["sha"]
        head_sha = payload["pull_request"]["head"]["sha"]
        
        repo_info = payload["repository"]
        owner = repo_info["owner"]["login"]
        repo_name = repo_info["name"]
        
        print(f"\n[Diff-Guard] Analyzing PR #{pull_number} ({base_sha} -> {head_sha})")
        
        # Step 4 logic: Fetch archive states concurrently using ThreadPoolExecutor
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_base = executor.submit(fetch_repository_archive, owner, repo_name, base_sha, GITHUB_TOKEN)
            future_head = executor.submit(fetch_repository_archive, owner, repo_name, head_sha, GITHUB_TOKEN)
            
            base_files = future_base.result()
            head_files = future_head.result()
        
        # Step 3 logic: Build dependency graph from base state
        graph = build_dependency_graph(base_files)
        
        # Step 2 logic: Compare base and head files to locate structural changes
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
                    base_funcs = extract_functions(base_code, "python")
                    head_funcs = extract_functions(head_code, "python")
                    
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
                        
        # Step 3/7 logic: Trace impacted modules upward via DiGraph BFS
        import networkx as nx
        from parser import find_functions_using_symbol
        
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
                if len(path) == 2: # Direct consumer
                    # Scan the consumer for usage of the modified symbols
                    code_bytes = head_files.get(imp_file)
                    if code_bytes:
                        for c_func_name, c_type in changed_entities:
                            if c_type in ("modified", "deleted"):
                                found_funcs = find_functions_using_symbol(code_bytes, c_func_name)
                                if found_funcs:
                                    if imp_file not in at_risk_functions:
                                        at_risk_functions[imp_file] = []
                                    at_risk_functions[imp_file].extend(found_funcs)
                                    
        # Dedup at_risk_functions
        for k in at_risk_functions:
            at_risk_functions[k] = list(dict.fromkeys(at_risk_functions[k]))
            
        # Step 8 logic: Format and Dispatch feedback
        report_md = format_markdown_report(
            pull_number, modified_files, modified_functions_by_file,
            all_impacted_files, impact_paths, at_risk_functions
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

def format_markdown_report(
    pull_number: int,
    modified_files: list,
    modified_functions_by_file: dict,
    all_impacted_files: set,
    impact_paths: dict,
    at_risk_functions: dict
) -> str:
    """
    Constructs a structured GitHub Markdown report with a Risk Score.
    """
    # 10 points of risk per impacted downstream file, capped at 100
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
        md += "_No Python code modifications detected._\n"
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
            
    return md

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
