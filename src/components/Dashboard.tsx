
import React, { useState, useEffect } from 'react';
import F1Logo from './F1Logo';
import TimingTable from './TimingTable';
import LapSelector from './LapSelector';
import CircuitDisplay from './CircuitDisplay';
import { SessionData } from '../types/f1-types';

interface DashboardProps {
  sessionData: SessionData;
}

const Dashboard: React.FC<DashboardProps> = ({ sessionData }) => {
  const [selectedLap, setSelectedLap] = useState<number>(sessionData.currentLap);
  const [isLive, setIsLive] = useState<boolean>(sessionData.status === 'Live');

  // Handle lap change
  const handleLapChange = (lap: number) => {
    setSelectedLap(lap);
  };

  return (
    <div className="min-h-screen bg-background text-foreground p-6">
      <header className="mb-6 flex justify-between items-center">
        <F1Logo />
        <div className="flex items-center space-x-4">
          <div className="bg-f1-red px-4 py-1 rounded font-semibold text-white">
            {sessionData.type}
          </div>
          <h2 className="text-xl font-bold">{sessionData.name}</h2>
          {isLive && (
            <div className="flex items-center">
              <div className="w-3 h-3 rounded-full bg-red-500 animate-pulse mr-2"></div>
              <span className="text-red-500 font-medium">LIVE</span>
            </div>
          )}
        </div>
      </header>

      <main className="space-y-6">
        <LapSelector
          currentLap={sessionData.currentLap}
          totalLaps={sessionData.currentLap}
          selectedLap={selectedLap}
          onLapChange={handleLapChange}
        />

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <TimingTable
              drivers={sessionData.drivers}
              lapTimes={sessionData.lapTimes}
              selectedLap={selectedLap}
            />
          </div>
          <div>
            <CircuitDisplay 
              trackName={sessionData.name}
              selectedLap={selectedLap}
            />
          </div>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
