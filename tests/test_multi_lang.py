import pytest
from parser import extract_functions, find_functions_using_symbol, extract_api_routes
from graph_engine import build_dependency_graph

def test_javascript_extraction():
    js_code = b"""
    function standardFunc() {
        return 42;
    }
    
    const arrowFunc = () => {
        console.log("hello");
    };
    
    class MyClass {
        methodName() {
            // inside method
        }
    }
    """
    
    funcs = extract_functions(js_code, file_path="app.js")
    assert "standardFunc" in funcs
    assert "arrowFunc" in funcs
    assert "methodName" in funcs
    
    assert funcs["standardFunc"] == (2, 4)
    assert funcs["arrowFunc"] == (6, 8)
    assert funcs["methodName"] == (11, 13)

def test_javascript_find_using_symbol():
    js_code = b"""
    function caller() {
        targetSymbol();
    }
    function safe() {}
    """
    at_risk = find_functions_using_symbol(js_code, "targetSymbol", file_path="app.js")
    assert "caller" in at_risk
    assert "safe" not in at_risk

def test_javascript_resolve_imports():
    files_data = {
        "src/app.js": b"import { x } from './utils'; import y from '../config'; const z = require('./components/Button');",
        "src/utils.js": b"export const x = 1;",
        "config.ts": b"export default {};",
        "src/components/Button/index.tsx": b"export default function Button() {}",
    }
    
    graph = build_dependency_graph(files_data)
    
    # Edges go supplier -> consumer
    assert graph.has_edge("src/utils.js", "src/app.js")
    assert graph.has_edge("config.ts", "src/app.js")
    assert graph.has_edge("src/components/Button/index.tsx", "src/app.js")

def test_javascript_api_routes():
    js_code = b"""
    app.get('/api/users', getUsers);
    router.post('/login', loginUser);
    """
    routes = extract_api_routes(js_code, file_path="server.js")
    assert "getUsers" in routes
    assert routes["getUsers"] == {"method": "GET", "path": "/api/users"}
    assert "loginUser" in routes
    assert routes["loginUser"] == {"method": "POST", "path": "/login"}

def test_go_extraction():
    go_code = b"""
    package main
    
    func StandardFunc() int {
        return 42
    }
    
    func (r *Receiver) MethodName() {
        // do something
    }
    """
    funcs = extract_functions(go_code, file_path="main.go")
    assert "StandardFunc" in funcs
    assert "MethodName" in funcs
    
    assert funcs["StandardFunc"] == (4, 6)
    assert funcs["MethodName"] == (8, 10)

def test_go_find_using_symbol():
    go_code = b"""
    package main
    func caller() {
        TargetSymbol()
    }
    """
    at_risk = find_functions_using_symbol(go_code, "TargetSymbol", file_path="main.go")
    assert "caller" in at_risk

def test_go_resolve_imports():
    files_data = {
        "go.mod": b"module github.com/user/myproject\n\ngo 1.18",
        "main.go": b'package main\nimport "github.com/user/myproject/pkg/utils"',
        "pkg/utils/math.go": b"package utils",
        "pkg/utils/string.go": b"package utils",
    }
    
    graph = build_dependency_graph(files_data)
    
    # main.go should depend on all files in utils folder
    assert graph.has_edge("pkg/utils/math.go", "main.go")
    assert graph.has_edge("pkg/utils/string.go", "main.go")

def test_go_api_routes():
    go_code = b"""
    package main
    func main() {
        r.GET("/users", GetUsers)
        router.POST("/v1/login", LoginHandler)
    }
    """
    routes = extract_api_routes(go_code, file_path="main.go")
    assert "GetUsers" in routes
    assert routes["GetUsers"] == {"method": "GET", "path": "/users"}
    assert "LoginHandler" in routes
    assert routes["LoginHandler"] == {"method": "POST", "path": "/v1/login"}
