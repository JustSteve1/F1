
import { SessionData, LapTime, Driver } from '../types/f1-types';

// Base URL for the backend API
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

/**
 * Service to fetch data from the F1 API backend
 */
export const F1ApiService = {
  /**
   * Get the current or most recent session
   */
  getCurrentSession: async (): Promise<SessionData> => {
    try {
      const response = await fetch(`${API_BASE_URL}/sessions/current`);
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching current session:', error);
      throw error;
    }
  },

  /**
   * Get data for a specific session
   */
  getSession: async (sessionId: string): Promise<SessionData> => {
    try {
      const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}`);
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error(`Error fetching session ${sessionId}:`, error);
      throw error;
    }
  },

  /**
   * Get lap data for a specific session and lap number
   */
  getLapData: async (sessionId: string, lapNumber: number): Promise<LapTime[]> => {
    try {
      const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}/laps/${lapNumber}`);
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error(`Error fetching lap ${lapNumber} for session ${sessionId}:`, error);
      throw error;
    }
  },

  /**
   * Get all drivers for a specific session
   */
  getDrivers: async (sessionId: string): Promise<Driver[]> => {
    try {
      const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}/drivers`);
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error(`Error fetching drivers for session ${sessionId}:`, error);
      throw error;
    }
  },

  /**
   * Setup WebSocket connection for live updates
   * Returns a function to close the connection
   */
  connectToLiveUpdates: (sessionId: string, onUpdate: (data: any) => void): (() => void) => {
    // In a real implementation, this would establish a WebSocket connection
    // For now, we'll just simulate with an interval
    
    // This is where you'd implement WebSocket logic:
    // const ws = new WebSocket(`${WS_BASE_URL}/sessions/${sessionId}/live`);
    // ws.onmessage = (event) => onUpdate(JSON.parse(event.data));
    
    // Simulated updates with an interval
    const interval = setInterval(() => {
      // Simulate receiving a message
      onUpdate({ 
        type: 'lap_update',
        timestamp: new Date().toISOString(),
        data: { /* updated data */ }
      });
    }, 5000);
    
    // Return a function to close the connection
    return () => clearInterval(interval);
  }
};

export default F1ApiService;
