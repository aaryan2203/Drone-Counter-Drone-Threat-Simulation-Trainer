"use client";

import React from "react";
import { Card, CardHeader, CardTitle, CardContent } from "./ui/card";
import { Badge } from "./ui/badge";
import { Progress } from "./ui/progress";

export interface AARReportData {
  id: number;
  session_code: string;
  trainee_code: string;
  scenario_code: string;
  environment: string;
  lighting: string;
  difficulty: string;
  duration: number;
  detection_score: number;
  classification_score: number;
  decision_score: number;
  response_score: number;
  overall_score: number;
  total_detections: number;
  correct_actions: number;
  total_actions: number;
  avg_response_time: number;
  summary_notes?: string;
  created_at: string;
}

interface AARReportViewProps {
  report: AARReportData;
  onNewSession?: () => void;
}

export function AARReportView({ report, onNewSession }: AARReportViewProps) {
  return (
    <Card className="max-w-4xl mx-auto border-cyan-500/40 bg-slate-950/90 shadow-2xl">
      <CardHeader className="flex flex-row items-center justify-between border-b border-cyan-500/20 pb-4">
        <div>
          <span className="text-xs font-mono text-cyan-400 block tracking-widest">
            AFTER-ACTION REVIEW (AAR) REPORT
          </span>
          <CardTitle className="text-xl text-white font-mono mt-1">
            SESSION: {report.session_code}
          </CardTitle>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            TRAINEE: {report.trainee_code} | SCENARIO: {report.scenario_code}
          </p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <Badge variant="cyan" className="font-mono">
            {report.difficulty.toUpperCase()} DIFFICULTY
          </Badge>
          <span className="text-xs font-mono text-slate-400">
            {report.environment.toUpperCase()} / {report.lighting.toUpperCase()}
          </span>
        </div>
      </CardHeader>

      <CardContent className="space-y-6 pt-6">
        {/* Composite Score Banner */}
        <div className="flex flex-col sm:flex-row items-center justify-between p-5 bg-slate-900/80 border border-slate-800 rounded-lg">
          <div>
            <h4 className="text-sm font-mono text-slate-400 uppercase">Overall Simulation Score</h4>
            <p className="text-xs text-slate-500 mt-1 max-w-md">
              Calculated using weighted parameters: Detection (30%), Classification (30%), Decision (30%), Response Time (10%).
            </p>
          </div>
          <div className="text-center sm:text-right mt-4 sm:mt-0">
            <span className="text-4xl font-extrabold font-mono text-cyan-400">
              {report.overall_score}%
            </span>
            <span className="block text-xs font-mono text-slate-400 mt-1">
              STATUS: {report.overall_score >= 70 ? "PASSED" : "REQUIRES RETEST"}
            </span>
          </div>
        </div>

        {/* Detailed Metrics Breakdown */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {/* Left Column: Progress Bars */}
          <div className="space-y-4 p-4 bg-slate-900/40 rounded-lg border border-slate-800">
            <div>
              <div className="flex justify-between text-xs font-mono mb-1">
                <span className="text-slate-300">DETECTION EFFICIENCY (30%)</span>
                <span className="text-cyan-400 font-bold">{report.detection_score}%</span>
              </div>
              <Progress value={report.detection_score} indicatorColor="bg-cyan-500" />
            </div>

            <div>
              <div className="flex justify-between text-xs font-mono mb-1">
                <span className="text-slate-300">CLASSIFICATION ACCURACY (30%)</span>
                <span className="text-emerald-400 font-bold">{report.classification_score}%</span>
              </div>
              <Progress value={report.classification_score} indicatorColor="bg-emerald-500" />
            </div>

            <div>
              <div className="flex justify-between text-xs font-mono mb-1">
                <span className="text-slate-300">DECISION ADHERENCE (30%)</span>
                <span className="text-amber-400 font-bold">{report.decision_score}%</span>
              </div>
              <Progress value={report.decision_score} indicatorColor="bg-amber-500" />
            </div>

            <div>
              <div className="flex justify-between text-xs font-mono mb-1">
                <span className="text-slate-300">RESPONSE LATENCY SCORE (10%)</span>
                <span className="text-blue-400 font-bold">{report.response_score}%</span>
              </div>
              <Progress value={report.response_score} indicatorColor="bg-blue-500" />
            </div>
          </div>

          {/* Right Column: Statistics Grid */}
          <div className="grid grid-cols-2 gap-3 p-4 bg-slate-900/40 rounded-lg border border-slate-800 text-center font-mono">
            <div className="p-3 bg-slate-950/60 rounded border border-slate-800">
              <span className="text-xs text-slate-400 block">TOTAL DETECTIONS</span>
              <span className="text-2xl font-bold text-white mt-1 block">{report.total_detections}</span>
            </div>

            <div className="p-3 bg-slate-950/60 rounded border border-slate-800">
              <span className="text-xs text-slate-400 block">DECISIONS CORRECT</span>
              <span className="text-2xl font-bold text-emerald-400 mt-1 block">
                {report.correct_actions} / {report.total_actions}
              </span>
            </div>

            <div className="p-3 bg-slate-950/60 rounded border border-slate-800">
              <span className="text-xs text-slate-400 block">AVG LATENCY</span>
              <span className="text-2xl font-bold text-cyan-400 mt-1 block">
                {report.avg_response_time}s
              </span>
            </div>

            <div className="p-3 bg-slate-950/60 rounded border border-slate-800">
              <span className="text-xs text-slate-400 block">DURATION</span>
              <span className="text-2xl font-bold text-white mt-1 block">{report.duration}s</span>
            </div>
          </div>
        </div>

        {/* Evaluator Notes */}
        {report.summary_notes && (
          <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-lg font-mono text-xs text-slate-300">
            <span className="text-cyan-400 font-bold block mb-1">SIMULATION EVALUATION SUMMARY:</span>
            {report.summary_notes}
          </div>
        )}

        {/* Restart / New Scenario Button */}
        {onNewSession && (
          <div className="flex justify-end pt-2">
            <button
              onClick={onNewSession}
              className="px-6 py-2.5 bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold font-mono text-sm rounded shadow-lg shadow-cyan-500/20 cursor-pointer"
            >
              GENERATE NEW TRAINING SCENARIO →
            </button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
