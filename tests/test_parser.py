import pytest
from parser import extract_functions, find_functions_using_symbol

def test_extract_functions():
    code = b"""
def foo():
    pass

class Bar:
    def method(self):
        pass

async def async_foo():
    pass
"""
    funcs = extract_functions(code, "python")
    
    assert "foo" in funcs
    assert "method" in funcs
    assert "async_foo" in funcs
    
    assert funcs["foo"] == (2, 3)
    assert funcs["method"] == (6, 7)
    assert funcs["async_foo"] == (9, 10)

def test_find_functions_using_symbol():
    code = b"""
def outer():
    modified_target()
    
def safe_func():
    pass
"""
    at_risk = find_functions_using_symbol(code, "modified_target", "python")
    assert "outer" in at_risk
    assert "safe_func" not in at_risk
