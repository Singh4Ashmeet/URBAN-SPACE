package com.urbanshield.core.service;

import com.urbanshield.core.repository.IncidentRepository;
import com.urbanshield.core.dto.IncidentRequest;
import com.urbanshield.core.dto.IncidentResponse;
import com.urbanshield.core.dto.IncidentStatusUpdateRequest;
import com.urbanshield.core.dto.IncidentSummaryResponse;
import com.urbanshield.core.exception.ResourceNotFoundException;
import com.urbanshield.core.mapper.IncidentMapper;
import com.urbanshield.core.model.Incident;
import com.urbanshield.core.model.IncidentStatus;
import com.urbanshield.core.model.IncidentType;
import jakarta.persistence.criteria.Predicate;
import java.time.OffsetDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.lang.NonNull;
import org.springframework.lang.Nullable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.Assert;

@Service
@SuppressWarnings("null")
public class IncidentService {

  private final IncidentRepository incidentRepository;
  private final IncidentMapper incidentMapper;
  private final IncidentEventService incidentEventService;

  public IncidentService(
      IncidentRepository incidentRepository,
      IncidentMapper incidentMapper,
      IncidentEventService incidentEventService) {
    this.incidentRepository = incidentRepository;
    this.incidentMapper = incidentMapper;
    this.incidentEventService = incidentEventService;
  }

  public long countIncidents() {
    return incidentRepository.count();
  }

  @Transactional(readOnly = true)
  public Page<IncidentResponse> findIncidents(
      @Nullable IncidentStatus status,
      @Nullable IncidentType incidentType,
      @Nullable Integer minimumSeverity,
      @Nullable Integer maximumSeverity,
      @NonNull Pageable pageable) {
    return incidentRepository.findAll(specification(status, incidentType, minimumSeverity, maximumSeverity), pageable)
        .map(incidentMapper::toResponse);
  }

  @Transactional(readOnly = true)
  public IncidentResponse getIncident(long id) {
    Long incidentId = Long.valueOf(id);
    Optional<Incident> incident = incidentRepository.findById(incidentId);
    return incident
        .map(incidentMapper::toResponse)
        .orElseThrow(() -> new ResourceNotFoundException("Incident not found: " + incidentId));
  }

  @Transactional
  public IncidentResponse createIncident(@NonNull IncidentRequest request) {
    Incident entity = incidentMapper.toEntity(request);
    Incident saved = incidentRepository.save(entity);
    Assert.notNull(saved, "Saved incident must not be null");
    IncidentResponse response = incidentMapper.toResponse(saved);
    incidentEventService.publish("created", response);
    return response;
  }

  @Transactional
  public IncidentResponse updateIncident(long id, @NonNull IncidentRequest request) {
    Incident incident = findEntity(id);
    incidentMapper.updateEntity(incident, request);
    IncidentResponse response = incidentMapper.toResponse(incident);
    incidentEventService.publish("updated", response);
    return response;
  }

  @Transactional
  public IncidentResponse updateStatus(long id, @NonNull IncidentStatusUpdateRequest request) {
    Incident incident = findEntity(id);
    incident.setStatus(request.status());
    incident.setUpdatedAt(OffsetDateTime.now());
    IncidentResponse response = incidentMapper.toResponse(incident);
    incidentEventService.publish("status_updated", response);
    return response;
  }

  @Transactional
  public void deleteIncident(long id) {
    Incident incident = findEntity(id);
    IncidentResponse response = incidentMapper.toResponse(incident);
    incidentRepository.delete(incident);
    incidentEventService.publish("deleted", response);
  }

  @Transactional(readOnly = true)
  public List<IncidentResponse> findNearby(double latitude, double longitude, double radiusMeters) {
    return incidentRepository.findNearby(latitude, longitude, radiusMeters).stream()
        .map(incidentMapper::toResponse)
        .toList();
  }

  @Transactional(readOnly = true)
  public IncidentSummaryResponse summarize() {
    long total = incidentRepository.count();
    long resolved = incidentRepository.countByStatus(IncidentStatus.RESOLVED);
    long cancelled = incidentRepository.countByStatus(IncidentStatus.CANCELLED);
    long active = total - resolved - cancelled;
    return new IncidentSummaryResponse(
        total,
        active,
        resolved,
        enumCounts(incidentRepository.countGroupedByType()),
        enumCounts(incidentRepository.countGroupedByStatus()),
        severityCounts(incidentRepository.countGroupedBySeverity()),
        Math.round(incidentRepository.averageSeverity() * 100.0) / 100.0);
  }

  private Incident findEntity(long id) {
    Long incidentId = Long.valueOf(id);
    Optional<Incident> incident = incidentRepository.findById(incidentId);
    return incident
        .orElseThrow(() -> new ResourceNotFoundException("Incident not found: " + incidentId));
  }

  private Specification<Incident> specification(
      @Nullable IncidentStatus status,
      @Nullable IncidentType incidentType,
      @Nullable Integer minimumSeverity,
      @Nullable Integer maximumSeverity) {
    return (root, query, criteriaBuilder) -> {
      List<Predicate> predicates = new java.util.ArrayList<>();
      if (status != null) {
        predicates.add(criteriaBuilder.equal(root.get("status"), status));
      }
      if (incidentType != null) {
        predicates.add(criteriaBuilder.equal(root.get("incidentType"), incidentType));
      }
      if (minimumSeverity != null) {
        predicates.add(criteriaBuilder.greaterThanOrEqualTo(root.get("severity"), minimumSeverity));
      }
      if (maximumSeverity != null) {
        predicates.add(criteriaBuilder.lessThanOrEqualTo(root.get("severity"), maximumSeverity));
      }
      return criteriaBuilder.and(predicates.toArray(Predicate[]::new));
    };
  }

  private Map<String, Long> enumCounts(List<Object[]> rows) {
    Map<String, Long> counts = new LinkedHashMap<>();
    for (Object[] row : rows) {
      Object key = row[0];
      Object value = row[1];
      if (value instanceof Long count) {
        counts.put(String.valueOf(key), count);
      }
    }
    return counts;
  }

  private Map<Integer, Long> severityCounts(List<Object[]> rows) {
    Map<Integer, Long> counts = new LinkedHashMap<>();
    for (Object[] row : rows) {
      Object key = row[0];
      Object value = row[1];
      if (key instanceof Integer severity && value instanceof Long count) {
        counts.put(severity, count);
      }
    }
    return counts;
  }
}
