package com.inforsight.controlplane.resilience;

import org.junit.jupiter.api.Test;

import java.time.Duration;

import static org.assertj.core.api.Assertions.assertThat;

class ResilienceTest {
    @Test
    void rateLimiterRejectsAfterBurst() {
        var limiter = new RateLimiter(2, Duration.ofDays(1));
        assertThat(limiter.tryAcquire()).isTrue();
        assertThat(limiter.tryAcquire()).isTrue();
        assertThat(limiter.tryAcquire()).isFalse();
        assertThat(limiter.rejectedCount()).isEqualTo(1);
    }

    @Test
    void circuitBreakerOpensAfterThresholdAndClosesAfterSuccess() {
        var breaker = new CircuitBreaker(2, Duration.ofSeconds(1));
        breaker.recordFailure();
        assertThat(breaker.allowRequest()).isTrue();
        breaker.recordFailure();
        assertThat(breaker.state()).isEqualTo(CircuitBreaker.State.OPEN);
        assertThat(breaker.allowRequest()).isFalse();
        breaker.recordSuccess();
        assertThat(breaker.state()).isEqualTo(CircuitBreaker.State.CLOSED);
    }
}
