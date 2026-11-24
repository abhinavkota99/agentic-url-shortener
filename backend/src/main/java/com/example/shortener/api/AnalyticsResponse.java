package com.example.shortener.api;

public record AnalyticsResponse(String shortCode, long totalClicks, long clicksLast24Hours) {}
