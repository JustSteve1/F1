
# F1 Live Timing Application

A real-time Formula 1 timing application that displays live lap data from F1 races, capturing and storing timing information in Google Cloud.

## Features

- React frontend with F1-inspired design
- Python backend with FastAPI
- Real-time data updates from the F1 timing API
- Google Cloud Firestore database for data storage
- Lap-by-lap timing analysis
- Driver performance comparisons

## Project Structure

```
├── backend/               # Python FastAPI backend
│   ├── main.py            # Main API server
│   └── requirements.txt   # Python dependencies
│
├── public/                # Static assets
│
└── src/                   # React frontend
    ├── components/        # React components
    ├── data/              # Mock data for development
    ├── pages/             # Page components
    ├── services/          # API services
    ├── types/             # TypeScript types
    └── api/               # API documentation
```

## Getting Started

### Frontend

1. Install dependencies:
   ```
   npm install
   ```

2. Start the development server:
   ```
   npm run dev
   ```

3. The frontend will be available at http://localhost:8080

### Backend

1. Navigate to the backend directory:
   ```
   cd backend
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up Google Cloud credentials:
   ```
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service-account-key.json"
   ```

4. Start the backend server:
   ```
   uvicorn main:app --reload
   ```

5. The API will be available at http://localhost:8000

## Frontend-Backend Integration

In a production environment, update the API base URL in `src/services/apiService.ts` to point to your deployed backend.

## Google Cloud Setup

1. Create a new Google Cloud project
2. Enable Firestore and set up a database
3. Create a service account with appropriate permissions
4. Download the service account key JSON file
5. Set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to point to this file

## F1 API Integration

The application connects to the official F1 timing API. Please note that access to this API may be restricted, and you should ensure you have the necessary permissions to use it.

## Deployment

### Frontend
- Build the React app: `npm run build`
- Deploy to your preferred hosting service (Netlify, Vercel, GitHub Pages, etc.)

### Backend
- Deploy to Google Cloud Run, App Engine, or any other cloud service that supports Python
- Ensure environment variables are properly set in your deployment environment
