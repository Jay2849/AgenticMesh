"use client";

import { useEffect, useState } from "react";
import { io } from "socket.io-client";
import IncidentQueue from "@/components/IncidentQueue";
import LiveLogStream from "@/components/LiveLogStream";

export default function Dashboard() {
  const [incidents, setIncidents] = useState<any[]>([]);
  const [logs, setLogs] = useState<any[]>([]);

  useEffect(() => {
    const socket = io();

    socket.on("incident", (data) => {
      setIncidents((prev) => [data, ...prev.filter((i) => i.incident_id !== data.incident_id)]);
    });

    socket.on("remediation", (data) => {
      setIncidents((prev) =>
        prev.map((i) => (i.incident_id === data.incident_id ? { ...i, status: data.final_status, remediation_details: data } : i))
      );
    });

    return () => {
      socket.disconnect();
    };
  }, []);

  const handleStatusUpdate = (incident_id: string, newStatus: string) => {
    setIncidents((prev) =>
      prev.map((i) => (i.incident_id === incident_id ? { ...i, status: newStatus } : i))
    );
  };

  return (
    <main className="flex min-h-screen flex-col p-6 max-w-7xl mx-auto gap-6">
      <header className="mb-4">
        <h1 className="text-3xl font-bold tracking-tight">AgenticMesh</h1>
        <p className="text-slate-400">AI-accelerated incident triage with human-approved automated remediation</p>
      </header>
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <IncidentQueue incidents={incidents} onStatusUpdate={handleStatusUpdate} />
        </div>
        <div className="lg:col-span-1 h-[800px]">
          <LiveLogStream logs={logs} />
        </div>
      </div>
    </main>
  );
}
