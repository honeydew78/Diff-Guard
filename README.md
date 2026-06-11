# 🛡️ Diff-Guard: Stateless AST-Based Architectural Risk Engine

Diff-Guard is a stateless, high-performance static analyzer and developer tool designed to run in continuous integration (CI) environments, webhook containers, or as a local/hosted dashboard. By translating source code into Abstract Syntax Trees (ASTs) rather than parsing raw text differences, Diff-Guard resolves modified semantic entities (like functions) and calculates their exact architectural "blast radius" upward through your codebase using a directed dependency call graph.

🚀 **Hosted Web Dashboard:** [https://diff-guard.onrender.com/dashboard/](https://diff-guard.onrender.com/dashboard/)

---

## ✨ Features

- **Multi-Language AST Parsing:** Supports robust AST parsing and symbol extraction for **Python**, **JavaScript/TypeScript**, and **Go** codebases using Tree-sitter.
- **In-Memory Operations:** Bypasses disk-heavy git clones. It streams gzipped code archives directly into memory buffers via the GitHub API, making it lightweight and highly scalable.
- **AST Change Intersection:** Maps modified line coordinates directly to tree-sitter AST nodes to find altered semantic functions and classes.
- **Transitive Impact Graph:** Reconstructs the repository's dependency graph in-memory using `networkx` to run upstream BFS queries.
- **Downstream Usage Scanner:** Identifies at-risk functions in direct consumer modules that rely on the modified symbols.
- **Public API Entrypoint Tracker:** Flags if any modified backend functions ultimately cascade into and affect public API endpoints (e.g., FastAPI, Express, or Go router handlers).
- **Automated PR Reviewer:** Posts structured feedback reports containing a calculated risk score directly to the developer's GitHub Pull Request.
- **Interactive React Dashboard:** A visually stunning, glassmorphic UI built with React and Cytoscape.js. It visualizes the blast radius of any two commits, fetches branches/commits directly, and maintains a history of past analyses.

---

## 🚦 Understanding the Risk Score

Diff-Guard calculates a **Risk Score (0-100)** to quantify the *architectural fragility* of a change. The score is a multi-factor calculation based on:
1. **Graph Centrality (up to 40 pts):** Betweenness centrality of the modified files in the dependency graph.
2. **Blast Radius (up to 30 pts):** The total number of downstream modules impacted by the change.
3. **Public API Exposure (up to 20 pts):** The number of downstream user-facing API endpoints affected.
4. **Deleted Functions (up to 10 pts):** The count of removed semantic entities.

- 🟢 **Low Risk (0 - 19) - *Isolated Change*:** 
  The modified files have limited connectivity and impact few, if any, downstream consumers.
  - *Context:* Standard code review is sufficient.
  
- 🟡 **Moderate Risk (20 - 49) - *Moderate Dependency*:**
  The change ripples into several downstream consumers that should be verified.
  - *Context:* Ensure integration tests cover the affected downstream modules.

- 🔴 **High to Critical Risk (50 - 100) - *Core Infrastructure Change*:**
  The modified code is highly centralized (e.g., core utilities) and has a wide downstream impact.
  - *Context:* Requires a Senior Engineer review. Extensive regression testing and validation of impacted API contracts are strongly recommended.

---

## 📸 Interactive Web Interface

The React dashboard allows developers to analyze repositories in real-time, browse history, and inspect code impacts.

### 1. Interactive Codebase Graph & Analysis Input
At the top of the interface, input a GitHub Repository URL and use the **Browse** panel to search or choose base/head branches or commit SHAs. Clicking **Analyze** processes the diff and renders the interactive codebase network.
- **Orange Nodes:** Modified files.
- **Purple Nodes:** Impacted downstream files.
- **Grey Nodes:** Untouched modules.

<img width="1468" height="799" alt="Screenshot 2026-06-11 at 1 32 56 PM" src="https://github.com/user-attachments/assets/fbd52acb-8607-465d-92b9-1d08309b7016" />



### 2. Branch & Commit Browser Modal
Clicking the **Browse** button opens a modal that allows you to browse branch-specific commit history fetched directly from the GitHub API.
- **Branch Dropdown:** Select a branch from the dropdown menu (e.g., `main`, `stable`, `workflow`) to retrieve its recent commits.
- **Commit Timeline:** View commit messages, authors, dates, and SHAs in chronological order.
- **Target Selectors:** Interactively assign any commit in the list as the **Base** or **Head** commit for your risk analysis with a single click.

<img width="1097" height="780" alt="Screenshot 2026-06-10 at 1 20 28 PM" src="https://github.com/user-attachments/assets/4821f99a-e811-4fd5-b8a5-efa898258cd8" />


### 3. Inspecting Modified Files & AST Changes
The **Modified Files** tab shows all the code files changed between the two commits, listing the specific AST entities (functions, routes) that were added, deleted, or modified.

<img width="2940" height="1598" alt="image" src="https://github.com/user-attachments/assets/538c7138-8a9f-419a-b1d5-dc31f707494e" />


### 4. Tracking Transitive Blast Radius
The **Transitive Blast Radius** tab shows all files impacted upstream by the changes, highlighting the exact dependency paths, downstream functions at risk, and affected public API routes.

<img width="2940" height="1600" alt="image" src="https://github.com/user-attachments/assets/19e2adba-a64f-455c-bb8c-9d32c792e4b0" />

### 5. Local Analysis History
The **History** tab in the sidebar saves previous analysis runs inside your browser's local storage. This allows you to instantly reload past codebase graphs or clear historical runs with a single click.

<img width="2930" height="1580" alt="image" src="https://github.com/user-attachments/assets/14412716-4244-4fe6-8d69-630b3337c5a4" />


---

## 🛠️ Architecture & Flow

```text
                       [GitHub PR Event / Local Form Submit]
                                    │
                                    ▼
      ┌────────────────────────────┴────────────────────────────┐
      │ Concurrent Stream Capture (Base vs. Head commit)        │
      │   ├─► Stream Base Tarball into RAM                      │
      │   └─► Stream Head Tarball into RAM                      │
      └────────────────────────────┬────────────────────────────┘
                                    │
                                    ▼
      ┌────────────────────────────┴────────────────────────────┐
      │ AST parsing (Tree-sitter) & Dependency Graph Builder    │
      └────────────────────────────┬────────────────────────────┘
                                    │
                                    ▼
      ┌────────────────────────────┴────────────────────────────┐
      │ Diff Intersection & BFS Traversal                       │
      │   ├─► Intersect line diffs with AST ranges             │
      │   └─► Trace impact paths upward using networkx          │
      └────────────────────────────┬────────────────────────────┘
                                    │
                                    ▼
      ┌────────────────────────────┴────────────────────────────┐
      │ Formatted JSON Response / Automated PR Comment          │
      └─────────────────────────────────────────────────────────┘
```

---

## 🚀 Setup & Local Execution

### 1. Installation Requirements
Ensure you are running Python 3.11+ and have installed the required dependencies:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Run Local Test Suite
To verify the AST parsing, dependency graph assembly, and reachability engine:
```bash
pytest tests/ -v
```

### 3. Start the Web Dashboard and API
Start the FastAPI server locally:
```bash
# Set your GitHub token to bypass API rate limits or dispatch PR comments
export GITHUB_TOKEN="your_personal_access_token"

# Run Uvicorn dev server
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```
Once running, open your browser and navigate to:
**`http://localhost:8000/dashboard/`**

---

## 💻 CLI Usage

Diff-Guard includes a command-line interface for running risk analysis directly on local repositories:

```bash
# Analyze changes between two branches/commits in the current directory
python cli.py --base main --head feature-branch

# Analyze a different local repository directory
python cli.py --base v1.0 --head v1.1 --repo /path/to/another/repo

# Automatically post the generated report back to a GitHub PR
python cli.py --base main --head feature-branch --post-comment --pr-number 42 --github-repository owner/repo
```

---

## 🕸️ API Endpoints

- **`GET /api/health`**  
  Health check endpoint to verify service status.
- **`POST /webhook`**  
  GitHub App/Webhook endpoint. Listens for `pull_request` events (`opened`, `synchronize`, `reopened`), performs analysis, and posts PR comments.
- **`GET /api/branches?repo_url=<URL>`**  
  Retrieves a list of branches for a given GitHub repository.
- **`GET /api/commits?repo_url=<URL>&branch=<branch>`**  
  Retrieves the commit history of a repository/branch.
- **`POST /api/analyze`**  
  Payload: `{"repo_url": "...", "base": "...", "head": "..."}`  
  Executes the in-memory AST and graph analysis, returning full risk details and CytoScape graph structures.

---

## 📦 Directory Structure

- `frontend/` - React + Cytoscape UI (`App.js`, `style.css`, `index.html`).
- `languages/` - AST language registry and language providers (`python.py`, `javascript.py`, `go.py`, `base.py`).
- `parser.py` - Wrappers for Tree-sitter parsing, coordinate mapping, and symbol scanning.
- `graph_engine.py` - Module import resolvers, dependency graph building, and BFS logic.
- `streaming_client.py` - In-memory sequential tarball streaming from GitHub.
- `app.py` - FastAPI controller containing background tasks, APIs, and dashboard routes.
- `cli.py` - Command-line interface for local repository testing.
