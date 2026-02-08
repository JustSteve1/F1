# Video Management Skill

## Function: Upload Video
This function allows the agent (or user via dashboard) to upload a video file to the F1 Data Library.

### Usage
- **Endpoint**: `POST /api/factory/upload`
- **Parameters**: 
    - `file`: The video file (multipart/form-data).
    - `type`: The category of the video.
        - `REF`: Reference Lap (F1) -> `uploads/reference/`
        - `SIM`: Simulator Lap (User) -> `uploads/sim/`
        - `DASHBOARD`: Dashboard Upload -> `uploads/dashboard/` (Auto-names with Timestamp)

### Behavior
- **Dashboard Upload**: When `type=DASHBOARD` is used, the system automatically prepends the current timestamp (`YYYYMMDD_HHMMSS_`) to the filename to ensure uniqueness and traceability.
- **Return**: A Google Cloud Storage URI (`gs://f1-data-library/...`).

### Example (Curl)
```bash
curl -X POST "http://localhost:8000/api/factory/upload?type=DASHBOARD" \
  -F "file=@/path/to/video.mp4"
```

### Agent Integration
To use this skill programmatically:
1.  Identify the video source type.
2.  Call the API with the appropriate `type`.
3.  Store the returned `uri` for downstream tasks (Sync, Comparison).
