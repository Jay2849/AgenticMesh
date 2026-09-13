import IncidentCard from "./IncidentCard";

export default function IncidentQueue({ incidents, onStatusUpdate }: { incidents: any[], onStatusUpdate: (id: string, s: string) => void }) {
  // Sort incidents by priority status
  const sorted = [...incidents].sort((a, b) => {
    const order: Record<string, number> = { "AWAITING_APPROVAL": 0, "REJECTED_OPEN": 1, "REMEDIATION_FAILED": 2, "REMEDIATED": 3 };
    const orderA = order[a.status] ?? 99;
    const orderB = order[b.status] ?? 99;
    return orderA - orderB;
  });

  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-xl font-semibold mb-2 flex items-center gap-2">
        Incident Queue
        <span className="bg-slate-800 text-slate-300 text-sm py-1 px-3 rounded-full">{incidents.length}</span>
      </h2>
      {sorted.length === 0 ? (
        <div className="border border-slate-800 rounded-lg p-8 text-center text-slate-500">
          No open incidents. System is healthy.
        </div>
      ) : (
        sorted.map(inc => (
          <IncidentCard key={inc.incident_id} incident={inc} onStatusUpdate={onStatusUpdate} />
        ))
      )}
    </div>
  );
}
