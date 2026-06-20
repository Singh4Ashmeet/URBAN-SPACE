package com.urbanshield.core.controller;

import com.urbanshield.core.dto.IncidentRequest;
import com.urbanshield.core.dto.IncidentResponse;
import com.urbanshield.core.dto.IncidentStatusUpdateRequest;
import com.urbanshield.core.dto.IncidentSummaryResponse;
import com.urbanshield.core.model.IncidentStatus;
import com.urbanshield.core.model.IncidentType;
import com.urbanshield.core.service.IncidentEventService;
import com.urbanshield.core.service.IncidentService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import java.util.List;
import java.util.Objects;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.lang.NonNull;
import org.springframework.lang.Nullable;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

@RestController
@RequestMapping("/api/core/incidents")
@Validated
public class IncidentController {

  private final IncidentService incidentService;
  private final IncidentEventService incidentEventService;

  public IncidentController(IncidentService incidentService, IncidentEventService incidentEventService) {
    this.incidentService = incidentService;
    this.incidentEventService = incidentEventService;
  }

  @GetMapping
  public Page<IncidentResponse> list(
      @Nullable @RequestParam(required = false) IncidentStatus status,
      @Nullable @RequestParam(required = false) IncidentType incidentType,
      @Nullable @RequestParam(required = false) @Min(1) @Max(5) Integer minimumSeverity,
      @Nullable @RequestParam(required = false) @Min(1) @Max(5) Integer maximumSeverity,
      @RequestParam(defaultValue = "0") @Min(0) int page,
      @RequestParam(defaultValue = "50") @Min(1) @Max(100) int size,
      @NonNull @RequestParam(defaultValue = "reportedAt") String sortBy,
      @NonNull @RequestParam(defaultValue = "desc") String direction) {
    Sort.Direction resolvedDirection = sortDirection(direction);
    String resolvedSort = safeSort(sortBy);
    Pageable pageable = PageRequest.of(page, size, Sort.by(resolvedDirection, resolvedSort));
    return incidentService.findIncidents(status, incidentType, minimumSeverity, maximumSeverity, pageable);
  }

  @GetMapping("/{id}")
  public IncidentResponse get(@PathVariable long id) {
    return incidentService.getIncident(id);
  }

  @PostMapping
  public ResponseEntity<IncidentResponse> create(@Nullable @Valid @RequestBody IncidentRequest request) {
    IncidentRequest incidentRequest = requireBody(request);
    return ResponseEntity.status(HttpStatus.CREATED).body(incidentService.createIncident(incidentRequest));
  }

  @PutMapping("/{id}")
  public IncidentResponse update(@PathVariable long id, @Nullable @Valid @RequestBody IncidentRequest request) {
    IncidentRequest incidentRequest = requireBody(request);
    return incidentService.updateIncident(id, incidentRequest);
  }

  @PatchMapping("/{id}/status")
  public IncidentResponse updateStatus(@PathVariable long id, @Nullable @Valid @RequestBody IncidentStatusUpdateRequest request) {
    IncidentStatusUpdateRequest statusRequest = requireBody(request);
    return incidentService.updateStatus(id, statusRequest);
  }

  @DeleteMapping("/{id}")
  public ResponseEntity<Void> delete(@PathVariable long id) {
    incidentService.deleteIncident(id);
    return ResponseEntity.noContent().build();
  }

  @GetMapping("/nearby")
  public List<IncidentResponse> nearby(
      @RequestParam @DecimalMin("-90.0") @DecimalMax("90.0") double latitude,
      @RequestParam @DecimalMin("-180.0") @DecimalMax("180.0") double longitude,
      @RequestParam @DecimalMin("1.0") double radiusMeters) {
    return incidentService.findNearby(latitude, longitude, radiusMeters);
  }

  @GetMapping("/summary")
  public IncidentSummaryResponse summary() {
    return incidentService.summarize();
  }

  @GetMapping("/events")
  public SseEmitter events() {
    return incidentEventService.subscribe();
  }

  @NonNull
  private Sort.Direction sortDirection(@NonNull String direction) {
    return "asc".equalsIgnoreCase(direction) ? Sort.Direction.ASC : Sort.Direction.DESC;
  }

  @NonNull
  private String safeSort(@NonNull String sortBy) {
    return switch (sortBy) {
      case "severity", "title", "reportedAt" -> sortBy;
      default -> "reportedAt";
    };
  }

  @NonNull
  private static <T> T requireBody(@Nullable T body) {
    return Objects.requireNonNull(body, "Request body must not be null");
  }
}
