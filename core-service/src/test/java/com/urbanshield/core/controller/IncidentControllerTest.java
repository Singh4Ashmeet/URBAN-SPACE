package com.urbanshield.core.controller;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.urbanshield.core.dto.IncidentRequest;
import com.urbanshield.core.dto.IncidentResponse;
import com.urbanshield.core.dto.IncidentStatusUpdateRequest;
import com.urbanshield.core.dto.IncidentSummaryResponse;
import com.urbanshield.core.model.IncidentStatus;
import com.urbanshield.core.model.IncidentType;
import com.urbanshield.core.service.IncidentEventService;
import com.urbanshield.core.service.IncidentService;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.data.domain.PageImpl;
import org.springframework.http.MediaType;
import org.springframework.lang.NonNull;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.util.Assert;

@WebMvcTest(IncidentController.class)
@SuppressWarnings("null")
class IncidentControllerTest {

  @Autowired
  private MockMvc mockMvc;

  @Autowired
  private ObjectMapper objectMapper;

  @MockBean
  private IncidentService incidentService;

  @MockBean
  private IncidentEventService incidentEventService;

  @Test
  void listReturnsIncidents() throws Exception {
    IncidentService service = required(incidentService);
    MockMvc mvc = required(mockMvc);
    Mockito.when(service.findIncidents(any(), any(), any(), any(), any()))
        .thenReturn(new PageImpl<>(List.of(response())));

    mvc.perform(get("/api/core/incidents"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.content[0].title").value("Demo"));
  }

  @Test
  void createReturnsCreatedIncident() throws Exception {
    IncidentService service = required(incidentService);
    MockMvc mvc = required(mockMvc);
    ObjectMapper mapper = required(objectMapper);
    Mockito.when(service.createIncident(any())).thenReturn(response());

    mvc.perform(post("/api/core/incidents")
            .contentType(required(MediaType.APPLICATION_JSON))
            .content(mapper.writeValueAsString(request())))
        .andExpect(status().isCreated())
        .andExpect(jsonPath("$.id").value(1));
  }

  @Test
  void validationErrorsReturnBadRequest() throws Exception {
    MockMvc mvc = required(mockMvc);
    ObjectMapper mapper = required(objectMapper);
    IncidentRequest invalid = new IncidentRequest("", null, IncidentType.ACCIDENT, 6, null, 100.0, 200.0);

    mvc.perform(post("/api/core/incidents")
            .contentType(required(MediaType.APPLICATION_JSON))
            .content(mapper.writeValueAsString(invalid)))
        .andExpect(status().isBadRequest());
  }

  @Test
  void updateStatusReturnsIncident() throws Exception {
    IncidentService service = required(incidentService);
    MockMvc mvc = required(mockMvc);
    ObjectMapper mapper = required(objectMapper);
    Mockito.when(service.updateStatus(eq(1L), any())).thenReturn(response());

    mvc.perform(patch("/api/core/incidents/1/status")
            .contentType(required(MediaType.APPLICATION_JSON))
            .content(mapper.writeValueAsString(new IncidentStatusUpdateRequest(IncidentStatus.RESOLVED))))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.status").value("REPORTED"));
  }

  @Test
  void deleteReturnsNoContent() throws Exception {
    required(mockMvc).perform(delete("/api/core/incidents/1"))
        .andExpect(status().isNoContent());
  }

  @Test
  void nearbyReturnsIncidents() throws Exception {
    IncidentService service = required(incidentService);
    MockMvc mvc = required(mockMvc);
    Mockito.when(service.findNearby(28.6, 77.2, 1000.0)).thenReturn(List.of(response()));

    mvc.perform(get("/api/core/incidents/nearby")
            .param("latitude", "28.6")
            .param("longitude", "77.2")
            .param("radiusMeters", "1000"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$[0].title").value("Demo"));
  }

  @Test
  void summaryReturnsStats() throws Exception {
    IncidentService service = required(incidentService);
    MockMvc mvc = required(mockMvc);
    Mockito.when(service.summarize())
        .thenReturn(new IncidentSummaryResponse(2, 1, 1, Map.of("ACCIDENT", 2L), Map.of("REPORTED", 1L), Map.of(3, 2L), 3.0));

    mvc.perform(get("/api/core/incidents/summary"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.totalIncidents").value(2));
  }

  @NonNull
  private IncidentRequest request() {
    return new IncidentRequest("Demo", "Description", IncidentType.ACCIDENT, 3, IncidentStatus.REPORTED, 28.6, 77.2);
  }

  @NonNull
  private IncidentResponse response() {
    return new IncidentResponse(1L, "Demo", "Description", IncidentType.ACCIDENT, 3, IncidentStatus.REPORTED, 28.6, 77.2, OffsetDateTime.now(), OffsetDateTime.now());
  }

  @NonNull
  private static <T> T required(T value) {
    Assert.notNull(value, "Injected test dependency must not be null");
    return value;
  }
}
