package com.inforsight.controlplane.resilience;

import java.time.Duration;
import java.util.concurrent.atomic.AtomicLong;

/** Small deterministic token bucket used at the service boundary. */
public final class RateLimiter {
    private final long capacity;
    private final double refillPerNano;
    private double tokens;
    private long lastNanos;
    private final AtomicLong rejected = new AtomicLong();

    public RateLimiter(long capacity, Duration window) {
        if (capacity <= 0 || window.isZero() || window.isNegative()) throw new IllegalArgumentException("invalid rate-limit configuration");
        this.capacity = capacity;
        this.refillPerNano = capacity / (double) window.toNanos();
        this.tokens = capacity;
        this.lastNanos = System.nanoTime();
    }

    public synchronized boolean tryAcquire() {
        long now = System.nanoTime();
        tokens = Math.min(capacity, tokens + (now - lastNanos) * refillPerNano);
        lastNanos = now;
        if (tokens < 1.0) { rejected.incrementAndGet(); return false; }
        tokens -= 1.0;
        return true;
    }

    public long rejectedCount() { return rejected.get(); }
}
