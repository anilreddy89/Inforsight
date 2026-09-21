package com.inforsight.controlplane.streaming;

import java.util.List;

/** Optional bounded batch seam for handlers that preserve ordered commit semantics. */
public interface BatchStreamingEventHandler extends StreamingEventHandler {
    void handleBatch(List<StreamingRecord> records);

    record StreamingRecord(String topic, String key, String value) {}
}
