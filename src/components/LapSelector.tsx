
import React from 'react';
import { Button } from "@/components/ui/button";

interface LapSelectorProps {
  currentLap: number;
  totalLaps: number;
  selectedLap: number;
  onLapChange: (lap: number) => void;
}

const LapSelector: React.FC<LapSelectorProps> = ({ 
  currentLap, 
  totalLaps, 
  selectedLap, 
  onLapChange 
}) => {
  // Generate an array of laps from 1 to totalLaps
  const laps = Array.from({ length: totalLaps }, (_, i) => i + 1);

  return (
    <div className="flex flex-col space-y-2">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">Lap: {selectedLap} of {totalLaps}</h3>
        <span className="text-f1-red px-2 py-1 bg-f1-black rounded text-sm font-semibold">
          {currentLap === totalLaps ? 'FINAL' : 'LIVE LAP ' + currentLap}
        </span>
      </div>
      
      <div className="grid grid-cols-10 gap-2">
        {laps.map(lap => (
          <Button
            key={lap}
            variant={selectedLap === lap ? "default" : "outline"}
            className={selectedLap === lap ? "bg-f1-red hover:bg-f1-red/90" : ""}
            onClick={() => onLapChange(lap)}
          >
            {lap}
          </Button>
        ))}
      </div>
    </div>
  );
};

export default LapSelector;
