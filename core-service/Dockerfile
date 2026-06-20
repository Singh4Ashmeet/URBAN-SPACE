FROM maven:3.9.11-eclipse-temurin-21 AS build
WORKDIR /workspace
COPY pom.xml .
RUN mvn -B dependency:go-offline
COPY src ./src
RUN mvn -B package

FROM eclipse-temurin:21-jre
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends wget \
    && rm -rf /var/lib/apt/lists/* \
    && addgroup --system urbanshield \
    && adduser --system --ingroup urbanshield urbanshield
COPY --from=build /workspace/target/core-service-0.1.0.jar app.jar
USER urbanshield
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
