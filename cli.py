import subprocess
import argparse
import sys
import os

# Import existing helpers from our app and parser
from app import get_changed_line_numbers, format_markdown_report, post_comment_to_github
from graph_engine import build_dependency_graph, get_impacted_files
from parser import extract_functions, find_functions_using_symbol
import networkx as nx

def git_list_files(repo_path: str, commit: str) -> list[str]:
    """
    Lists all Python files in the repository at a specific commit.
    """
    try:
        result = subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", commit],
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True
        )
        return [line.strip() for line in result.stdout.splitlines() if line.strip().endswith(".py")]
    except subprocess.CalledProcessError as e:
        print(f"Error listing files for commit {commit}: {e.stderr.strip()}", file=sys.stderr)
        sys.exit(1)

def git_show(repo_path: str, commit: str, file_path: str) -> bytes:
    """
    Gets the contents of a file at a specific commit.
    Returns empty bytes if the file doesn't exist at that commit.
    """
    try:
        result = subprocess.run(
            ["git", "show", f"{commit}:{file_path}"],
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError:
        # File might be newly created or deleted, return empty bytes
        return b""

def git_diff_files(repo_path: str, base: str, head: str) -> list[str]:
    """
    Gets the list of modified/added/deleted Python files between base and head.
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", base, head],
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True
        )
        return [line.strip() for line in result.stdout.splitlines() if line.strip().endswith(".py")]
    except subprocess.CalledProcessError as e:
        print(f"Error running git diff: {e.stderr.strip()}", file=sys.stderr)
        sys.exit(1)

def run_analysis(repo_path: str, base: str, head: str) -> str:
    """
    Executes the Diff-Guard risk analysis locally by reading from Git.
    """
    # 1. List and fetch all files at the base commit
    base_file_paths = git_list_files(repo_path, base)
    base_files = {}
    for f in base_file_paths:
        base_files[f] = git_show(repo_path, base, f)
        
    # 2. Build dependency graph
    graph = build_dependency_graph(base_files)
    
    # 3. List modified files
    modified_files = []
    modified_functions_by_file = {}
    
    diff_file_paths = git_diff_files(repo_path, base, head)
    for file_path in diff_file_paths:
        base_code = git_show(repo_path, base, file_path)
        head_code = git_show(repo_path, head, file_path)
        
        if not base_code:
            # File newly added in head
            head_funcs = extract_functions(head_code, "python")
            changed_funcs = [(f_name, "added") for f_name in head_funcs.keys()]
            if changed_funcs:
                modified_files.append(file_path)
                modified_functions_by_file[file_path] = changed_funcs
        elif not head_code:
            # File deleted in head
            base_funcs = extract_functions(base_code, "python")
            changed_funcs = [(f_name, "deleted") for f_name in base_funcs.keys()]
            if changed_funcs:
                modified_files.append(file_path)
                modified_functions_by_file[file_path] = changed_funcs
        else:
            # File modified
            if base_code != head_code:
                base_funcs = extract_functions(base_code, "python")
                head_funcs = extract_functions(head_code, "python")
                
                base_changed, head_changed = get_changed_line_numbers(base_code, head_code)
                changed_funcs = []
                
                # Check for modified or deleted functions
                for f_name, (start_b, end_b) in base_funcs.items():
                    if f_name not in head_funcs:
                        changed_funcs.append((f_name, "deleted"))
                    else:
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

    # 4. Compute blast radius upstream
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
        
    # 5. Scan direct consumers for at-risk functions
    for m_file in modified_files:
        changed_entities = modified_functions_by_file.get(m_file, [])
        for imp_file, path in impact_paths.get(m_file, {}).items():
            if len(path) == 2:  # Direct consumer
                # Get consumer file contents at head state
                code_bytes = git_show(repo_path, head, imp_file)
                if code_bytes:
                    for c_func_name, c_type in changed_entities:
                        if c_type in ("modified", "deleted"):
                            found_funcs = find_functions_using_symbol(code_bytes, c_func_name)
                            if found_funcs:
                                if imp_file not in at_risk_functions:
                                    at_risk_functions[imp_file] = []
                                at_risk_functions[imp_file].extend(found_funcs)
                                
    # Dedup at-risk functions list
    for k in at_risk_functions:
        at_risk_functions[k] = list(dict.fromkeys(at_risk_functions[k]))
        
    # Extract API Routes for impacted files
    from parser import extract_api_routes
    impacted_apis = []
    for imp_file, funcs in at_risk_functions.items():
        code_bytes = git_show(repo_path, head, imp_file)
        if code_bytes:
            routes = extract_api_routes(code_bytes)
            for f in funcs:
                if f in routes:
                    impacted_apis.append({
                        "file": imp_file,
                        "function": f,
                        "method": routes[f]["method"],
                        "path": routes[f]["path"]
                    })
        
    # 6. Format markdown report
    # We pass 0 as dummy PR number for CLI display, or we will override it in main()
    return format_markdown_report(
        0, modified_files, modified_functions_by_file,
        all_impacted_files, impact_paths, at_risk_functions, impacted_apis
    )

def main():
    parser = argparse.ArgumentParser(description="Diff-Guard Local CLI Analysis")
    parser.add_argument("--base", required=True, help="Base commit or branch (e.g. main)")
    parser.add_argument("--head", required=True, help="Head commit or branch (e.g. feature)")
    parser.add_argument("--repo", default=".", help="Path to local Git repository (default: current directory)")
    parser.add_argument("--post-comment", action="store_true", help="Post report to GitHub pull request")
    parser.add_argument("--pr-number", type=int, help="GitHub Pull Request number")
    parser.add_argument("--github-repository", help="GitHub repository name (e.g., owner/repo)")
    
    args = parser.parse_args()
    
    report_md = run_analysis(args.repo, args.base, args.head)
    
    print("\n--- Diff-Guard Analysis Report ---")
    print(report_md)
    print("----------------------------------\n")
    
    if args.post_comment:
        if not args.pr_number or not args.github_repository:
            print("Error: --pr-number and --github-repository are required when using --post-comment", file=sys.stderr)
            sys.exit(1)
            
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            print("Error: GITHUB_TOKEN environment variable is required to post comments", file=sys.stderr)
            sys.exit(1)
            
        # Update dummy PR number in report string
        report_md = report_md.replace("PR: #0", f"PR: #{args.pr_number}")
        
        # Override the global GITHUB_TOKEN inside app.py module's context so it can authenticate
        import app
        app.GITHUB_TOKEN = token
        
        parts = args.github_repository.split("/")
        if len(parts) != 2:
            print(f"Error: Invalid repository format '{args.github_repository}'. Expected 'owner/repo'", file=sys.stderr)
            sys.exit(1)
            
        owner, repo_name = parts
        post_comment_to_github(owner, repo_name, args.pr_number, report_md)

if __name__ == "__main__":
    main()
