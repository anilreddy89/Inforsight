package com.inforsight.controlplane.resilience;

import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ResponseStatusException;

import java.time.Duration;

@Component
public class TriageGuard {
    private final RateLimiter rateLimiter = new RateLimiter(1_000, Duration.ofSeconds(1));
    private final CircuitBreaker circuitBreaker = new CircuitBreaker(3, Duration.ofSeconds(5));

    public void beforeRequest() {
        if (!rateLimiter.tryAcquire()) throw new ResponseStatusException(HttpStatus.TOO_MANY_REQUESTS, "triage rate limit exceeded");
        if (!circuitBreaker.allowRequest()) throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE, "inference circuit is open");
    }
    public void success() { circuitBreaker.recordSuccess(); }
    public void failure() { circuitBreaker.recordFailure(); }
}
