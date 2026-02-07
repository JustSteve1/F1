
"use client";

import { useState, useRef, useEffect } from "react";
import { Mic, MicOff } from "lucide-react";

interface VoiceInputProps {
    onTranscription: (text: string) => void;
    className?: string;
}

export function VoiceInput({ onTranscription, className }: VoiceInputProps) {
    const [isRecording, setIsRecording] = useState(false);
    const [isProcessing, setIsProcessing] = useState(false);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const chunksRef = useRef<Blob[]>([]);

    // Sound FX
    const playRadioFx = () => {
        // Assuming file is in /public
        const audio = new Audio('/TeamRadiof1fx.wav');
        audio.volume = 0.5;
        audio.play().catch(e => console.warn("Audio play failed", e));
    };

    const startRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });

            mediaRecorderRef.current = mediaRecorder;
            chunksRef.current = [];

            mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) {
                    chunksRef.current.push(e.data);
                }
            };

            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(chunksRef.current, { type: 'audio/webm' });
                await processAudio(audioBlob);

                // Cleanup
                stream.getTracks().forEach(track => track.stop());
            };

            mediaRecorder.start();
            setIsRecording(true);
            playRadioFx(); // FX ON

        } catch (err) {
            console.error("Mic Access Error:", err);
            alert("Could not access microphone.");
        }
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current && isRecording) {
            mediaRecorderRef.current.stop();
            setIsRecording(false);
            setIsProcessing(true);
            playRadioFx(); // FX OFF
        }
    };

    const processAudio = async (blob: Blob) => {
        const formData = new FormData();
        formData.append("audio", blob);

        try {
            const res = await fetch("/api/pitwall/transcribe", {
                method: "POST",
                body: formData,
            });

            if (!res.ok) throw new Error("Transcription failed");

            const data = await res.json();
            if (data.text) {
                onTranscription(data.text);
            }
        } catch (error) {
            console.error("Transcribe Error:", error);
        } finally {
            setIsProcessing(false);
        }
    };

    return (
        <button
            onMouseDown={startRecording}
            onMouseUp={stopRecording}
            onMouseLeave={stopRecording}
            onTouchStart={startRecording}
            onTouchEnd={stopRecording}
            className={`
                p-3 rounded-full transition-all duration-200 flex items-center justify-center
                ${isRecording
                    ? "bg-red-600 text-white shadow-[0_0_15px_rgba(220,38,38,0.7)] scale-110"
                    : "bg-white/5 text-gray-400 hover:bg-white/10 hover:text-white"
                }
                ${isProcessing ? "opacity-50 cursor-wait" : ""}
                ${className}
            `}
            disabled={isProcessing}
            title="Hold to Speak"
        >
            {isRecording ? <Mic className="w-5 h-5 animate-pulse" /> : <MicOff className="w-5 h-5" />}
        </button>
    );
}
