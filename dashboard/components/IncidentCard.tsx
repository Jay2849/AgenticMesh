import ApprovalControls from "./ApprovalControls";
import { AlertCircle, CheckCircle2, XCircle } from "lucide-react";

export default function IncidentCard({ incident, onStatusUpdate }: { incident: any, onStatusUpdate: (id: string, s: string) => void }) {
  
  const StatusBadge = () => {
    switch (incident.status) {
      case "AWAITING_APPROVAL":
        return <span className="flex items-center gap-1 text-amber-400 bg-amber-400/10 px-3 py-1 rounded-full text-sm font-medium"><AlertCircle size={16}/> Awaiting Approval</span>;
      case "REJECTED_OPEN":
        return <span className="flex items-center gap-1 text-rose-400 bg-rose-400/10 px-3 py-1 rounded-full text-sm font-medium"><XCircle size={16}/> Rejected — needs manual review</span>;
      case "REMEDIATED":
      case "HEALTHY":
        return <span className="flex items-center gap-1 text-emerald-400 bg-emerald-400/10 px-3 py-1 rounded-full text-sm font-medium"><CheckCircle2 size={16}/> Remediated</span>;
      case "REMEDIATION_FAILED":
        return <span className="flex items-center gap-1 text-red-500 bg-red-500/10 px-3 py-1 rounded-full text-sm font-medium"><AlertCircle size={16}/> Remediation Failed</span>;
      default:
        return <span className="px-3 py-1 rounded-full text-sm font-medium bg-slate-800">{incident.status}</span>;
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-700 rounded-xl overflow-hidden shadow-lg">
      <div className="p-5 border-b border-slate-800 flex justify-between items-start bg-slate-800/50">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <h3 className="font-bold text-lg">{incident.incident_id}</h3>
            <StatusBadge />
          </div>
          <p className="text-slate-300 font-medium">Root Cause: <span className="text-slate-100">{incident.root_cause}</span></p>
          <div className="mt-2 text-sm text-slate-400">
            Confidence: <span className="text-emerald-400 font-mono">{(incident.confidence_score * 100).toFixed(1)}%</span>
          </div>
        </div>
      </div>
      
      <div className="p-5 grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <h4 className="text-sm font-semibold text-slate-400 mb-2 uppercase tracking-wider">Faulty Code ({incident.faulty_code_block?.file})</h4>
          <pre className="bg-slate-950 p-4 rounded-lg text-sm text-rose-300 font-mono overflow-x-auto">
            {incident.faulty_code_block?.code_snippet}
          </pre>
        </div>
        
        <div>
          <h4 className="text-sm font-semibold text-slate-400 mb-2 uppercase tracking-wider">Suggested Fix Diff</h4>
          <pre className="bg-slate-950 p-4 rounded-lg text-sm text-emerald-300 font-mono overflow-x-auto whitespace-pre-wrap">
            {incident.suggested_fix?.diff || "No diff available"}
          </pre>
        </div>
      </div>
      
      {incident.similar_historical_incidents && incident.similar_historical_incidents.length > 0 && (
        <div className="px-5 pb-5">
          <h4 className="text-sm font-semibold text-slate-400 mb-2 uppercase tracking-wider">Historical Context</h4>
          <div className="bg-slate-800/30 rounded-lg p-3 text-sm">
            <ul className="list-disc list-inside text-slate-300">
              {incident.similar_historical_incidents.map((hist: any, i: number) => (
                <li key={i}>
                  <span className="text-slate-500 font-mono">[{hist.incident_id}]</span> {(hist.similarity * 100).toFixed(0)}% match: {hist.resolution}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {(incident.status === "AWAITING_APPROVAL" || incident.status === "REJECTED_OPEN") && (
        <ApprovalControls incidentId={incident.incident_id} onStatusUpdate={onStatusUpdate} />
      )}
      
      {incident.remediation_details && (
        <div className="p-5 border-t border-slate-800 bg-emerald-950/20">
          <h4 className="text-sm font-semibold text-emerald-400 mb-1">Remediation Log</h4>
          <p className="text-sm text-slate-300">{incident.remediation_details.details}</p>
        </div>
      )}
    </div>
  );
}
