
import React from 'react';
import { Driver, LapTime } from '../types/f1-types';

interface DriverRowProps {
  driver: Driver;
  lapTime?: LapTime;
  selectedLap: number;
}

const DriverRow: React.FC<DriverRowProps> = ({ driver, lapTime, selectedLap }) => {
  // If no lap time is available for this driver in the selected lap
  if (!lapTime) {
    return (
      <tr className="border-b border-gray-700 hover:bg-secondary/50 transition-colors">
        <td className="py-3 px-4 text-left">{driver.position}</td>
        <td className="py-3 px-4 text-left">
          <div className="flex items-center">
            <div className="w-1 h-6 mr-3" style={{ backgroundColor: driver.team.color }}></div>
            <span className="font-semibold">{driver.code}</span>
            <span className="text-muted-foreground ml-2">{driver.number}</span>
          </div>
        </td>
        <td className="py-3 px-4 text-left text-muted-foreground" colSpan={6}>No lap data available</td>
      </tr>
    );
  }

  // Determine styling for fastest sectors
  const getSectorStyle = (sector: 'sector1' | 'sector2' | 'sector3') => {
    if (lapTime.isPurpleSector) {
      return 'text-purple-500 font-bold';
    }
    if (lapTime.isPersonalBest) {
      return 'text-green-500 font-semibold';
    }
    return '';
  };

  return (
    <tr className="border-b border-gray-700 hover:bg-secondary/50 transition-colors">
      <td className="py-3 px-4 text-left">{driver.position}</td>
      <td className="py-3 px-4 text-left">
        <div className="flex items-center">
          <div className="w-1 h-6 mr-3" style={{ backgroundColor: driver.team.color }}></div>
          <span className="font-semibold">{driver.code}</span>
          <span className="text-muted-foreground ml-2">{driver.number}</span>
        </div>
      </td>
      <td className="py-3 px-4 text-left font-mono">{lapTime.time}</td>
      <td className={`py-3 px-4 text-center font-mono ${getSectorStyle('sector1')}`}>
        {lapTime.sectors.sector1}
      </td>
      <td className={`py-3 px-4 text-center font-mono ${getSectorStyle('sector2')}`}>
        {lapTime.sectors.sector2}
      </td>
      <td className={`py-3 px-4 text-center font-mono ${getSectorStyle('sector3')}`}>
        {lapTime.sectors.sector3}
      </td>
      <td className="py-3 px-4 text-right font-mono">{lapTime.gap}</td>
      <td className="py-3 px-4 text-right font-mono">{lapTime.interval}</td>
    </tr>
  );
};

export default DriverRow;
