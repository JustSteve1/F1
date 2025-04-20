
import React from 'react';

interface CircuitDisplayProps {
  trackName: string;
  selectedLap: number;
  driverPositions?: Record<string, number>; // Map of driver codes to position on track (0-100)
}

// Simplified track data with SVG paths
const TRACK_DATA: Record<string, { path: string, length: number }> = {
  'Monaco Grand Prix': {
    path: "M60,180 C60,120 120,60 180,60 C240,60 300,120 300,180 C300,240 240,300 180,300 C120,300 60,240 60,180 Z",
    length: 3337
  },
  'Silverstone': {
    path: "M50,180 L180,50 L320,50 C350,50 360,90 330,110 L250,170 L300,250 L250,300 L140,300 L80,250 Z",
    length: 5891
  },
  'Monza': {
    path: "M70,150 L120,80 L280,80 L330,150 L330,250 L280,320 L120,320 L70,250 Z",
    length: 5793
  },
  'Spa': {
    path: "M50,250 L120,100 L220,100 L260,160 L300,120 L350,170 L320,230 L350,270 L280,320 L170,320 L120,260 Z",
    length: 7004
  }
};

// Default track if the specified one isn't found
const DEFAULT_TRACK = 'Monaco Grand Prix';

const CircuitDisplay: React.FC<CircuitDisplayProps> = ({ 
  trackName, 
  selectedLap,
  driverPositions = {}
}) => {
  const trackData = TRACK_DATA[trackName] || TRACK_DATA[DEFAULT_TRACK];
  
  return (
    <div className="bg-card rounded-md overflow-hidden shadow-lg p-4">
      <h3 className="text-lg font-semibold mb-4">{trackName} - Circuit Map</h3>
      
      <div className="relative w-full" style={{ height: '300px' }}>
        <svg 
          viewBox="0 0 400 400" 
          className="w-full h-full"
        >
          {/* Track outline */}
          <path 
            d={trackData.path} 
            fill="none" 
            stroke="#666" 
            strokeWidth="30" 
            strokeLinecap="round" 
            strokeLinejoin="round"
          />
          
          {/* Track surface */}
          <path 
            d={trackData.path} 
            fill="none" 
            stroke="#444" 
            strokeWidth="28" 
            strokeLinecap="round" 
            strokeLinejoin="round"
          />
          
          {/* Starting line */}
          <circle cx="70" cy="180" r="5" fill="#fff" />
          
          {/* Sector markers */}
          <circle cx="260" cy="80" r="5" fill="#f1c40f" /> {/* Sector 1 */}
          <circle cx="320" cy="250" r="5" fill="#f1c40f" /> {/* Sector 2 */}
          
          {/* Driver markers would be placed dynamically based on position data */}
          {/* This is just a placeholder for visualization */}
          <circle cx="120" cy="120" r="6" fill="#0600EF" stroke="#fff" strokeWidth="2" /> {/* Example: Red Bull */}
          <circle cx="150" cy="100" r="6" fill="#DC0000" stroke="#fff" strokeWidth="2" /> {/* Example: Ferrari */}
        </svg>
        
        <div className="absolute bottom-2 left-2 text-xs text-gray-400">
          Track Length: {trackData.length}m | Lap: {selectedLap}
        </div>
      </div>
      
      <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
        <div className="flex items-center">
          <div className="w-3 h-3 rounded-full bg-purple-500 mr-2"></div>
          <span>Fastest Overall Sector</span>
        </div>
        <div className="flex items-center">
          <div className="w-3 h-3 rounded-full bg-green-500 mr-2"></div>
          <span>Personal Best Sector</span>
        </div>
      </div>
    </div>
  );
};

export default CircuitDisplay;
