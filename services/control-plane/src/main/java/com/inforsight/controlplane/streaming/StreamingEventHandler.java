package com.inforsight.controlplane.streaming;

/** Bounded handler for validated streaming envelopes. */
@FunctionalInterface
public interface StreamingEventHandler {
    /** Return true when the event is accepted, false for a duplicate. */
    boolean handle(String topic, String key, String value);
}
