# ROADGUARD AI — API Endpoint Specification

The FastAPI service exposes RESTful endpoints for camera configuration, video management, traffic metric querying, violation retrieval, license plate records, surrogate safety events, explainable risk scores, and simulated e-Challan management.

## Endpoints Summary

### System & Health
- `GET /health`
  - Returns overall platform health, API version, environment, and DB status.

### Camera Configuration
- `GET /cameras`
  - Lists registered camera scene configurations.
- `POST /cameras`
  - Upserts camera configuration (ROIs, counting lines, stop lines, legal directions).
- `GET /cameras/{camera_id}`
  - Retrieves configuration for a specific camera.

### Video Ingestion & Pipeline
- `GET /videos`
  - Lists processed or ingested video files.
- `POST /videos`
  - Registers new video file metadata.
- `POST /analysis/start`
  - Triggers asynchronous computer vision pipeline processing.

### Traffic Intelligence
- `GET /traffic/metrics`
  - Returns traffic density, total volume, and directional inflow/outflow metrics.

### Violation Management
- `GET /violations`
  - Filters and lists detected violations (`WRONG_WAY`, `LANE_VIOLATION`, `RED_LIGHT`, `HELMET`, `TRIPLE_RIDING`).

### Automatic Number Plate Recognition (ANPR)
- `GET /plates`
  - Lists license plate detections with OCR confidence scores and temporal consensus counts.

### Surrogate Safety Measures (TTC & PET)
- `GET /safety/events`
  - Retrieves near-miss Time-to-Collision (TTC) and Post-Encroachment Time (PET) events.

### Explainable Risk Score
- `GET /risk/current`
  - Returns latest 0-100 risk score and indicator contribution breakdown for a camera.
- `GET /risk/history`
  - Returns historical risk scores for time-series chart rendering.

### Simulated e-Challan Module
- `GET /challans`
  - Lists generated e-Challans.
- `POST /challans`
  - Generates a new simulated e-Challan from a confirmed violation.
