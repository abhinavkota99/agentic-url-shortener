package com.example.shortener.service;

import com.example.shortener.api.*;
import com.example.shortener.domain.*;
import com.example.shortener.repository.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.net.URI;
import java.security.SecureRandom;
import java.time.Duration;
import java.time.Instant;

@Service
public class UrlService {
    private static final String ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ";
    private final SecureRandom random = new SecureRandom();
    private final UrlMappingRepository urls;
    private final ClickEventRepository clicks;
    private final StringRedisTemplate redis;
    private final String baseUrl;
    private final long cacheTtl;

    public UrlService(UrlMappingRepository urls, ClickEventRepository clicks,
                      StringRedisTemplate redis,
                      @Value("${app.base-url}") String baseUrl,
                      @Value("${app.cache-ttl-seconds:3600}") long cacheTtl) {
        this.urls = urls; this.clicks = clicks; this.redis = redis;
        this.baseUrl = baseUrl; this.cacheTtl = cacheTtl;
    }

    @Transactional
    public UrlResponse create(CreateUrlRequest request) {
        validateHttpUrl(request.originalUrl());
        if (request.expiresAt() != null && !request.expiresAt().isAfter(Instant.now()))
            throw new IllegalArgumentException("expiresAt must be in the future");

        String code = request.customAlias() == null || request.customAlias().isBlank()
                ? generateUniqueCode() : request.customAlias();
        if (urls.existsByShortCode(code)) throw new IllegalArgumentException("Short code already exists");

        UrlMapping saved = urls.save(new UrlMapping(code, request.originalUrl(), request.expiresAt()));
        return response(saved);
    }

    @Transactional(readOnly = true)
    public String resolve(String code) {
        String key = "url:" + code;
        String cached = redis.opsForValue().get(key);
        if (cached != null) return cached;

        UrlMapping mapping = urls.findByShortCode(code)
                .orElseThrow(() -> new UrlNotFoundException("Short URL not found"));
        if (!mapping.isActive() || mapping.isExpired())
            throw new UrlNotFoundException("Short URL is inactive or expired");

        long ttl = cacheTtl;
        if (mapping.getExpiresAt() != null) {
            ttl = Math.min(ttl, Math.max(1, Duration.between(Instant.now(), mapping.getExpiresAt()).getSeconds()));
        }
        redis.opsForValue().set(key, mapping.getOriginalUrl(), Duration.ofSeconds(ttl));
        return mapping.getOriginalUrl();
    }

    @Transactional
    public void recordClick(String code, String referrer, String userAgent) {
        clicks.save(new ClickEvent(code, safeHeader(referrer), safeHeader(userAgent)));
    }

    @Transactional
    public void deactivate(String code) {
        UrlMapping mapping = urls.findByShortCode(code)
                .orElseThrow(() -> new UrlNotFoundException("Short URL not found"));
        mapping.deactivate();
        redis.delete("url:" + code);
    }

    @Transactional(readOnly = true)
    public UrlResponse get(String code) {
        UrlMapping mapping = urls.findByShortCode(code)
                .orElseThrow(() -> new UrlNotFoundException("Short URL not found"));
        return response(mapping);
    }

    @Transactional(readOnly = true)
    public AnalyticsResponse analytics(String code) {
        if (!urls.existsByShortCode(code)) throw new UrlNotFoundException("Short URL not found");
        return new AnalyticsResponse(code, clicks.countByShortCode(code),
                clicks.countSince(code, Instant.now().minus(Duration.ofHours(24))));
    }

    private UrlResponse response(UrlMapping m) {
        return new UrlResponse(m.getShortCode(), baseUrl + "/" + m.getShortCode(),
                m.getOriginalUrl(), m.getCreatedAt(), m.getExpiresAt());
    }

    private String generateUniqueCode() {
        for (int attempt = 0; attempt < 5; attempt++) {
            StringBuilder code = new StringBuilder(7);
            for (int i = 0; i < 7; i++) code.append(ALPHABET.charAt(random.nextInt(ALPHABET.length())));
            if (!urls.existsByShortCode(code.toString())) return code.toString();
        }
        throw new IllegalStateException("Could not generate a unique short code after bounded retries");
    }

    private void validateHttpUrl(String value) {
        try {
            URI uri = URI.create(value);
            if (!("http".equalsIgnoreCase(uri.getScheme()) || "https".equalsIgnoreCase(uri.getScheme()))
                    || uri.getHost() == null) throw new IllegalArgumentException("Only absolute HTTP/HTTPS URLs are supported");
        } catch (IllegalArgumentException ex) {
            throw new IllegalArgumentException("Invalid URL: " + ex.getMessage());
        }
    }

    private String safeHeader(String value) {
        if (value == null) return null;
        return value.length() > 1000 ? value.substring(0, 1000) : value;
    }
}
