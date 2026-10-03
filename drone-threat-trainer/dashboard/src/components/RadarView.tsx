"use client";

import React, { useEffect, useRef } from "react";

export interface TrackedTarget {
  object_id: number;
  class: string;
  confidence: number;
  bbox: number[];
  velocity: number[];
  x?: number;
  y?: number;
  range?: number;
  bearing?: number;
}

interface RadarViewProps {
  targets: TrackedTarget[];
  selectedId: number | null;
  onSelectTarget: (target: TrackedTarget) => void;
  statusText?: string;
}

export function RadarView({ targets, selectedId, onSelectTarget, statusText }: RadarViewProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const sweepAngleRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;

    const render = () => {
      const width = canvas.width;
      const height = canvas.height;
      const cx = width / 2;
      const cy = height / 2;
      const radius = Math.min(cx, cy) - 20;

      ctx.clearRect(0, 0, width, height);

      // 1. Radar background circle
      ctx.fillStyle = "#090d14";
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, Math.PI * 2);
      ctx.fill();

      // 2. Concentric range rings (50m, 100m, 150m, 200m)
      ctx.strokeStyle = "rgba(6, 182, 212, 0.25)";
      ctx.lineWidth = 1;
      const rings = [0.25, 0.5, 0.75, 1.0];
      rings.forEach((ratio, idx) => {
        ctx.beginPath();
        ctx.arc(cx, cy, radius * ratio, 0, Math.PI * 2);
        ctx.stroke();

        ctx.fillStyle = "rgba(6, 182, 212, 0.5)";
        ctx.font = "10px monospace";
        ctx.fillText(`${(idx + 1) * 50}m`, cx + 6, cy - radius * ratio + 12);
      });

      // 3. Crosshairs
      ctx.beginPath();
      ctx.moveTo(cx - radius, cy);
      ctx.lineTo(cx + radius, cy);
      ctx.moveTo(cx, cy - radius);
      ctx.lineTo(cx, cy + radius);
      ctx.stroke();

      // 4. Rotating sweep beam
      sweepAngleRef.current = (sweepAngleRef.current + 0.035) % (Math.PI * 2);
      const angle = sweepAngleRef.current;

      const gradient = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius);
      gradient.addColorStop(0, "rgba(6, 182, 212, 0.4)");
      gradient.addColorStop(1, "rgba(6, 182, 212, 0.0)");

      ctx.save();
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.arc(cx, cy, radius, angle - 0.45, angle);
      ctx.closePath();
      ctx.fillStyle = "rgba(6, 182, 212, 0.15)";
      ctx.fill();

      // Sweep front line
      ctx.strokeStyle = "rgba(6, 182, 212, 0.8)";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(cx + radius * Math.cos(angle), cy + radius * Math.sin(angle));
      ctx.stroke();
      ctx.restore();

      // 5. Render Tracked Targets
      targets.forEach((tgt, idx) => {
        // Map bbox center to radar position if not explicitly set
        let tx = tgt.x;
        let ty = tgt.y;
        if (tx === undefined || ty === undefined) {
          const normX = ((tgt.bbox[0] + tgt.bbox[2]) / 2 - 320) / 320;
          const normY = ((tgt.bbox[1] + tgt.bbox[3]) / 2 - 240) / 240;
          tx = cx + normX * (radius * 0.75);
          ty = cy + normY * (radius * 0.75);
        }

        const isSelected = tgt.object_id === selectedId;
        const isDrone = tgt.class.toLowerCase().includes("drone");

        // Blip color
        const blipColor = isDrone ? "#f59e0b" : "#10b981";

        // Selection ring
        if (isSelected) {
          ctx.strokeStyle = "#06b6d4";
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.arc(tx, ty, 14, 0, Math.PI * 2);
          ctx.stroke();
        }

        // Target dot
        ctx.fillStyle = blipColor;
        ctx.beginPath();
        ctx.arc(tx, ty, 5, 0, Math.PI * 2);
        ctx.fill();

        // Velocity vector arrow
        const vx = tgt.velocity ? tgt.velocity[0] * 3 : 0;
        const vy = tgt.velocity ? tgt.velocity[1] * 3 : 0;
        if (Math.abs(vx) > 0.5 || Math.abs(vy) > 0.5) {
          ctx.strokeStyle = blipColor;
          ctx.lineWidth = 1.5;
          ctx.beginPath();
          ctx.moveTo(tx, ty);
          ctx.lineTo(tx + vx, ty + vy);
          ctx.stroke();
        }

        // Label
        ctx.fillStyle = isSelected ? "#06b6d4" : "#e2e8f0";
        ctx.font = "bold 10px monospace";
        ctx.fillText(`ID ${tgt.object_id.toString().padStart(2, "0")}`, tx + 8, ty - 6);
        ctx.fillStyle = "#94a3b8";
        ctx.font = "9px monospace";
        ctx.fillText(`${tgt.class.toUpperCase()} ${Math.round(tgt.confidence * 100)}%`, tx + 8, ty + 6);
      });

      animId = requestAnimationFrame(render);
    };

    render();

    return () => cancelAnimationFrame(animId);
  }, [targets, selectedId]);

  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    const cx = canvas.width / 2;
    const cy = canvas.height / 2;
    const radius = Math.min(cx, cy) - 20;

    let closest: TrackedTarget | null = null;
    let minDist = 30; // click radius threshold

    targets.forEach((tgt) => {
      let tx = tgt.x;
      let ty = tgt.y;
      if (tx === undefined || ty === undefined) {
        const normX = ((tgt.bbox[0] + tgt.bbox[2]) / 2 - 320) / 320;
        const normY = ((tgt.bbox[1] + tgt.bbox[3]) / 2 - 240) / 240;
        tx = cx + normX * (radius * 0.75);
        ty = cy + normY * (radius * 0.75);
      }
      const dist = Math.hypot(clickX - tx, clickY - ty);
      if (dist < minDist) {
        minDist = dist;
        closest = tgt;
      }
    });

    if (closest) {
      onSelectTarget(closest);
    }
  };

  return (
    <div className="relative flex flex-col items-center justify-center p-4 bg-slate-950 rounded-lg border border-slate-800">
      <div className="w-full flex justify-between items-center mb-2 px-2 text-xs font-mono text-cyan-400">
        <span>RADAR 360° SWEEP :: DEFENSE SECTOR</span>
        <span>{statusText || "RADAR ONLINE"}</span>
      </div>
      <canvas
        ref={canvasRef}
        width={420}
        height={420}
        onClick={handleCanvasClick}
        className="cursor-crosshair rounded-full shadow-inner border border-cyan-500/20"
      />
      <div className="mt-3 flex gap-6 text-xs font-mono text-slate-400">
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-amber-500 inline-block" /> Drone Threat
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block" /> Non-Threat / Bio
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full border border-cyan-400 inline-block" /> Target Locked
        </span>
      </div>
    </div>
  );
}
