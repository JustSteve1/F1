export type Fastf1CacheSession = {
  folder: string;
  code: string | null;
};

export type Fastf1CacheEvent = {
  folder: string;
  uri: string;
  sessions: Fastf1CacheSession[];
};

export type Fastf1CacheStatus = {
  year: number;
  race: string | null;
  bucket: string;
  prefix: string;
  uri: string;
  readable: boolean;
  present: boolean;
  events: Fastf1CacheEvent[];
  sessionCodes: string[];
  missingSessionCodes: string[];
  error: string | null;
  hint: string;
};
