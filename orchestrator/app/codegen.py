"""LLM-assisted code generation with strict file/path policy and deterministic fallback."""
from pathlib import Path
from .agents import _llm_json
from .workspace import create_workspace, apply_files, git_diff, git_status, WorkspaceError


def _fallback_files(requirement: str) -> list[dict]:
    backend = Path(__file__).resolve().parents[2] / "backend"
    service_path = backend / "src/main/java/com/example/shortener/service/UrlService.java"
    controller_path = backend / "src/main/java/com/example/shortener/api/UrlController.java"
    service = service_path.read_text(encoding="utf-8")
    controller = controller_path.read_text(encoding="utf-8")

    service_anchor = "    private UrlResponse response(UrlMapping m) {"
    service_method = """    @Transactional
    public UrlResponse updateExpiry(String code, Instant expiresAt) {
        UrlExpirationPolicy.validateFutureExpiry(expiresAt, Instant.now());
        UrlMapping mapping = urls.findByShortCode(code)
                .orElseThrow(() -> new UrlNotFoundException("Short URL not found"));
        mapping.updateExpiry(expiresAt);
        redis.delete("url:" + code);
        return response(mapping);
    }

"""
    if service_anchor not in service:
        raise WorkspaceError("Could not safely locate UrlService insertion point")
    service = service.replace(service_anchor, service_method + service_anchor, 1)

    controller_anchor = """    @DeleteMapping("/api/v1/urls/{code}")
"""
    controller_method = """    @PatchMapping("/api/v1/urls/{code}/expiry")
    public UrlResponse updateExpiry(@PathVariable String code,
                                    @RequestBody UpdateExpiryRequest request) {
        return service.updateExpiry(code, request.expiresAt());
    }

"""
    if controller_anchor not in controller:
        raise WorkspaceError("Could not safely locate UrlController insertion point")
    controller = controller.replace(controller_anchor, controller_method + controller_anchor, 1)

    return [
        {
            "path": "src/main/java/com/example/shortener/service/UrlService.java",
            "content": service
        },
        {
            "path": "src/main/java/com/example/shortener/api/UrlController.java",
            "content": controller
        },
        {
            "path": "src/main/java/com/example/shortener/api/UpdateExpiryRequest.java",
            "content": """package com.example.shortener.api;

import java.time.Instant;

public record UpdateExpiryRequest(Instant expiresAt) {}
"""
        },
        {
            "path": "src/main/java/com/example/shortener/service/UrlExpirationPolicy.java",
            "content": """package com.example.shortener.service;

import java.time.Instant;

/** Centralizes URL expiration decisions for reuse by redirect and management flows. */
public final class UrlExpirationPolicy {
    private UrlExpirationPolicy() {}

    public static boolean isExpired(Instant expiresAt, Instant now) {
        return expiresAt != null && !expiresAt.isAfter(now);
    }

    public static void validateFutureExpiry(Instant expiresAt, Instant now) {
        if (expiresAt != null && !expiresAt.isAfter(now)) {
            throw new IllegalArgumentException("expiresAt must be in the future");
        }
    }
}
"""
        },
        {
            "path": "src/test/java/com/example/shortener/service/UrlExpirationPolicyTest.java",
            "content": """package com.example.shortener.service;

import org.junit.jupiter.api.Test;
import java.time.Instant;
import static org.junit.jupiter.api.Assertions.*;

class UrlExpirationPolicyTest {
    @Test void noExpiryNeverExpires() {
        assertFalse(UrlExpirationPolicy.isExpired(null, Instant.parse("2026-01-01T00:00:00Z")));
    }
    @Test void futureExpiryIsActive() {
        assertFalse(UrlExpirationPolicy.isExpired(
            Instant.parse("2027-01-01T00:00:00Z"), Instant.parse("2026-01-01T00:00:00Z")));
    }
    @Test void expiryAtNowIsExpired() {
        Instant now = Instant.parse("2026-01-01T00:00:00Z");
        assertTrue(UrlExpirationPolicy.isExpired(now, now));
    }
    @Test void pastExpiryIsExpired() {
        assertTrue(UrlExpirationPolicy.isExpired(
            Instant.parse("2025-01-01T00:00:00Z"), Instant.parse("2026-01-01T00:00:00Z")));
    }
    @Test void rejectsExpiryThatIsNotInFuture() {
        Instant now = Instant.parse("2026-01-01T00:00:00Z");
        assertThrows(IllegalArgumentException.class,
            () -> UrlExpirationPolicy.validateFutureExpiry(now, now));
    }
}
"""
        }
    ]

def validate_generated_content(files: list[dict]) -> None:
    forbidden = [
        "Runtime.getRuntime().exec",
        "new ProcessBuilder",
        "ScriptEngineManager",
        "ObjectInputStream",
        "setAccessible(true)"
    ]
    secret_patterns = [
        r"""(?i)(api[_-]?key|password|secret)\s*[:=]\s*['"][^'"]{8,}['"]""",
        r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"
    ]
    import re
    for item in files:
        content = item.get("content", "")
        for token in forbidden:
            if token in content:
                raise WorkspaceError(f"Generated code violates execution policy: {token}")
        for pattern in secret_patterns:
            if re.search(pattern, content):
                raise WorkspaceError("Generated code appears to contain a hard-coded secret")

def generate_and_apply(workflow_id: str, requirement: str) -> dict:
    workspace = create_workspace(workflow_id)
    prompt = (
        "Generate a minimal, production-quality Java 21 Spring Boot feature for this repository. "
        "Return strict JSON: {summary:string, files:[{path:string,content:string}], tests:string[]}. "
        "Only add or edit files under src/main/java/ or src/test/java/. "
        "Never modify pom.xml, application configuration, security policy, Docker files, or scripts. "
        "Do not include shell commands. Include focused JUnit 5 tests. "
        f"Requirement: {requirement}"
    )
    generated = _llm_json(
        "You are a cautious senior Java engineer. Return valid JSON only. "
        "Do not claim tests ran. Generate minimal compilable Java code and tests.",
        prompt
    )
    source = "llm" if generated and isinstance(generated.get("files"), list) else "deterministic-fallback"
    files = generated["files"] if source == "llm" else _fallback_files(requirement)
    if not files:
        raise WorkspaceError("Code generator returned no files")
    validate_generated_content(files)
    changed = apply_files(workspace, files)
    diff = git_diff(workspace)
    return {
        "status": "CODE_GENERATED",
        "generator": source,
        "summary": generated.get("summary", "Added URL expiration policy and unit tests") if generated else "Added URL expiration policy and unit tests",
        "workspace": str(workspace),
        "changedFiles": changed,
        "gitStatus": git_status(workspace),
        "diff": diff[:30000],
        "diffTruncated": len(diff) > 30000
    }
