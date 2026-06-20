package com.urbanshield.core.dto;

import java.util.Map;

public record IncidentSummaryResponse(
    long totalIncidents,
    long activeIncidents,
    long resolvedIncidents,
    Map<String, Long> byType,
    Map<String, Long> byStatus,
    Map<Integer, Long> bySeverity,
    double averageSeverity) {
}
