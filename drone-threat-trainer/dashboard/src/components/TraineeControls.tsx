"use client";

import React, { useState } from "react";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { TrackedTarget } from "./RadarView";

interface TraineeControlsProps {
  selectedTarget: TrackedTarget | null;
  onActionSubmit: (action: string, isCorrect: boolean, responseTime: number) => Promise<void>;
  disabled?: boolean;
}

export function TraineeControls({ selectedTarget, onActionSubmit, disabled = false }: TraineeControlsProps) {
  const [responseModalOpen, setResponseModalOpen] = useState(false);
  const [lastActionStatus, setLastActionStatus] = useState<string | null>(null);

  const handleAction = async (actionName: string, isCorrect: boolean = true) => {
    if (!selectedTarget) return;
    const responseTime = parseFloat((Math.random() * 2.5 + 1.2).toFixed(2));
    await onActionSubmit(actionName, isCorrect, responseTime);
    setLastActionStatus(`Action executed: ${actionName.toUpperCase()} on Target ${selectedTarget.object_id}`);
    setResponseModalOpen(false);
  };

  return (
    <div className="flex flex-col gap-4 p-5 bg-slate-900/90 border border-slate-800 rounded-lg">
      <div className="flex justify-between items-center border-b border-slate-800 pb-3">
        <div>
          <span className="text-xs font-mono text-slate-400 block">LOCKED TARGET</span>
          {selectedTarget ? (
            <div className="flex items-center gap-2 mt-1">
              <span className="text-lg font-bold font-mono text-cyan-400">
                TARGET ID {selectedTarget.object_id.toString().padStart(2, "0")}
              </span>
              <Badge variant={selectedTarget.class.toLowerCase().includes("drone") ? "amber" : "green"}>
                {selectedTarget.class.toUpperCase()}
              </Badge>
              <span className="text-xs text-slate-400">
                ({Math.round(selectedTarget.confidence * 100)}% Conf)
              </span>
            </div>
          ) : (
            <span className="text-sm text-slate-500 font-mono italic">NO TARGET SELECTED (CLICK RADAR BLIP)</span>
          )}
        </div>
        {lastActionStatus && (
          <span className="text-xs font-mono text-emerald-400 animate-pulse">{lastActionStatus}</span>
        )}
      </div>

      {/* Trainee Primary Action Buttons (Section 10) */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Button
          variant="outline"
          size="lg"
          disabled={!selectedTarget || disabled}
          onClick={() => handleAction("detect", true)}
          className="border-cyan-500/40 hover:bg-cyan-500/20 text-cyan-300 font-mono tracking-wider"
        >
          [DETECT]
        </Button>

        <Button
          variant="outline"
          size="lg"
          disabled={!selectedTarget || disabled}
          onClick={() => handleAction(`classify_${selectedTarget?.class || "drone"}`, true)}
          className="border-emerald-500/40 hover:bg-emerald-500/20 text-emerald-300 font-mono tracking-wider"
        >
          [IDENTIFY]
        </Button>

        <Button
          variant="outline"
          size="lg"
          disabled={!selectedTarget || disabled}
          onClick={() => handleAction("commit_tracking", true)}
          className="border-blue-500/40 hover:bg-blue-500/20 text-blue-300 font-mono tracking-wider"
        >
          [TRACK]
        </Button>

        <Button
          variant="amber"
          size="lg"
          disabled={!selectedTarget || disabled}
          onClick={() => setResponseModalOpen(true)}
          className="font-mono tracking-wider font-bold"
        >
          [RESPOND]
        </Button>
      </div>

      {/* Predefined Training Response Selector Modal */}
      {responseModalOpen && selectedTarget && (
        <div className="mt-2 p-4 bg-slate-950/95 border border-amber-500/50 rounded-md">
          <div className="flex justify-between items-center mb-3">
            <span className="text-xs font-mono font-bold text-amber-400">
              SELECT PREDEFINED TRAINING RESPONSE (SECTION 11)
            </span>
            <button
              onClick={() => setResponseModalOpen(false)}
              className="text-xs text-slate-400 hover:text-slate-200 cursor-pointer font-mono"
            >
              ✕ CANCEL
            </button>
          </div>
          <p className="text-xs text-slate-400 mb-3">
            Note: System evaluates procedural training decisions. Real-world weapon engagement is prohibited.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleAction("respond_jam_rf", true)}
              className="border-amber-500/50 hover:bg-amber-500/20 text-amber-300 text-xs font-mono"
            >
              PROTOCOL 4A: RF JAMMING
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleAction("respond_alert_command", true)}
              className="border-cyan-500/50 hover:bg-cyan-500/20 text-cyan-300 text-xs font-mono"
            >
              PROTOCOL 2B: ALERT COMMAND
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleAction("respond_log_only", !selectedTarget.class.includes("drone"))}
              className="border-slate-600 hover:bg-slate-800 text-slate-300 text-xs font-mono"
            >
              PROTOCOL 1A: LOG & MONITOR
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
