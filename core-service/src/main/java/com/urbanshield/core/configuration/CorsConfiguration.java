package com.urbanshield.core.configuration;

import java.util.List;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;
import org.springframework.lang.NonNull;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
public class CorsConfiguration implements WebMvcConfigurer {

  private final List<String> allowedOrigins;

  public CorsConfiguration(
      @Value("${app.cors.allowed-origins:http://localhost:3000,http://localhost:8000}") List<String> allowedOrigins) {
    this.allowedOrigins = allowedOrigins;
  }

  @Override
  @SuppressWarnings("null")
  public void addCorsMappings(@NonNull CorsRegistry registry) {
    String[] origins = allowedOrigins.toArray(String[]::new);
    registry.addMapping("/**")
        .allowedOrigins(origins)
        .allowedMethods("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")
        .allowedHeaders("*");
  }
}
