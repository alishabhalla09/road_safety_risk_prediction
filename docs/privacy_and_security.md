# ROADGUARD AI — Privacy & Security Architecture

RoadGuard AI is designed with strict privacy preservation and security guidelines in mind.

## Privacy Directives & Safeguards

1. **No Facial Recognition:**
   - The vision pipeline detects pedestrians solely as bounding boxes (`x1, y1, x2, y2`).
   - Facial feature extraction, biometric indexing, or identity matching is strictly prohibited.

2. **ANPR Opt-in & Retention Minimization:**
   - License plate recognition (ANPR) is an optional module (`ANPR_ENABLED=False` by default in high-privacy modes).
   - License plate text is linked only to temporal vehicle tracks, not personal identifying databases.
   - Evidence crops containing license plates undergo retention minimization.

3. **Academic e-Challan Simulation Boundaries:**
   - The e-Challan generation workflow is an academic prototype for research evaluation.
   - It has no connectivity to law enforcement databases, motor vehicle registries, or payment gateways.
   - Watermarks explicitly label generated documents as: `ACADEMIC SIMULATION ONLY - NO LEGAL VALIDITY`.

4. **Surrogate Safety Estimations:**
   - TTC (Time-to-Collision) and PET (Post-Encroachment Time) estimates are decision-support indicators for traffic engineers.
   - They represent mathematical motion projections, not definitive evidence of reckless driving or accident fault.

## Security Architecture

1. **Input Validation:**
   - Strictly validated video upload file extensions (`.mp4`, `.avi`, `.mov`) and size limits.
   - Path traversal prevention on file storage paths.

2. **API Security & CORS:**
   - Configurable CORS origins preventing unauthorized cross-origin requests.
   - Schema validation via Pydantic v2 preventing SQL injection or payload tampering.
