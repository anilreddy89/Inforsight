package com.inforsight.controlplane.domain;

import java.util.List;

public record EligibilityResult(String actionType, boolean eligible, List<String> reasons) {
    public EligibilityResult {
        reasons = List.copyOf(reasons);
    }
}
