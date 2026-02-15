import React from 'react';

export default function FactoryPage() {
    return (
        <div className="flex flex-col h-screen w-full bg-black">
            <iframe
                src="https://gemini-video-analyst-576746898444.us-west1.run.app"
                className="flex-grow w-full border-0"
                title="Gemini Video Analyst"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; camera; microphone"
                allowFullScreen
            />
        </div>
    );
}
