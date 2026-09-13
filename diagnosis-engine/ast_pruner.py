import ast
import os

def extract_function_from_line(filepath: str, target_line: int) -> dict:
    if not os.path.exists(filepath):
        # Fallback mock for demo purposes if the container can't access the file
        return {
            "file": filepath,
            "function": "unknown_function",
            "line_start": target_line,
            "line_end": target_line + 5,
            "code_snippet": "# Source file not accessible in container"
        }

    with open(filepath, "r") as f:
        source_code = f.read()

    try:
        tree = ast.parse(source_code)
    except Exception:
        return {}

    lines = source_code.splitlines()

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if hasattr(node, "lineno") and hasattr(node, "end_lineno"):
                # Check if the target line falls inside the function, or just return the first function for simplicity if target_line is 0
                if target_line == 0 or (node.lineno <= target_line <= node.end_lineno):
                    snippet = "\n".join(lines[node.lineno - 1 : node.end_lineno])
                    return {
                        "file": os.path.basename(filepath),
                        "function": node.name,
                        "line_start": node.lineno,
                        "line_end": node.end_lineno,
                        "code_snippet": snippet
                    }
                    
    return {
        "file": os.path.basename(filepath),
        "function": "unknown",
        "line_start": target_line,
        "line_end": target_line,
        "code_snippet": "# Could not find matching function block"
    }

def prune_code_for_incident(service_name: str, stack_trace: str) -> dict:
    # In a real system, we'd parse the stack trace to find the file and line number.
    # For AgenticMesh mock, we hardcode paths to the mounted source.
    target_file = f"/app/mock-services/{service_name.replace('-', '_')}.py"
    
    # Simple heuristic to find a line number in stack trace
    target_line = 0
    import re
    match = re.search(r"line (\d+)", stack_trace)
    if match:
        target_line = int(match.group(1))
        
    return extract_function_from_line(target_file, target_line)
