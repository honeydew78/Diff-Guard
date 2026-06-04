# 🛡️ Diff-Guard: Stateless AST-Based Architectural Risk Engine

Diff-Guard is a stateless, high-performance static analyzer and developer tool designed to run in continuous integration (CI) environments or webhook containers. By translating source code into Abstract Syntax Trees (ASTs) rather than parsing raw text differences, Diff-Guard resolves modified semantic entities (like functions) and calculates their exact architectural "blast radius" upward through your codebase using a directed dependency call graph.

---

## ✨ Features
- **In-Memory Operations:** Bypasses disk-heavy git clones. It streams gzipped code archives directly into memory buffers, making it lightweight and highly scalable.
- **AST Change Intersection:** Maps changed code coordinates directly to tree-sitter AST nodes to find altered semantic functions.
- **Transitive Impact Graph:** Reconstructs your repository's dependency graph in-memory using `networkx` to run upstream BFS queries.
- **Automated PR Reviewer:** Posts clear, structured feedback reports containing a calculated risk score directly to the developer's GitHub Pull Request.

---

## 🛠️ Architecture

```
                       [GitHub PR Event Webhook]
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
                       [GitHub PR Review Report]
```

---

## 🚀 Setup & Execution

### 1. Requirements
Ensure you are running Python 3.9+ and have installed the required dependencies:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Run Local Test Suite
To verify the parsing and graph reachability engine works end-to-end:
```bash
python sandbox_test.py
```

### 3. Start Webhook Server
Start the Uvicorn-based FastAPI app locally:
```bash
# Set your GitHub token if you wish to dispatch comments back to PRs
export GITHUB_TOKEN="your_personal_access_token"

# Run Uvicorn dev server
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🕸️ API Webhook Endpoint
The engine exposes a single endpoint to handle GitHub webhooks:
- **Route:** `POST /webhook`
- **Headers:** `X-GitHub-Event: pull_request`
- **Payload Action Filters:** `opened`, `synchronize`, `reopened`

---

## 📦 Directory Structure
- [parser.py](file:///Users/agrimraj/Projects/Diff-Guard/parser.py): Tree-sitter parsing wrappers and function coordinate extractor.
- [graph_engine.py](file:///Users/agrimraj/Projects/Diff-Guard/graph_engine.py): Dependency graph assembly and BFS tracer using networkx.
- [streaming_client.py](file:///Users/agrimraj/Projects/Diff-Guard/streaming_client.py): In-memory sequential streaming and tar archive extractor.
- [app.py](file:///Users/agrimraj/Projects/Diff-Guard/app.py): FastAPI web server and webhook pipeline controller.
- [requirements.txt](file:///Users/agrimraj/Projects/Diff-Guard/requirements.txt): List of pinned project dependencies.
