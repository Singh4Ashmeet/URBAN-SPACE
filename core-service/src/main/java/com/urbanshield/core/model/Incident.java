package com.urbanshield.core.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.OffsetDateTime;
import lombok.Getter;
import lombok.Setter;
import org.locationtech.jts.geom.Point;

@Entity
@Table(name = "incidents")
@Getter
@Setter
public class Incident {

  @Id
  @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;

  @Column(nullable = false)
  private String title;

  private String description;

  @Column(name = "incident_type", nullable = false)
  @Enumerated(EnumType.STRING)
  private IncidentType incidentType;

  @Column(nullable = false)
  private Integer severity;

  @Column(nullable = false, columnDefinition = "geometry(Point,4326)")
  private Point location;

  @Column(nullable = false)
  private Double latitude;

  @Column(nullable = false)
  private Double longitude;

  @Column(nullable = false)
  @Enumerated(EnumType.STRING)
  private IncidentStatus status = IncidentStatus.REPORTED;

  @Column(name = "reported_at", nullable = false, insertable = false, updatable = false)
  private OffsetDateTime reportedAt;

  @Column(name = "updated_at", nullable = false)
  private OffsetDateTime updatedAt;
}
