
import React from 'react';
import { Driver, LapTime } from '../types/f1-types';
import DriverRow from './DriverRow';

interface TimingTableProps {
  drivers: Driver[];
  lapTimes: LapTime[];
  selectedLap: number;
}

const TimingTable: React.FC<TimingTableProps> = ({ drivers, lapTimes, selectedLap }) => {
  // Filter lap times for the selected lap
  const currentLapTimes = lapTimes.filter(lt => lt.lap === selectedLap);

  return (
    <div className="bg-card rounded-md overflow-hidden shadow-lg">
      <table className="w-full border-collapse">
        <thead className="bg-f1-black text-white">
          <tr>
            <th className="py-3 px-4 text-left">Pos</th>
            <th className="py-3 px-4 text-left">Driver</th>
            <th className="py-3 px-4 text-left">Time</th>
            <th className="py-3 px-4 text-center">S1</th>
            <th className="py-3 px-4 text-center">S2</th>
            <th className="py-3 px-4 text-center">S3</th>
            <th className="py-3 px-4 text-right">Gap</th>
            <th className="py-3 px-4 text-right">Interval</th>
          </tr>
        </thead>
        <tbody>
          {drivers
            .sort((a, b) => a.position - b.position)
            .map((driver) => {
              const lapTime = currentLapTimes.find(lt => lt.driverId === driver.number);
              return (
                <DriverRow
                  key={driver.number}
                  driver={driver}
                  lapTime={lapTime}
                  selectedLap={selectedLap}
                />
              );
            })}
        </tbody>
      </table>
    </div>
  );
};

export default TimingTable;
