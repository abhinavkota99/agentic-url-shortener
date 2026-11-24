package com.example.shortener.api;

import java.time.Instant;

public record UrlResponse(String shortCode, String shortUrl, String originalUrl, Instant createdAt, Instant expiresAt) {}
