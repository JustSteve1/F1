
// F1 Driver data types
export interface Driver {
  number: number;
  code: string;
  firstName: string;
  lastName: string;
  team: Team;
  position: number;
}

export interface Team {
  id: string;
  name: string;
  color: string;
}

export interface LapTime {
  driverId: number;
  lap: number;
  position: number;
  time: string; // in format "1:30.123"
  gap: string; // gap to leader
  interval: string; // interval to car ahead
  sectors: SectorTimes;
  isPersonalBest: boolean;
  isPurpleSector: boolean; // fastest of all
  pitStops: number;
}

export interface SectorTimes {
  sector1: string;
  sector2: string;
  sector3: string;
}

export interface SessionData {
  name: string;
  type: 'FP1' | 'FP2' | 'FP3' | 'Q' | 'R' | 'Sprint';
  date: string;
  status: 'Upcoming' | 'Live' | 'Finished';
  lapTimes: LapTime[];
  currentLap: number;
  drivers: Driver[];
}

// Mock data for development
export const TEAMS: Record<string, Team> = {
  MERCEDES: { id: 'mercedes', name: 'Mercedes', color: '#00D2BE' },
  RED_BULL: { id: 'redbull', name: 'Red Bull Racing', color: '#0600EF' },
  FERRARI: { id: 'ferrari', name: 'Ferrari', color: '#DC0000' },
  MCLAREN: { id: 'mclaren', name: 'McLaren', color: '#FF8700' },
  ASTON_MARTIN: { id: 'astonmartin', name: 'Aston Martin', color: '#006F62' },
  ALPINE: { id: 'alpine', name: 'Alpine', color: '#0090FF' },
  WILLIAMS: { id: 'williams', name: 'Williams', color: '#005AFF' },
  ALPHATAURI: { id: 'alphatauri', name: 'AlphaTauri', color: '#2B4562' },
  ALFA_ROMEO: { id: 'alfaromeo', name: 'Alfa Romeo', color: '#900000' },
  HAAS: { id: 'haas', name: 'Haas F1 Team', color: '#FFFFFF' },
};
