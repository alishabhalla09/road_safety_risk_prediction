# ROADGUARD AI — Research & Experimentation Plan

This document outlines the 8 core research experiments (R1–R8) designed to evaluate and benchmark the integrated RoadGuard AI pipeline.

## Experiment Matrix

| ID | Title | Hypothesis / Objective | Target Metrics |
|---|---|---|---|
| **R1** | Detection Model Benchmark | Compare YOLO variants (YOLOv8s vs YOLOv8m vs YOLOv8l) on mixed traffic. | mAP50, mAP50-95, FPS, Precision, Recall |
| **R2** | Tracking Algorithm Evaluation | Evaluate ByteTrack vs BoT-SORT on dense urban traffic with high occlusion. | IDF1, HOTA, MOTA, ID Switches |
| **R3** | Trajectory Smoothing Analysis | Assess raw bounding box center vs moving average vs Kalman filter trajectory smoothing. | Trajectory Error (RMSE), Jitter Index |
| **R4** | Violation Persistence Tuning | Evaluate temporal threshold (1-10 frames) on false positive violation rates. | Precision, Recall, False Positive Rate |
| **R5** | TTC / PET Sensitivity | Test Time-to-Collision thresholds (1.0s to 3.0s) against manual near-miss labels. | Sensitivity, Specificity, Agreement Index |
| **R6** | Risk Score Ablation | Measure risk sensitivity across indicator sets: Density vs Density+Violations vs Full. | Risk Variance, Explainability Score |
| **R7** | Indian Domain Benchmark | Compare performance on Indian urban footage (heterogeneous traffic, Rickshaws, Motorcycles) vs Standard Datasets. | Class Precision, Small-object Recall |
| **R8** | Environmental Robustness | Evaluate pipeline resilience across lighting (Day vs Night), weather, and camera tilt angles. | Accuracy Drop %, FPS Stability |

## Evaluation Workflow
Each experiment run logs data directly into the `experiments` and `model_versions` database tables, capturing parameter configurations, evaluation metrics, and qualitative notes.
