
import { Driver, LapTime, SessionData, TEAMS } from '../types/f1-types';

// Mock Drivers
export const mockDrivers: Driver[] = [
  { number: 1, code: 'VER', firstName: 'Max', lastName: 'Verstappen', team: TEAMS.RED_BULL, position: 1 },
  { number: 11, code: 'PER', firstName: 'Sergio', lastName: 'Perez', team: TEAMS.RED_BULL, position: 2 },
  { number: 16, code: 'LEC', firstName: 'Charles', lastName: 'Leclerc', team: TEAMS.FERRARI, position: 3 },
  { number: 55, code: 'SAI', firstName: 'Carlos', lastName: 'Sainz', team: TEAMS.FERRARI, position: 4 },
  { number: 44, code: 'HAM', firstName: 'Lewis', lastName: 'Hamilton', team: TEAMS.MERCEDES, position: 5 },
  { number: 63, code: 'RUS', firstName: 'George', lastName: 'Russell', team: TEAMS.MERCEDES, position: 6 },
  { number: 4, code: 'NOR', firstName: 'Lando', lastName: 'Norris', team: TEAMS.MCLAREN, position: 7 },
  { number: 81, code: 'PIA', firstName: 'Oscar', lastName: 'Piastri', team: TEAMS.MCLAREN, position: 8 },
  { number: 14, code: 'ALO', firstName: 'Fernando', lastName: 'Alonso', team: TEAMS.ASTON_MARTIN, position: 9 },
  { number: 18, code: 'STR', firstName: 'Lance', lastName: 'Stroll', team: TEAMS.ASTON_MARTIN, position: 10 },
];

// Generate mock lap times
export const generateMockLapTimes = (drivers: Driver[], laps: number): LapTime[] => {
  const lapTimes: LapTime[] = [];
  
  for (let lap = 1; lap <= laps; lap++) {
    drivers.forEach((driver) => {
      // Generate random lap time between 1:28.000 and 1:35.000
      const baseTime = 88000 + Math.random() * 7000; // milliseconds
      const s1Time = (baseTime * 0.33) + (Math.random() * 1000 - 500);
      const s2Time = (baseTime * 0.33) + (Math.random() * 1000 - 500);
      const s3Time = baseTime - s1Time - s2Time;
      
      const formatTime = (ms: number) => {
        const totalSeconds = ms / 1000;
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = totalSeconds % 60;
        return `${minutes}:${seconds.toFixed(3)}`;
      };
      
      const formatSectorTime = (ms: number) => {
        return (ms / 1000).toFixed(3);
      };
      
      lapTimes.push({
        driverId: driver.number,
        lap,
        position: driver.position,
        time: formatTime(baseTime),
        gap: driver.position === 1 ? "" : `+${(driver.position - 1) * 0.5}.${Math.floor(Math.random() * 1000)}`,
        interval: driver.position === 1 ? "" : `+${0}.${Math.floor(Math.random() * 1000)}`,
        sectors: {
          sector1: formatSectorTime(s1Time),
          sector2: formatSectorTime(s2Time),
          sector3: formatSectorTime(s3Time),
        },
        isPersonalBest: Math.random() > 0.8,
        isPurpleSector: Math.random() > 0.95,
        pitStops: Math.random() > 0.9 ? 1 : 0,
      });
    });
  }
  
  return lapTimes;
};

// Mock session data
export const mockSession: SessionData = {
  name: 'Monaco Grand Prix',
  type: 'R',
  date: '2023-05-28',
  status: 'Live',
  lapTimes: generateMockLapTimes(mockDrivers, 10),
  currentLap: 10,
  drivers: mockDrivers,
};
