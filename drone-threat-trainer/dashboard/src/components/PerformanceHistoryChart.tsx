"use client";

import React, { useEffect, useRef } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "./ui/card";

export interface SessionHistoryItem {
  session_number: number;
  session_code: string;
  date: string;
  difficulty: string;
  detection_score: number;
  classification_score: number;
  decision_score: number;
  overall_score: number;
}

interface PerformanceHistoryChartProps {
  sessions: SessionHistoryItem[];
  traineeCode: string;
}

export function PerformanceHistoryChart({ sessions, traineeCode }: PerformanceHistoryChartProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;
    const padding = { top: 30, right: 30, bottom: 40, left: 50 };

    ctx.clearRect(0, 0, width, height);

    // Grid background
    ctx.strokeStyle = "rgba(51, 65, 85, 0.4)";
    ctx.lineWidth = 1;

    // Y-Axis lines (0%, 25%, 50%, 75%, 100%)
    const ySteps = [0, 25, 50, 75, 100];
    ySteps.forEach((val) => {
      const y = height - padding.bottom - (val / 100) * (height - padding.top - padding.bottom);
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(width - padding.right, y);
      ctx.stroke();

      ctx.fillStyle = "#64748b";
      ctx.font = "10px monospace";
      ctx.fillText(`${val}%`, padding.left - 30, y + 3);
    });

    if (sessions.length < 2) {
      ctx.fillStyle = "#94a3b8";
      ctx.font = "12px monospace";
      ctx.fillText("Complete at least 2 sessions to render historical trends.", padding.left + 20, height / 2);
      return;
    }

    const plotWidth = width - padding.left - padding.right;
    const plotHeight = height - padding.top - padding.bottom;
    const xStep = plotWidth / (sessions.length - 1);

    // Draw Line helper
    const drawTrendLine = (
      key: "detection_score" | "classification_score" | "decision_score" | "overall_score",
      color: string,
      lineWidth: number = 2
    ) => {
      ctx.strokeStyle = color;
      ctx.lineWidth = lineWidth;
      ctx.beginPath();

      sessions.forEach((s, i) => {
        const x = padding.left + i * xStep;
        const val = s[key];
        const y = height - padding.bottom - (val / 100) * plotHeight;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();

      // Draw point markers
      sessions.forEach((s, i) => {
        const x = padding.left + i * xStep;
        const val = s[key];
        const y = height - padding.bottom - (val / 100) * plotHeight;
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(x, y, 4, 0, Math.PI * 2);
        ctx.fill();
      });
    };

    // Render 4 metric lines
    drawTrendLine("detection_score", "#06b6d4", 2);       // Cyan
    drawTrendLine("classification_score", "#10b981", 2);  // Green
    drawTrendLine("decision_score", "#f59e0b", 2);        // Amber
    drawTrendLine("overall_score", "#ffffff", 3);         // White bold

    // X-Axis labels
    sessions.forEach((s, i) => {
      const x = padding.left + i * xStep;
      ctx.fillStyle = "#94a3b8";
      ctx.font = "10px monospace";
      ctx.fillText(`S${s.session_number}`, x - 8, height - 12);
    });
  }, [sessions]);

  return (
    <Card className="border-slate-800 bg-slate-900/90 shadow-xl">
      <CardHeader className="flex flex-row justify-between items-center pb-2">
        <div>
          <CardTitle className="text-sm font-mono text-cyan-400">
            PERFORMANCE PROGRESSION HISTORY
          </CardTitle>
          <p className="text-xs text-slate-400 font-mono mt-0.5">TRAINEE: {traineeCode}</p>
        </div>
        <div className="flex gap-4 text-xs font-mono">
          <span className="flex items-center gap-1.5 text-white">
            <span className="w-2.5 h-0.5 bg-white inline-block" /> Overall
          </span>
          <span className="flex items-center gap-1.5 text-cyan-400">
            <span className="w-2.5 h-0.5 bg-cyan-400 inline-block" /> Detection
          </span>
          <span className="flex items-center gap-1.5 text-emerald-400">
            <span className="w-2.5 h-0.5 bg-emerald-400 inline-block" /> Classification
          </span>
          <span className="flex items-center gap-1.5 text-amber-400">
            <span className="w-2.5 h-0.5 bg-amber-400 inline-block" /> Decision
          </span>
        </div>
      </CardHeader>

      <CardContent>
        <canvas ref={canvasRef} width={640} height={220} className="w-full h-auto rounded bg-slate-950" />

        {/* Tabular History (Section 15) */}
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-xs font-mono text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400">
                <th className="py-2 px-3">SESSION</th>
                <th className="py-2 px-3">DIFFICULTY</th>
                <th className="py-2 px-3">DETECTION</th>
                <th className="py-2 px-3">CLASSIFICATION</th>
                <th className="py-2 px-3">DECISION</th>
                <th className="py-2 px-3">OVERALL</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((s) => (
                <tr key={s.session_code} className="border-b border-slate-800/40 hover:bg-slate-800/20">
                  <td className="py-2 px-3 text-cyan-400 font-bold">#{s.session_number} ({s.session_code})</td>
                  <td className="py-2 px-3 uppercase text-slate-300">{s.difficulty}</td>
                  <td className="py-2 px-3 text-cyan-300">{s.detection_score}%</td>
                  <td className="py-2 px-3 text-emerald-300">{s.classification_score}%</td>
                  <td className="py-2 px-3 text-amber-300">{s.decision_score}%</td>
                  <td className="py-2 px-3 text-white font-bold">{s.overall_score}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
