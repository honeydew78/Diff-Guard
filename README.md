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

Diff-Guard calculates a **Risk Score (0-100%)** to quantify the *architectural fragility* of a change. It doesn't measure code quality (like a linter), but rather how interconnected the modified code is. This helps teams prioritize code review time and testing resources.

- 🟢 **Low Risk (0 - 49%) - *Isolated Change*:** 
  The modified files are "leaf nodes" (e.g., standalone scripts, tests, isolated features) and have few downstream dependents.
  - *Context:* Junior/mid-level engineers can confidently approve. Minimal regression testing needed.
  
- 🟡 **Medium Risk (50 - 79%) - *Moderate Dependency*:**
  The change modifies components imported by multiple downstream modules, but isn't core infrastructure.
  - *Context:* Reviewers should check the interfaces. QA should write or run integration tests specifically for the impacted downstream modules.

- 🔴 **High Risk (80 - 100%) - *Core Infrastructure Change*:**
  The modified code is highly centralized (e.g., database connection handler, core authentication module). A bug here will cascade through the entire system.
  - *Context:* Requires a Senior Engineer or Tech Lead review. Meticulous backward compatibility checks and exhaustive regression test suites are justified.

---

## 📸 Interactive Web Interface

The React dashboard allows developers to analyze repositories in real-time, browse history, and inspect code impacts.

### 1. Interactive Codebase Graph & Analysis Input
At the top of the interface, input a GitHub Repository URL and use the **Browse** panel to search or choose base/head branches or commit SHAs. Clicking **Analyze** processes the diff and renders the interactive codebase network.
- **Orange Nodes:** Modified files.
- **Purple Nodes:** Impacted downstream files.
- **Grey Nodes:** Untouched modules.

![Main Dashboard](dashboard_main.png)

### 2. Inspecting Modified Files & AST Changes
The **Modified Files** tab shows all the code files changed between the two commits, listing the specific AST entities (functions, routes) that were added, deleted, or modified.

![Modified Files](modified_files.png)

### 3. Tracking Transitive Blast Radius
The **Transitive Blast Radius** tab shows all files impacted upstream by the changes, highlighting the exact dependency paths, downstream functions at risk, and affected public API routes.

![Transitive Blast Radius](blast_radius.png)

### 4. Local Analysis History
The **History** tab in the sidebar saves previous analysis runs inside your browser's local storage. This allows you to instantly reload past codebase graphs or clear historical runs with a single click.

![Analysis History](history.png)

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
Ensure you are running Python 3.9+ and have installed the required dependencies:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Run Local Test Suite
To verify the AST parsing, dependency graph assembly, and reachability engine:
```bash
python sandbox_test.py
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
