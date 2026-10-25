"use client";

import Link from "next/link";
import raw from "./hamilton-fp3-speed.json";

type Sample = [number, number, number, number];

const points = raw.points as Sample[];

const STOPS: Array<[number, [number, number, number]]> = [
  [80, [37, 99, 235]],
  [150, [14, 165, 183]],
  [210, [132, 204, 22]],
  [270, [250, 204, 21]],
  [340, [239, 68, 68]],
];

function mix(speed: number): string {
  const first = STOPS[0];
  const last = STOPS[STOPS.length - 1];
  if (speed <= first[0]) return rgb(first[1]);
  if (speed >= last[0]) return rgb(last[1]);
  for (let index = 1; index < STOPS.length; index += 1) {
    const [hi, hc] = STOPS[index];
    const [lo, lc] = STOPS[index - 1];
    if (speed > hi) continue;
    const blend = (speed - lo) / (hi - lo);
    return rgb([
      Math.round(lc[0] + (hc[0] - lc[0]) * blend),
      Math.round(lc[1] + (hc[1] - lc[1]) * blend),
      Math.round(lc[2] + (hc[2] - lc[2]) * blend),
    ]);
  }
  return rgb(last[1]);
}

function rgb(channels: [number, number, number]): string {
  return `rgb(${channels[0]} ${channels[1]} ${channels[2]})`;
}

const WIDTH = 1000;
const HEIGHT = 640;
const PAD = 28;

export function SpeedMap() {
  const speeds = points.map((point) => point[3]);
  const minSpeed = Math.min(...speeds);
  const maxSpeed = Math.max(...speeds);
  const minX = Math.min(...points.map((point) => point[1]));
  const maxX = Math.max(...points.map((point) => point[1]));
  const minY = Math.min(...points.map((point) => point[2]));
  const maxY = Math.max(...points.map((point) => point[2]));
  const spanX = Math.max(maxX - minX, 1);
  const spanY = Math.max(maxY - minY, 1);
  const scale = Math.min((WIDTH - PAD * 2) / spanX, (HEIGHT - PAD * 2) / spanY);
  const offsetX = (WIDTH - spanX * scale) / 2;
  const offsetY = (HEIGHT - spanY * scale) / 2;
  const projectX = (x: number) => offsetX + (x - minX) * scale;
  const projectY = (y: number) => offsetY + (maxY - y) * scale;
  const lastTime = points[points.length - 1][0];

  return (
    <div className="text-white">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="mb-2 font-mono text-[11px] uppercase tracking-widest text-white/45">
            telemetry_live · speed
          </p>
          <h1 className="text-3xl font-black uppercase tracking-tighter md:text-4xl">
            {raw.driverName}
          </h1>
          <p className="mt-1 font-mono text-xs uppercase tracking-widest text-white/45">
            {raw.event} · {raw.session} · lap {raw.lap} · {raw.lapTime} · {raw.compound}
          </p>
        </div>
        <Link
          href="/live/laps"
          className="font-mono text-[11px] uppercase tracking-widest text-white/50 hover:text-white"
        >
          Completed laps
        </Link>
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_180px]">
        <div className="rounded-sm border border-white/10 bg-white/[0.02] p-3">
          <svg
            viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
            className="h-auto w-full"
            role="img"
            aria-label="Circuit of the Americas colored by Lewis Hamilton speed on lap 10"
          >
            <title>
              {raw.circuit} speed map, {raw.driver} lap {raw.lap}
            </title>
            {points.slice(1).map((point, index) => {
              const previous = points[index];
              const speed = (previous[3] + point[3]) / 2;
              return (
                <line
                  key={`${point[0]}`}
                  x1={projectX(previous[1])}
                  y1={projectY(previous[2])}
                  x2={projectX(point[1])}
                  y2={projectY(point[2])}
                  stroke={mix(speed)}
                  strokeWidth={14}
                  strokeLinecap="round"
                />
              );
            })}
            <circle cx={projectX(points[0][1])} cy={projectY(points[0][2])} r={5} fill="white" />
          </svg>
          <p className="px-1 pt-2 font-mono text-[10px] uppercase tracking-widest text-white/40">
            White dot is the start/finish line · metres from the official position feed · colour is speed
          </p>
        </div>

        <div className="flex flex-col justify-between gap-4 rounded-sm border border-white/10 p-4">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-widest text-white/40">Speed</p>
            <div className="mt-3 flex items-stretch gap-3">
              <div
                className="w-3 rounded-sm"
                style={{
                  background: `linear-gradient(to top, ${STOPS.map((stop) => rgb(stop[1])).join(", ")})`,
                }}
              />
              <div className="flex flex-col justify-between font-mono text-[10px] text-white/70">
                <span>{STOPS[STOPS.length - 1][0]} km/h</span>
                <span>{STOPS[2][0]}</span>
                <span>{STOPS[0][0]} km/h</span>
              </div>
            </div>
          </div>
          <dl className="space-y-2 font-mono text-[11px] uppercase tracking-widest text-white/70">
            <div className="flex justify-between gap-3">
              <dt className="text-white/40">Fastest</dt>
              <dd>{maxSpeed} km/h</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-white/40">Slowest</dt>
              <dd>{minSpeed} km/h</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-white/40">Lap</dt>
              <dd>{raw.lapTime}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-white/40">Samples</dt>
              <dd>{points.length}</dd>
            </div>
          </dl>
        </div>
      </div>

      <div className="mt-4 rounded-sm border border-white/10 bg-white/[0.02] p-3">
        <p className="mb-2 px-1 font-mono text-[10px] uppercase tracking-widest text-white/40">
          Speed through the lap · seconds from the start line
        </p>
        <svg viewBox="0 0 1000 160" className="h-auto w-full" role="img" aria-label="Speed against lap time">
          <title>Speed in kilometres per hour against lap time in seconds</title>
          {points.slice(1).map((point, index) => {
            const previous = points[index];
            const chartX = (time: number) => 36 + (time / lastTime) * 940;
            const chartY = (speed: number) => 16 + (1 - (speed - 60) / (340 - 60)) * 112;
            return (
              <line
                key={`t-${point[0]}`}
                x1={chartX(previous[0])}
                y1={chartY(previous[3])}
                x2={chartX(point[0])}
                y2={chartY(point[3])}
                stroke={mix((previous[3] + point[3]) / 2)}
                strokeWidth={3}
                strokeLinecap="round"
              />
            );
          })}
          <text x="36" y="152" fill="rgba(255,255,255,0.45)" fontSize="11" fontFamily="ui-monospace, monospace">
            0 s
          </text>
          <text x="940" y="152" fill="rgba(255,255,255,0.45)" fontSize="11" fontFamily="ui-monospace, monospace" textAnchor="end">
            {lastTime.toFixed(0)} s
          </text>
          <text x="8" y="24" fill="rgba(255,255,255,0.45)" fontSize="11" fontFamily="ui-monospace, monospace">
            340
          </text>
          <text x="8" y="128" fill="rgba(255,255,255,0.45)" fontSize="11" fontFamily="ui-monospace, monospace">
            60
          </text>
        </svg>
      </div>
    </div>
  );
}
