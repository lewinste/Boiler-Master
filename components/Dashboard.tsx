"use client";

import { useEffect, useState, useCallback } from "react";
import { getTodayReadings, Reading } from "@/lib/supabase";
import { detectShowers, ShowerAnalysis } from "@/lib/shower-detection";
import TemperatureChart from "./TemperatureChart";

const REFRESH_INTERVAL = 30_000; // 30 seconds

export default function Dashboard() {
  const [readings, setReadings] = useState<Reading[]>([]);
  const [analysis, setAnalysis] = useState<ShowerAnalysis>({
    showers: [],
    totalHotWaterMinutes: 0,
    baseline: 0,
    threshold: 0,
  });
  const [currentTemp, setCurrentTemp] = useState<number | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    const data = await getTodayReadings();
    setReadings(data);

    if (data.length > 0) {
      setCurrentTemp(data[data.length - 1].temperature);
      setLastUpdate(new Date(data[data.length - 1].timestamp));
    }

    const result = detectShowers(data);
    setAnalysis(result);
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, REFRESH_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchData]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-slate-400 text-lg">Loading readings...</div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-4 md:p-6 space-y-6">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Boiler Monitor</h1>
        {lastUpdate && (
          <span className="text-xs text-slate-500">
            Updated{" "}
            {lastUpdate.toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
              second: "2-digit",
            })}
          </span>
        )}
      </header>

      {/* Stats cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard
          label="Current Temp"
          value={currentTemp !== null ? `${currentTemp.toFixed(1)}°C` : "—"}
          color="sky"
        />
        <StatCard
          label="Showers Today"
          value={String(analysis.showers.length)}
          color="violet"
        />
        <StatCard
          label="Hot Water"
          value={`${analysis.totalHotWaterMinutes} min`}
          color="amber"
        />
        <StatCard
          label="Baseline / Threshold"
          value={`${analysis.baseline}° / ${analysis.threshold}°`}
          color="emerald"
        />
      </div>

      {/* Chart */}
      {readings.length > 0 ? (
        <TemperatureChart
          readings={readings}
          threshold={analysis.threshold}
          showers={analysis.showers}
        />
      ) : (
        <div className="bg-slate-800 rounded-xl p-12 text-center text-slate-500">
          No readings yet today. Data starts from 05:00.
        </div>
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color: string;
}) {
  const colorMap: Record<string, string> = {
    sky: "text-sky-400",
    violet: "text-violet-400",
    amber: "text-amber-400",
    emerald: "text-emerald-400",
  };

  return (
    <div className="bg-slate-800 rounded-xl p-4">
      <div className="text-xs text-slate-500 uppercase tracking-wide mb-1">
        {label}
      </div>
      <div className={`text-2xl font-bold ${colorMap[color] ?? "text-white"}`}>
        {value}
      </div>
    </div>
  );
}
