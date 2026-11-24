package com.example.shortener.api;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import java.time.Instant;

public record CreateUrlRequest(
    @NotBlank String originalUrl,
    @Pattern(regexp = "^[a-zA-Z0-9_-]{3,32}$", message = "Alias must be 3-32 URL-safe characters")
    String customAlias,
    Instant expiresAt
) {}
