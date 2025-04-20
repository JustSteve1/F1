
import React, { useState, useEffect } from 'react';
import Dashboard from '../components/Dashboard';
import { mockSession } from '../data/mockData';
import { SessionData } from '../types/f1-types';

const Index = () => {
  const [sessionData, setSessionData] = useState<SessionData>(mockSession);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // This would be replaced with actual API fetching
  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        // In a real app, this would be a fetch call to your Python backend
        // For now, we're using mock data
        setSessionData(mockSession);
        setIsLoading(false);
      } catch (err) {
        setError('Failed to fetch session data');
        setIsLoading(false);
        console.error(err);
      }
    };

    fetchData();

    // Simulate live updates
    const interval = setInterval(() => {
      setSessionData(prevData => ({
        ...prevData,
        currentLap: prevData.currentLap < 20 ? prevData.currentLap + 1 : prevData.currentLap,
        status: prevData.currentLap >= 20 ? 'Finished' : 'Live'
      }));
    }, 10000); // Update every 10 seconds

    return () => clearInterval(interval);
  }, []);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-f1-red border-t-transparent rounded-full animate-spin mx-auto mb-6"></div>
          <h2 className="text-2xl font-bold text-white">Loading session data...</h2>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center text-red-500">
          <h2 className="text-2xl font-bold mb-4">{error}</h2>
          <p>Please check your connection and try again.</p>
        </div>
      </div>
    );
  }

  return <Dashboard sessionData={sessionData} />;
};

export default Index;
