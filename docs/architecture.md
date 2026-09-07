# ROADGUARD AI — System Architecture & Design Specification

## Overview
RoadGuard AI is a modular, high-throughput road safety and traffic intelligence system that processes video streams from CCTV and traffic cameras to derive real-time insights, traffic density, directional flow, traffic violations, license plate recognition (ANPR), surrogate safety measures (TTC/PET), and an explainable 0–100 risk score.

```
+-----------------------------------------------------------------------------------+
|                                 VIDEO INGESTION                                   |
|                          CCTV / RTSP / MP4 File Decoding                          |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                              YOLO OBJECT DETECTION                                |
|   (Cars, Trucks, Buses, Motorcycles, Auto-Rickshaws, Pedestrians, Traffic Lights) |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                           MULTI-OBJECT TRACKING (MOT)                             |
|                           ByteTrack / BoT-SORT Engine                             |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                        TRAJECTORY & KINEMATICS ENGINE                             |
|                  Smooth Center Trajectories, Speed & Vector Estimation             |
+-----------------------------------------------------------------------------------+
                                          |
       +----------------------------------+----------------------------------+
       |                                  |                                  |
       v                                  v                                  v
+---------------+                +------------------+              +--------------------+
| TRAFFIC FLOW  |                | VIOLATION ENGINE |              | ANPR MODULE        |
|  & DENSITY    |                | (Wrong-way, Lane,|              | (OCR, Multi-frame  |
| (ROI Polygons,|                | Red-light, Helmet|              |  Temporal Consensus|
| Counting Line)|                | Triple Riding)   |              |  Privacy Guarded)  |
+---------------+                +------------------+              +--------------------+
       |                                  |                                  |
       +----------------------------------+----------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                     SURROGATE SAFETY INDICATORS (TTC / PET)                       |
|           Interaction Pair Search, Collision Course Detection, PET Gap           |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                      EXPLAINABLE 0–100 RISK SCORE ENGINE                          |
|         Multi-factor Aggregation, Weighted Contribution, Heatmap Matrix           |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                             FASTAPI BACKEND SERVICE                               |
|                     PostgreSQL Database + Alembic Migrations                      |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                       REACT + TYPESCRIPT DASHBOARD UI                             |
|          Live Analytics, Violation Evidence, Risk Breakdown, Experiments           |
+-----------------------------------------------------------------------------------+
```

## Architectural Modules

### 1. Ingestion Layer (`ai/detection`)
- Ingests MP4/RTSP video streams frame by frame.
- High-res frame extraction with frame drop protection for uninterrupted analysis.

### 2. Multi-Class Object Detection (`ai/detection`)
- Fine-tuned Ultralytics YOLO model detecting 9+ road user classes.
- Native support for Indian urban traffic entities (auto-rickshaws, high motorcycle density).

### 3. Multi-Object Tracking (`ai/tracking`)
- Persistent `track_id` assignments using ByteTrack / BoT-SORT algorithms.
- Kalman filter motion prediction preventing track swapping during visual occlusion.

### 4. Trajectory & Motion Analysis (`ai/trajectory`)
- Derives frame-by-frame velocity vectors `(vx, vy)` and movement angles.
- Moving-average spatial trajectory smoothing.

### 5. Scene-Aware Rule Engine (`ai/violations`)
- Scene configuration defines ROI lane polygons, legal motion vectors, signal stop lines.
- Temporal persistence requirement (e.g., minimum 5 consecutive frames) prevents false positives caused by detection jitter.

### 6. ANPR Engine (`ai/anpr`)
- Vehicle crop -> Plate box detection -> Preprocessing -> OCR text extraction -> Multi-frame temporal consensus.
- Privacy minimized: no facial recognition, strict evidence retention policies.

### 7. Surrogate Safety Measures (`ai/safety`)
- Time-to-Collision (TTC) & Post-Encroachment Time (PET) evaluation.
- Identifies near-miss interaction pairs without claiming guaranteed accident prediction.

### 8. Explainable 0–100 Risk Engine (`ai/risk`)
- Aggregates multi-indicator normalized values over a 60-second sliding window.
- Computes contribution breakdown per indicator for full transparency.
