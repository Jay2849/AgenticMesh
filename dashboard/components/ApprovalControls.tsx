import { useState } from "react";
import { Check, X, Loader2 } from "lucide-react";

export default function ApprovalControls({ incidentId, onStatusUpdate }: { incidentId: string, onStatusUpdate: (id: string, s: string) => void }) {
  const [loading, setLoading] = useState(false);

  const handleDecision = async (decision: "APPROVED" | "REJECTED") => {
    setLoading(true);
    try {
      await fetch("/api/approve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          incident_id: incidentId,
          decision: decision,
          approved_by: "engineer_demo_user",
          timestamp: new Date().toISOString(),
          action: "ROLLBACK_CONTAINER"
        }),
      });
      // Optimistically update
      onStatusUpdate(incidentId, decision === "APPROVED" ? "APPROVED" : "REJECTED_OPEN");
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  return (
    <div className="p-5 bg-slate-950 flex items-center justify-between border-t border-slate-800">
      <div className="text-sm text-slate-400">
        Requires human approval before executing remediation.
      </div>
      <div className="flex gap-3">
        <button
          onClick={() => handleDecision("REJECTED")}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 rounded-lg font-medium bg-slate-800 text-rose-400 hover:bg-slate-700 transition-colors"
        >
          {loading ? <Loader2 className="animate-spin" size={18} /> : <X size={18} />}
          REJECT
        </button>
        <button
          onClick={() => handleDecision("APPROVED")}
          disabled={loading}
          className="flex items-center gap-2 px-6 py-2 rounded-lg font-bold bg-emerald-600 text-white hover:bg-emerald-500 transition-colors shadow-lg shadow-emerald-900/50"
        >
          {loading ? <Loader2 className="animate-spin" size={18} /> : <Check size={18} />}
          APPROVE FIX
        </button>
      </div>
    </div>
  );
}
