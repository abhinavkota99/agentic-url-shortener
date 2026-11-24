import pytest
from app.dag import validate_and_group, DependencyError, retry_delay

def test_parallel_levels():
    tasks = [
        {"id":"A","dependencies":[]},
        {"id":"B","dependencies":["A"]},
        {"id":"C","dependencies":["A"]},
        {"id":"D","dependencies":["B","C"]}
    ]
    assert validate_and_group(tasks) == [["A"], ["B","C"], ["D"]]

def test_cycle_rejected():
    with pytest.raises(DependencyError):
        validate_and_group([
            {"id":"A","dependencies":["B"]},
            {"id":"B","dependencies":["A"]}
        ])

def test_retry_backoff_bounded():
    assert retry_delay(1) == 1
    assert retry_delay(4) == 8
    assert retry_delay(10) == 30
