"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { RadarView, TrackedTarget } from "@/components/RadarView";
import { TraineeControls } from "@/components/TraineeControls";
import { AARReportView, AARReportData } from "@/components/AARReportView";
import { PerformanceHistoryChart, SessionHistoryItem } from "@/components/PerformanceHistoryChart";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const API_BASE = "http://127.0.0.1:8000/api";
const WS_URL = "ws://127.0.0.1:8000/ws/telemetry";

export default function DashboardPage() {
  const [traineeCode, setTraineeCode] = useState("TRN-042");
  const [sessionCode, setSessionCode] = useState<string | null>(null);
  const [scenarioInfo, setScenarioInfo] = useState<{
    code: string;
    environment: string;
    lighting: string;
    difficulty: string;
    duration: number;
  }>({
    code: "SCN-00127",
    environment: "urban",
    lighting: "night",
    difficulty: "hard",
    duration: 180,
  });

  const [targets, setTargets] = useState<TrackedTarget[]>([]);
  const [selectedTarget, setSelectedTarget] = useState<TrackedTarget | null>(null);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [isSessionActive, setIsSessionActive] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [timelineEvents, setTimelineEvents] = useState<Array<{ time: string; text: string; type: string }>>([]);
  const [aarReport, setAarReport] = useState<AARReportData | null>(null);
  const [historySessions, setHistorySessions] = useState<SessionHistoryItem[]>([]);

  const wsRef = useRef<WebSocket | null>(null);

  // Setup WebSocket connection to FastAPI
  useEffect(() => {
    let ws: WebSocket;
    const connect = () => {
      ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        setWsConnected(true);
        addTimelineEvent("SYSTEM", "WebSocket Telemetry Link Established");
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleIncomingTelemetry(data);
        } catch (e) {
          console.error("Invalid telemetry payload", e);
        }
      };

      ws.onclose = () => {
        setWsConnected(false);
        setTimeout(connect, 3000); // Reconnect after 3s
      };

      ws.onerror = () => {
        setWsConnected(false);
      };
    };

    connect();

    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  // Timer loop when session is active
  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (isSessionActive) {
      timer = setInterval(() => {
        setElapsedTime((prev) => prev + 1);
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [isSessionActive]);

  const addTimelineEvent = (type: string, text: string) => {
    const minutes = Math.floor(elapsedTime / 60).toString().padStart(2, "0");
    const seconds = (elapsedTime % 60).toString().padStart(2, "0");
    setTimelineEvents((prev) => [{ time: `${minutes}:${seconds}`, text, type }, ...prev.slice(0, 19)]);
  };

  const handleIncomingTelemetry = (data: any) => {
    if (data.event === "object_detected" || data.event === "object_tracked") {
      setTargets((prev) => {
        const existingIdx = prev.findIndex((t) => t.object_id === data.object_id);
        const updated: TrackedTarget = {
          object_id: data.object_id,
          class: data.class || "drone",
          confidence: data.confidence || 0.9,
          bbox: data.bbox || [200, 150, 260, 210],
          velocity: data.velocity || [0, 0],
        };

        if (existingIdx >= 0) {
          const nextList = [...prev];
          nextList[existingIdx] = updated;
          return nextList;
        } else {
          addTimelineEvent("DETECTION", `Target ID ${data.object_id.toString().padStart(2, "0")} (${updated.class.toUpperCase()}) acquired on radar`);
          return [...prev, updated];
        }
      });
    } else if (data.event === "trainee_response") {
      addTimelineEvent("ACTION", `Trainee executed ${data.action.toUpperCase()} on Target ID ${data.object_id}`);
    }
  };

  const handleStartSession = async (difficulty: string = "hard") => {
    try {
      const resp = await fetch(`${API_BASE}/sessions/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          trainee_code: traineeCode,
          difficulty: difficulty,
        }),
      });

      if (!resp.ok) throw new Error("Failed to start session");
      const data = await resp.json();

      setSessionCode(data.session_code);
      setScenarioInfo({
        code: data.scenario_code,
        environment: "urban",
        lighting: "night",
        difficulty: difficulty,
        duration: 180,
      });

      setTargets([]);
      setSelectedTarget(null);
      setElapsedTime(0);
      setIsSessionActive(true);
      setAarReport(null);
      setTimelineEvents([]);
      addTimelineEvent("SESSION", `Scenario Started: ${data.scenario_code} (Difficulty: ${difficulty.toUpperCase()})`);

      // Seed initial simulated targets for demonstration
      setTimeout(() => {
        setTargets([
          { object_id: 1, class: "drone", confidence: 0.94, bbox: [220, 140, 280, 200], velocity: [3.2, 0.4] },
          { object_id: 2, class: "bird", confidence: 0.78, bbox: [410, 220, 450, 250], velocity: [-1.2, 0.8] },
          { object_id: 3, class: "drone", confidence: 0.89, bbox: [120, 310, 180, 370], velocity: [2.1, -1.5] },
        ]);
      }, 1000);
    } catch (e) {
      console.error(e);
    }
  };

  const handleEndSession = async () => {
    if (!sessionCode) return;
    try {
      const resp = await fetch(`${API_BASE}/sessions/end`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_code: sessionCode }),
      });

      if (!resp.ok) throw new Error("Failed to end session");
      const report: AARReportData = await resp.json();

      setIsSessionActive(false);
      setAarReport(report);
      addTimelineEvent("AAR", `Session Completed. Overall Score: ${report.overall_score}%`);

      // Fetch updated history
      fetchPerformanceHistory();
    } catch (e) {
      console.error(e);
    }
  };

  const handleActionSubmit = async (action: string, isCorrect: boolean, responseTime: number) => {
    if (!sessionCode || !selectedTarget) return;

    try {
      await fetch(`${API_BASE}/actions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_code: sessionCode,
          object_id: selectedTarget.object_id,
          action: action,
          timestamp: parseFloat((elapsedTime + 0.5).toFixed(2)),
          correct: isCorrect,
          response_time: responseTime,
        }),
      });

      addTimelineEvent("RESPONSE", `Submitted ${action.toUpperCase()} on Target ${selectedTarget.object_id}`);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchPerformanceHistory = async () => {
    try {
      const resp = await fetch(`${API_BASE}/performance/${traineeCode}`);
      if (resp.ok) {
        const data = await resp.json();
        setHistorySessions(data.sessions || []);
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchPerformanceHistory();
  }, [traineeCode]);

  const formatClock = (seconds: number) => {
    const mins = Math.floor(seconds / 60).toString().padStart(2, "0");
    const secs = (seconds % 60).toString().padStart(2, "0");
    return `${mins}:${secs}`;
  };

  return (
    <div className="flex flex-col min-h-screen p-4 sm:p-6 max-w-7xl mx-auto space-y-6">
      {/* Top HUD Header (Section 10) */}
      <header className="flex flex-col sm:flex-row justify-between items-start sm:items-center p-4 bg-slate-900 border border-slate-800 rounded-lg shadow-lg">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-lg font-bold tracking-wider text-cyan-400 font-mono">
              DRONE THREAT TRAINING SIMULATOR
            </h1>
            <Badge variant={wsConnected ? "green" : "destructive"}>
              {wsConnected ? "LIVE TELEMETRY" : "OFFLINE"}
            </Badge>
          </div>
          <p className="text-xs text-slate-400 font-mono mt-1">
            PERCEPTION & EVALUATION CONSOLE :: NON-KINETIC DEFENSE SIMULATOR
          </p>
        </div>

        <div className="flex items-center gap-4 mt-4 sm:mt-0 font-mono">
          <div className="text-right">
            <span className="text-xs text-slate-400 block">TRAINEE CODE</span>
            <span className="text-sm font-bold text-white">{traineeCode}</span>
          </div>

          <div className="text-right border-l border-slate-800 pl-4">
            <span className="text-xs text-slate-400 block">SIM TIME</span>
            <span className="text-xl font-extrabold text-cyan-400">{formatClock(elapsedTime)}</span>
          </div>

          {!isSessionActive ? (
            <Button variant="cyan" onClick={() => handleStartSession("hard")}>
              START SCENARIO
            </Button>
          ) : (
            <Button variant="destructive" onClick={handleEndSession}>
              END SCENARIO
            </Button>
          )}
        </div>
      </header>

      {/* Scenario Telemetry Bar */}
      <div className="flex flex-wrap items-center justify-between px-4 py-2 bg-slate-950 border border-slate-800 rounded-md font-mono text-xs">
        <div className="flex gap-4">
          <span>SCENARIO: <strong className="text-cyan-400">{scenarioInfo.code}</strong></span>
          <span>ENV: <strong className="text-slate-300">{scenarioInfo.environment.toUpperCase()}</strong></span>
          <span>LIGHTING: <strong className="text-slate-300">{scenarioInfo.lighting.toUpperCase()}</strong></span>
          <span>DIFFICULTY: <strong className="text-amber-400">{scenarioInfo.difficulty.toUpperCase()}</strong></span>
        </div>
        <div>
          <span>ACTIVE TARGETS: <strong className="text-cyan-400">{targets.length}</strong></span>
        </div>
      </div>

      {/* Main Simulation Workspace: Radar + Trainee Controls */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Radar View & Primary Controls */}
        <div className="lg:col-span-8 flex flex-col gap-6">
          <RadarView
            targets={targets}
            selectedId={selectedTarget ? selectedTarget.object_id : null}
            onSelectTarget={(target) => setSelectedTarget(target)}
            statusText={isSessionActive ? "TRACKING ACTIVE" : "STANDBY"}
          />

          <TraineeControls
            selectedTarget={selectedTarget}
            onActionSubmit={handleActionSubmit}
            disabled={!isSessionActive}
          />
        </div>

        {/* Right Column: Target Manifest & Event Timeline */}
        <div className="lg:col-span-4 flex flex-col gap-6">
          {/* Target Manifest */}
          <div className="p-4 bg-slate-900/90 border border-slate-800 rounded-lg">
            <h3 className="text-xs font-mono font-bold text-cyan-400 mb-3 uppercase tracking-wider">
              TARGET MANIFEST ({targets.length})
            </h3>
            <div className="space-y-2 max-h-52 overflow-y-auto pr-1">
              {targets.length === 0 ? (
                <p className="text-xs font-mono text-slate-500 italic">No active airborne targets.</p>
              ) : (
                targets.map((tgt) => (
                  <div
                    key={tgt.object_id}
                    onClick={() => setSelectedTarget(tgt)}
                    className={`flex justify-between items-center p-2 rounded border cursor-pointer font-mono text-xs transition-colors ${
                      selectedTarget?.object_id === tgt.object_id
                        ? "bg-cyan-500/10 border-cyan-500 text-cyan-300"
                        : "bg-slate-950 border-slate-800 hover:border-slate-700 text-slate-300"
                    }`}
                  >
                    <div>
                      <span className="font-bold">ID {tgt.object_id.toString().padStart(2, "0")}</span>
                      <span className="ml-2 text-slate-400 uppercase">({tgt.class})</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-400">{Math.round(tgt.confidence * 100)}%</span>
                      <Badge variant={tgt.class.includes("drone") ? "amber" : "green"}>
                        {tgt.class.includes("drone") ? "THREAT" : "BIO"}
                      </Badge>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Event Timeline (Section 13 & 14) */}
          <div className="p-4 bg-slate-900/90 border border-slate-800 rounded-lg flex-1 flex flex-col">
            <h3 className="text-xs font-mono font-bold text-cyan-400 mb-3 uppercase tracking-wider">
              EVENT TIMELINE
            </h3>
            <div className="space-y-2 overflow-y-auto max-h-72 pr-1 font-mono text-xs flex-1">
              {timelineEvents.length === 0 ? (
                <p className="text-xs text-slate-500 italic">No events logged yet.</p>
              ) : (
                timelineEvents.map((ev, i) => (
                  <div key={i} className="flex items-start gap-2 border-l border-cyan-500/30 pl-2 py-0.5">
                    <span className="text-cyan-400 font-bold shrink-0">{ev.time}</span>
                    <span className="text-slate-300">{ev.text}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>

      {/* After-Action Review (AAR) Section (Section 14) */}
      {aarReport && (
        <section className="pt-6">
          <AARReportView report={aarReport} onNewSession={() => handleStartSession("hard")} />
        </section>
      )}

      {/* Historical Performance Trends (Section 15) */}
      {historySessions.length > 0 && (
        <section className="pt-6">
          <PerformanceHistoryChart sessions={historySessions} traineeCode={traineeCode} />
        </section>
      )}
    </div>
  );
}
