# Video Analysis Skill (Dashboard)

## Feature: Automated Dashboard Analysis
This skill is designed to process videos uploaded via the Factory Dashboard (`uploads/dashboard/`).

### Goal
To analyze the uploaded video and generate a summary of:
1.  **Video Metadata**: Duration, speed, 
2.  **Content Overview**: What is happening in the video (e.g., "Onboard lap of Monza", " Pit stop practice").
3.  **Key Events**: Timestamps of significant moments (e.g., "Start of lap", "Lock up at Turn 1").

### Workflow
1.  **Trigger**: User uploads a video on `/factory/dashboard`.
2.  **Process**:
    -   The system identifies the `gs://` URI from the upload response.
    -   (Future) A background job is triggered to pass this URI to gemini-3-flash-preview
    -   No other model should be used for this task, as gemini-3-flash-preview is the only model that supports video analysis in the 
3.  **Prompt Strategy**:
    > "Analyze this video located at {VIDEO_URI}. Provide a concise summary of the content, identify the track if applicable, and list any key driving events with timestamps."
    > "Analyse each second of the video and provide a summary of what is happening in the video at that second."
    > "Provide the output in a JSON format with the following structure:"
    > "{
    >   "track": "Autodromo Nazionale Monza",
    >   "driver": "Lewis Hamilton",
    >   "car": "Mercedes-AMG F1 W11 EQ Performance",
    >   "lap_time": "1:18.887",
    >   "data_points": [
    >     {"lap_time_s": 0, "speed_kmh": 295, "location": "Start/Finish Line"}}
    > for each second there be a datapoint that logs time, speed, location
    
- **Frontend**: `frontend/src/app/factory/dashboard/page.tsx`
- **Upload Path**: `gs://f1-data-library/uploads/dashboard/{TIMESTAMP}_{FILENAME}`

### Success Criteria
-   The user can upload a video.
-   The system acknowledges the upload.
-   (Future) The prompt calculates the metadata for every second and exports it into a json file

### Output Example

```json
{
  \"track\": \"Autodromo Nazionale Monza\",
  \"car_data\": [
    {\"lap_time_sec\": 0, \"speed_kmh\": 238},
    {\"lap_time_sec\": 1, \"speed_kmh\": 247},
    {\"lap_time_sec\": 2, \"speed_kmh\": 253},
    {\"lap_time_sec\": 3, \"speed_kmh\": 258},
    {\"lap_time_sec\": 4, \"speed_kmh\": 264},
    {\"lap_time_sec\": 5, \"speed_kmh\": 269},
    {\"lap_time_sec\": 6, \"speed_kmh\": 274},
    {\"lap_time_sec\": 7, \"speed_kmh\": 278},
    {\"lap_time_sec\": 8, \"speed_kmh\": 283},
    {\"lap_time_sec\": 9, \"speed_kmh\": 287},
    {\"lap_time_sec\": 10, \"speed_kmh\": 291},
    {\"lap_time_sec\": 11, \"speed_kmh\": 293},
    {\"lap_time_sec\": 12, \"speed_kmh\": 151},
    {\"lap_time_sec\": 13, \"speed_kmh\": 67},
    {\"lap_time_sec\": 14, \"speed_kmh\": 55},
    {\"lap_time_sec\": 15, \"speed_kmh\": 69},
    {\"lap_time_sec\": 16, \"speed_kmh\": 96},
    {\"lap_time_sec\": 17, \"speed_kmh\": 124},
    {\"lap_time_sec\": 18, \"speed_kmh\": 147},
    {\"lap_time_sec\": 19, \"speed_kmh\": 168},
    {\"lap_time_sec\": 20, \"speed_kmh\": 185},
    {\"lap_time_sec\": 21, \"speed_kmh\": 200},
    {\"lap_time_sec\": 22, \"speed_kmh\": 213},
    {\"lap_time_sec\": 23, \"speed_kmh\": 225},
    {\"lap_time_sec\": 24, \"speed_kmh\": 236},
    {\"lap_time_sec\": 25, \"speed_kmh\": 245},
    {\"lap_time_sec\": 26, \"speed_kmh\": 254},
    {\"lap_time_sec\": 27, \"speed_kmh\": 261},
    {\"lap_time_sec\": 28, \"speed_kmh\": 269},
    {\"lap_time_sec\": 29, \"speed_kmh\": 275},
    {\"lap_time_sec\": 30, \"speed_kmh\": 279},
    {\"lap_time_sec\": 31, \"speed_kmh\": 283},
    {\"lap_time_sec\": 32, \"speed_kmh\": 287},
    {\"lap_time_sec\": 33, \"speed_kmh\": 290},
    {\"lap_time_sec\": 34, \"speed_kmh\": 294},
    {\"lap_time_sec\": 35, \"speed_kmh\": 297},
    {\"lap_time_sec\": 36, \"speed_kmh\": 299},
    {\"lap_time_sec\": 37, \"speed_kmh\": 250},
    {\"lap_time_sec\": 38, \"speed_kmh\": 130},
    {\"lap_time_sec\": 39, \"speed_kmh\": 82},
    {\"lap_time_sec\": 40, \"speed_kmh\": 81},
    {\"lap_time_sec\": 41, \"speed_kmh\": 92},
    {\"lap_time_sec\": 42, \"speed_kmh\": 114},
    {\"lap_time_sec\": 43, \"speed_kmh\": 136},
    {\"lap_time_sec\": 44, \"speed_kmh\": 154},
    {\"lap_time_sec\": 45, \"speed_kmh\": 168},
    {\"lap_time_sec\": 46, \"speed_kmh\": 171},
    {\"lap_time_sec\": 47, \"speed_kmh\": 163},
    {\"lap_time_sec\": 48, \"speed_kmh\": 152},
    {\"lap_time_sec\": 49, \"speed_kmh\": 155},
    {\"lap_time_sec\": 50, \"speed_kmh\": 168},
    {\"lap_time_sec\": 51, \"speed_kmh\": 182},
    {\"lap_time_sec\": 52, \"speed_kmh\": 184},
    {\"lap_time_sec\": 53, \"speed_kmh\": 147},
    {\"lap_time_sec\": 54, \"speed_kmh\": 140},
    {\"lap_time_sec\": 55, \"speed_kmh\": 151},
    {\"lap_time_sec\": 56, \"speed_kmh\": 168},
    {\"lap_time_sec\": 57, \"speed_kmh\": 182},
    {\"lap_time_sec\": 58, \"speed_kmh\": 196},
    {\"lap_time_sec\": 59, \"speed_kmh\": 209}
  ]
}
```
