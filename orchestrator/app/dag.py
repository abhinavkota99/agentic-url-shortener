from collections import defaultdict, deque

class DependencyError(ValueError):
    pass

def validate_and_group(tasks):
    ids = {t["id"] for t in tasks}
    if len(ids) != len(tasks):
        raise DependencyError("Duplicate task IDs")
    indegree = {t["id"]: 0 for t in tasks}
    children = defaultdict(list)
    for task in tasks:
        for dep in task.get("dependencies", []):
            if dep not in ids:
                raise DependencyError(f"Unknown dependency {dep} for task {task['id']}")
            indegree[task["id"]] += 1
            children[dep].append(task["id"])
    queue = deque(sorted(k for k, v in indegree.items() if v == 0))
    levels, visited = [], 0
    while queue:
        current = list(queue)
        queue.clear()
        levels.append(current)
        visited += len(current)
        for node in current:
            for child in children[node]:
                indegree[child] -= 1
                if indegree[child] == 0:
                    queue.append(child)
    if visited != len(tasks):
        raise DependencyError("Dependency cycle detected")
    return levels

def retry_delay(attempt, base_seconds=1.0, max_seconds=30.0):
    if attempt < 1:
        raise ValueError("attempt must be >= 1")
    return min(max_seconds, base_seconds * (2 ** (attempt - 1)))
