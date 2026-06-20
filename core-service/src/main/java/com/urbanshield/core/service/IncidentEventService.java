package com.urbanshield.core.service;

import com.urbanshield.core.dto.IncidentResponse;
import java.io.IOException;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

@Service
public class IncidentEventService {

  private final List<SseEmitter> emitters = new CopyOnWriteArrayList<>();

  public SseEmitter subscribe() {
    SseEmitter emitter = new SseEmitter(0L);
    emitters.add(emitter);
    emitter.onCompletion(() -> emitters.remove(emitter));
    emitter.onTimeout(() -> emitters.remove(emitter));
    emitter.onError(error -> emitters.remove(emitter));
    return emitter;
  }

  public void publish(String action, IncidentResponse incident) {
    for (SseEmitter emitter : emitters) {
      try {
        emitter.send(SseEmitter.event().name("incident").data(new IncidentEvent(action, incident)));
      } catch (IOException ex) {
        emitters.remove(emitter);
      }
    }
  }

  private record IncidentEvent(String action, IncidentResponse incident) {
  }
}
