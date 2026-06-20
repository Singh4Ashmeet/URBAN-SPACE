package com.urbanshield.core.dto;

import com.urbanshield.core.model.IncidentStatus;
import com.urbanshield.core.model.IncidentType;
import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

public record IncidentRequest(
    @NotBlank @Size(max = 180) String title,
    @Size(max = 2000) String description,
    @NotNull IncidentType incidentType,
    @NotNull @Min(1) @Max(5) Integer severity,
    IncidentStatus status,
    @NotNull @DecimalMin("-90.0") @DecimalMax("90.0") Double latitude,
    @NotNull @DecimalMin("-180.0") @DecimalMax("180.0") Double longitude) {
}
