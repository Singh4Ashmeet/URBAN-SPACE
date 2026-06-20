package com.urbanshield.core.dto;

import com.urbanshield.core.model.IncidentStatus;
import jakarta.validation.constraints.NotNull;

public record IncidentStatusUpdateRequest(@NotNull IncidentStatus status) {
}
