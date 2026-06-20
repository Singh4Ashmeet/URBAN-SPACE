package com.urbanshield.core.repository;

import com.urbanshield.core.model.Incident;
import com.urbanshield.core.model.IncidentStatus;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

@Repository
public interface IncidentRepository extends JpaRepository<Incident, Long>, JpaSpecificationExecutor<Incident> {

  long countByStatus(IncidentStatus status);

  @Query("select i.incidentType, count(i) from Incident i group by i.incidentType")
  List<Object[]> countGroupedByType();

  @Query("select i.status, count(i) from Incident i group by i.status")
  List<Object[]> countGroupedByStatus();

  @Query("select i.severity, count(i) from Incident i group by i.severity")
  List<Object[]> countGroupedBySeverity();

  @Query("select coalesce(avg(i.severity), 0) from Incident i")
  double averageSeverity();

  @Query(
      value = """
          select * from incidents
          where ST_DWithin(
            location::geography,
            ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)::geography,
            :radiusMeters
          )
          order by reported_at desc
          """,
      nativeQuery = true)
  List<Incident> findNearby(
      @Param("latitude") double latitude,
      @Param("longitude") double longitude,
      @Param("radiusMeters") double radiusMeters);
}
