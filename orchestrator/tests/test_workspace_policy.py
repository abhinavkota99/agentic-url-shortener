import pytest
from app.workspace import validate_relative_path, WorkspaceError

def test_java_source_path_allowed():
    assert validate_relative_path("src/main/java/com/example/Foo.java").as_posix().endswith("Foo.java")

def test_path_traversal_rejected():
    with pytest.raises(WorkspaceError):
        validate_relative_path("../outside.txt")

def test_build_configuration_protected():
    with pytest.raises(WorkspaceError):
        validate_relative_path("pom.xml")

def test_arbitrary_script_path_rejected():
    with pytest.raises(WorkspaceError):
        validate_relative_path("scripts/run.sh")
