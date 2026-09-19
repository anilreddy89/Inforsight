package com.inforsight.controlplane.resilience;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;

/** Fail-fast circuit breaker; it never retries or authorizes a decision itself. */
public final class CircuitBreaker {
    public enum State { CLOSED, OPEN, HALF_OPEN }
    private final int failureThreshold;
    private final Duration openDuration;
    private final Clock clock;
    private int failures;
    private State state = State.CLOSED;
    private Instant openedAt;

    public CircuitBreaker(int failureThreshold, Duration openDuration) { this(failureThreshold, openDuration, Clock.systemUTC()); }
    CircuitBreaker(int failureThreshold, Duration openDuration, Clock clock) {
        if (failureThreshold <= 0 || openDuration.isNegative() || openDuration.isZero()) throw new IllegalArgumentException("invalid circuit-breaker configuration");
        this.failureThreshold = failureThreshold;
        this.openDuration = openDuration;
        this.clock = clock;
    }
    public synchronized boolean allowRequest() {
        if (state == State.CLOSED) return true;
        if (state == State.OPEN && openedAt.plus(openDuration).isBefore(Instant.now(clock))) { state = State.HALF_OPEN; return true; }
        return state == State.HALF_OPEN;
    }
    public synchronized void recordSuccess() { failures = 0; state = State.CLOSED; openedAt = null; }
    public synchronized void recordFailure() { if (++failures >= failureThreshold) { state = State.OPEN; openedAt = Instant.now(clock); } }
    public synchronized State state() { return state; }
}
