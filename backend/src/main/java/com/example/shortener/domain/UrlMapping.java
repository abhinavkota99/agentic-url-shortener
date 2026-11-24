package com.example.shortener.domain;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "url_mappings", uniqueConstraints = @UniqueConstraint(name = "uk_short_code", columnNames = "short_code"))
public class UrlMapping {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    @Column(name = "short_code", nullable = false, length = 32)
    private String shortCode;
    @Column(name = "original_url", nullable = false, columnDefinition = "TEXT")
    private String originalUrl;
    @Column(name = "created_at", nullable = false)
    private Instant createdAt;
    @Column(name = "expires_at")
    private Instant expiresAt;
    @Column(name = "active", nullable = false)
    private boolean active = true;

    protected UrlMapping() {}
    public UrlMapping(String shortCode, String originalUrl, Instant expiresAt) {
        this.shortCode = shortCode; this.originalUrl = originalUrl;
        this.createdAt = Instant.now(); this.expiresAt = expiresAt; this.active = true;
    }
    public Long getId() { return id; }
    public String getShortCode() { return shortCode; }
    public String getOriginalUrl() { return originalUrl; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getExpiresAt() { return expiresAt; }
    public boolean isActive() { return active; }
    public void deactivate() { this.active = false; }
    public void updateExpiry(Instant expiresAt) { this.expiresAt = expiresAt; }
    public boolean isExpired() { return expiresAt != null && !expiresAt.isAfter(Instant.now()); }
}
