package com.example.shortener.api;

import com.example.shortener.service.UrlService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import java.net.URI;

@RestController
public class UrlController {
    private final UrlService service;
    public UrlController(UrlService service) { this.service = service; }

    @PostMapping("/api/v1/urls")
    public ResponseEntity<UrlResponse> create(@Valid @RequestBody CreateUrlRequest request) {
        return ResponseEntity.status(HttpStatus.CREATED).body(service.create(request));
    }

    @GetMapping("/api/v1/urls/{code}")
    public UrlResponse get(@PathVariable String code) { return service.get(code); }

    @DeleteMapping("/api/v1/urls/{code}")
    public ResponseEntity<Void> deactivate(@PathVariable String code) {
        service.deactivate(code); return ResponseEntity.noContent().build();
    }

    @GetMapping("/api/v1/urls/{code}/analytics")
    public AnalyticsResponse analytics(@PathVariable String code) { return service.analytics(code); }

    @GetMapping("/{code:[a-zA-Z0-9_-]{3,32}}")
    public ResponseEntity<Void> redirect(@PathVariable String code, HttpServletRequest request) {
        String target = service.resolve(code);
        service.recordClick(code, request.getHeader("Referer"), request.getHeader("User-Agent"));
        return ResponseEntity.status(HttpStatus.FOUND).location(URI.create(target)).build();
    }
}
