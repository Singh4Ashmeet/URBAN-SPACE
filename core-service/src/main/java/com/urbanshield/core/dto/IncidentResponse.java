package com.urbanshield.core.dto;

import com.urbanshield.core.model.IncidentStatus;
import com.urbanshield.core.model.IncidentType;
import java.time.OffsetDateTime;

public record IncidentResponse(
    Long id,
    String title,
    String description,
    IncidentType incidentType,
    Integer severity,
    IncidentStatus status,
    Double latitude,
    Double longitude,
    OffsetDateTime reportedAt,
    OffsetDateTime updatedAt) {
}
