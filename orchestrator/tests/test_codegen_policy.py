import pytest
from app.codegen import validate_generated_content
from app.workspace import WorkspaceError

def test_rejects_process_execution():
    with pytest.raises(WorkspaceError):
        validate_generated_content([{
            "path": "src/main/java/com/example/Bad.java",
            "content": 'Runtime.getRuntime().exec("whoami");'
        }])

def test_rejects_hardcoded_secret():
    with pytest.raises(WorkspaceError):
        validate_generated_content([{
            "path": "src/main/java/com/example/Bad.java",
            "content": 'String api_key = "super-secret-value-123";'
        }])

def test_accepts_ordinary_java():
    validate_generated_content([{
        "path": "src/main/java/com/example/Good.java",
        "content": "public class Good {}"
    }])
