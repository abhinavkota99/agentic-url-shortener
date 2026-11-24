package com.example.shortener.domain;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "click_events", indexes = @Index(name = "idx_click_code_time", columnList = "short_code, clicked_at"))
public class ClickEvent {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    @Column(name = "short_code", nullable = false, length = 32)
    private String shortCode;
    @Column(name = "clicked_at", nullable = false)
    private Instant clickedAt;
    @Column(name = "referrer", length = 1000)
    private String referrer;
    @Column(name = "user_agent", length = 1000)
    private String userAgent;
    protected ClickEvent() {}
    public ClickEvent(String shortCode, String referrer, String userAgent) {
        this.shortCode = shortCode; this.referrer = referrer;
        this.userAgent = userAgent; this.clickedAt = Instant.now();
    }
    public String getShortCode() { return shortCode; }
    public Instant getClickedAt() { return clickedAt; }
}
