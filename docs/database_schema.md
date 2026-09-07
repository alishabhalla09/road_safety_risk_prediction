# ROADGUARD AI — Database Schema Specification

The PostgreSQL database stores video metadata, frame-level object detections, persistent object trajectories, aggregated traffic flow, violation incidents, ANPR extractions, simulated e-Challan records, surrogate safety events, and explainable risk scores.

## Table Inventory

### 1. `videos`
- `id` (PK, INT): Video record ID
- `camera_id` (VARCHAR): Camera identifier
- `filename` (VARCHAR): Video source filename
- `source` (VARCHAR): File path or stream URI
- `fps` (FLOAT): Frames per second
- `width` (INT): Frame width in pixels
- `height` (INT): Frame height in pixels
- `duration` (FLOAT): Duration in seconds
- `created_at` (TIMESTAMP): Ingestion timestamp

### 2. `detections`
- `id` (PK, INT): Detection record ID
- `video_id` (FK -> videos.id): Parent video reference
- `frame_no` (INT): Frame index
- `timestamp` (FLOAT): Video timestamp in seconds
- `class_name` (VARCHAR): Detected object class
- `confidence` (FLOAT): Detection confidence score [0.0 - 1.0]
- `x1, y1, x2, y2` (FLOAT): Bounding box coordinates

### 3. `tracks`
- `id` (PK, INT): Track record ID
- `video_id` (FK -> videos.id): Parent video
- `camera_id` (VARCHAR): Camera ID
- `track_id` (INT): Tracker persistent ID
- `class_name` (VARCHAR): Vehicle/Road-user class
- `first_seen` (FLOAT): Start timestamp
- `last_seen` (FLOAT): End timestamp

### 4. `trajectory_points`
- `id` (PK, INT): Trajectory point ID
- `track_ref` (FK -> tracks.id): Track reference
- `timestamp` (FLOAT): Point timestamp
- `x, y` (FLOAT): Bottom-center spatial coordinate
- `vx, vy` (FLOAT): Estimated velocity components
- `direction` (VARCHAR): Computed motion direction
- `lane_id` (INT): Current lane association

### 5. `traffic_metrics`
- `id` (PK, INT): Metric record ID
- `camera_id` (VARCHAR): Camera ID
- `timestamp` (TIMESTAMP): Measurement timestamp
- `vehicle_count` (INT): Active vehicle count
- `density` (FLOAT): Occupancy ratio [0.0 - 1.0]
- `flow_in` (INT): Vehicles crossed inflow line
- `flow_out` (INT): Vehicles crossed outflow line
- `class_counts` (JSON): Per-class breakdown dict

### 6. `camera_configs`
- `id` (PK, INT): Config record ID
- `camera_id` (VARCHAR, UNIQUE): Unique camera key
- `name` (VARCHAR): Camera descriptive name
- `lanes` (JSON): ROI lane polygons & legal directions
- `directions` (JSON): Allowed directional angles
- `counting_lines` (JSON): Flow counting line segments
- `stop_lines` (JSON): Red-light stop lines
- `zones` (JSON): Conflict & junction polygons
- `calibration` (JSON): Pixels-per-meter scale & perspective matrix
- `signal_config` (JSON): Traffic signal ROI & state mappings
- `updated_at` (TIMESTAMP): Configuration modification date

### 7. `violations`
- `id` (PK, INT): Violation record ID
- `camera_id` (VARCHAR): Camera ID
- `track_id` (FK -> tracks.id): Associated vehicle track
- `type` (VARCHAR): Violation classification (`WRONG_WAY`, `LANE_VIOLATION`, `RED_LIGHT`, `HELMET`, `TRIPLE_RIDING`)
- `timestamp` (TIMESTAMP): Incident timestamp
- `confidence` (FLOAT): Event confidence
- `reason` (TEXT): Detailed rule explanation
- `evidence_id` (VARCHAR): Frame image key
- `status` (VARCHAR): Life-cycle status

### 8. `vehicle_plates`
- `id` (PK, INT): Plate record ID
- `track_id` (FK -> tracks.id, UNIQUE): Associated track
- `plate_text` (VARCHAR): Recognized registration number
- `ocr_confidence` (FLOAT): OCR score
- `frame_count` (INT): Consensus frame sample count
- `best_evidence_id` (VARCHAR): Best image key

### 9. `challans`
- `id` (PK, INT): Challan ID
- `violation_id` (FK -> violations.id, UNIQUE): Source violation
- `challan_number` (VARCHAR, UNIQUE): Generated reference code
- `vehicle_number` (VARCHAR): License plate text
- `type` (VARCHAR): Offense category
- `timestamp` (TIMESTAMP): Generation date
- `status` (VARCHAR): (`GENERATED`, `UNDER_REVIEW`, `RESOLVED`, `CANCELLED`)
- `notes` (TEXT): Administrative notes

### 10. `safety_events`
- `id` (PK, INT): Safety event ID
- `camera_id` (VARCHAR): Camera ID
- `track_a` (INT): Vehicle A track ID
- `track_b` (INT): Vehicle B track ID
- `type` (VARCHAR): `NEAR_MISS_TTC` or `PET_CONFLICT`
- `timestamp` (TIMESTAMP): Event timestamp
- `ttc` (FLOAT): Time-to-collision in seconds
- `pet` (FLOAT): Post-encroachment time in seconds
- `separation` (FLOAT): Spatial gap in meters
- `quality` (VARCHAR): Indicator quality tag

### 11. `risk_scores`
- `id` (PK, INT): Risk score ID
- `camera_id` (VARCHAR): Camera ID
- `timestamp` (TIMESTAMP): Assessment timestamp
- `score` (FLOAT): Aggregated risk index [0.0 - 100.0]
- `category` (VARCHAR): `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`

### 12. `risk_contributions`
- `id` (PK, INT): Contribution ID
- `risk_score_id` (FK -> risk_scores.id): Parent risk score
- `indicator` (VARCHAR): Indicator name
- `normalized_value` (FLOAT): Normalized metric [0.0 - 1.0]
- `weight` (FLOAT): Indicator weight
- `contribution` (FLOAT): Sub-score contribution

### 13. `experiments`
- `id` (PK, INT): Experiment ID
- `name` (VARCHAR): Research experiment title
- `dataset` (VARCHAR): Target dataset name
- `model_version` (VARCHAR): Model checkpoint tag
- `parameters` (JSON): Hyperparameters & thresholds
- `metrics` (JSON): Evaluation metrics (mAP, IDF1, MAE)
- `notes` (TEXT): Experiment findings summary
- `created_at` (TIMESTAMP): Run date

### 14. `model_versions`
- `id` (PK, INT): Model version ID
- `model_name` (VARCHAR): Model architecture name
- `version` (VARCHAR): Version tag
- `dataset` (VARCHAR): Training dataset
- `metrics` (JSON): Benchmark performance results
- `created_at` (TIMESTAMP): Registration date
