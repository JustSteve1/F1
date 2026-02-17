"use client";

import { useEffect, useState, useRef } from "react";

interface CounterProps {
    end: number;
    duration?: number;
    label: string;
    subtext: string;
    suffix?: string;
}

const CounterItem = ({ end, duration = 2000, label, subtext, suffix = "" }: CounterProps) => {
    const [count, setCount] = useState(0);
    const countRef = useRef<HTMLDivElement>(null);
    const [isVisible, setIsVisible] = useState(false);

    useEffect(() => {
        const observer = new IntersectionObserver(
            ([entry]) => {
                if (entry.isIntersecting) {
                    setIsVisible(true);
                    observer.disconnect();
                }
            },
            { threshold: 0.1 }
        );

        if (countRef.current) {
            observer.observe(countRef.current);
        }

        return () => observer.disconnect();
    }, []);

    useEffect(() => {
        if (!isVisible) return;

        let startTime: number | null = null;
        const step = (timestamp: number) => {
            if (!startTime) startTime = timestamp;
            const progress = Math.min((timestamp - startTime) / duration, 1);

            // Easing function for smooth animation (easeOutExpo)
            const easeOut = (x: number): number => {
                return x === 1 ? 1 : 1 - Math.pow(2, -10 * x);
            };

            setCount(Math.floor(easeOut(progress) * end));

            if (progress < 1) {
                window.requestAnimationFrame(step);
            }
        };

        window.requestAnimationFrame(step);
    }, [isVisible, end, duration]);

    return (
        <div ref={countRef} className="flex flex-col items-center text-center p-6 border border-white/10 bg-white/5 rounded-sm">
            <div className="text-4xl md:text-5xl lg:text-6xl font-black text-white mb-2 tracking-tighter">
                {count.toLocaleString()}{suffix}
            </div>
            <div className="text-[#2596be] font-bold uppercase tracking-widest text-sm mb-4">
                {label}
            </div>
            <p className="text-white/60 font-serif text-sm leading-relaxed max-w-xs">
                {subtext}
            </p>
        </div>
    );
};

export default function StatsCounter() {
    return (
        <section className="bg-black py-24 px-4 border-t border-white/10">
            <div className="mx-auto max-w-7xl">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                    <CounterItem
                        end={1000000000}
                        duration={2500}
                        label="Lap datapoints indexed"
                        subtext="Every braking point, every apex, every decision — captured and structured."
                        suffix="+"
                    />
                    <CounterItem
                        end={10000}
                        duration={2000}
                        label="Onboard laps synchronised"
                        subtext="From broadcast to simulator — aligned into a single behavioural surface."
                        suffix="+"
                    />
                    <CounterItem
                        end={1}
                        duration={1500}
                        label="Agent learning continuously"
                        subtext="Transforming raw motion into insight, in real time."
                    />
                </div>
            </div>
        </section>
    );
}
