package com.urbanshield.core.mapper;

import com.urbanshield.core.dto.IncidentRequest;
import com.urbanshield.core.dto.IncidentResponse;
import com.urbanshield.core.model.Incident;
import com.urbanshield.core.model.IncidentStatus;
import java.time.OffsetDateTime;
import org.locationtech.jts.geom.Coordinate;
import org.locationtech.jts.geom.GeometryFactory;
import org.locationtech.jts.geom.PrecisionModel;
import org.springframework.stereotype.Component;

@Component
public class IncidentMapper {

  private final GeometryFactory geometryFactory = new GeometryFactory(new PrecisionModel(), 4326);

  public Incident toEntity(IncidentRequest request) {
    Incident incident = new Incident();
    updateEntity(incident, request);
    if (incident.getUpdatedAt() == null) {
      incident.setUpdatedAt(OffsetDateTime.now());
    }
    return incident;
  }

  public void updateEntity(Incident incident, IncidentRequest request) {
    incident.setTitle(request.title().trim());
    incident.setDescription(request.description());
    incident.setIncidentType(request.incidentType());
    incident.setSeverity(request.severity());
    incident.setStatus(request.status() == null ? IncidentStatus.REPORTED : request.status());
    incident.setLatitude(request.latitude());
    incident.setLongitude(request.longitude());
    incident.setLocation(geometryFactory.createPoint(new Coordinate(request.longitude(), request.latitude())));
    incident.getLocation().setSRID(4326);
    incident.setUpdatedAt(OffsetDateTime.now());
  }

  public IncidentResponse toResponse(Incident incident) {
    return new IncidentResponse(
        incident.getId(),
        incident.getTitle(),
        incident.getDescription(),
        incident.getIncidentType(),
        incident.getSeverity(),
        incident.getStatus(),
        incident.getLatitude(),
        incident.getLongitude(),
        incident.getReportedAt(),
        incident.getUpdatedAt());
  }
}
