
import React from 'react';

const F1Logo: React.FC = () => {
  return (
    <div className="flex items-center">
      <div className="relative h-10 w-20">
        <span className="absolute font-bold text-3xl text-f1-red" style={{ left: '0px', top: '2px' }}>F1</span>
        <span className="absolute font-bold text-3xl text-white" style={{ left: '2px', top: '0px' }}>F1</span>
        <span className="ml-12 text-lg text-white font-semibold">LIVE TIMING</span>
      </div>
    </div>
  );
};

export default F1Logo;
