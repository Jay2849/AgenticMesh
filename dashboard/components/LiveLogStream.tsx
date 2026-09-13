export default function LiveLogStream({ logs }: { logs: any[] }) {
  // We're mocking live logs for visual effect in the dashboard, 
  // normally these would flow from WebSocket. 
  // In our simplified setup, the frontend generates some green mock logs.
  return (
    <div className="h-full bg-slate-950 border border-slate-800 rounded-xl overflow-hidden flex flex-col">
      <div className="p-4 border-b border-slate-800 bg-slate-900 flex justify-between items-center">
        <h3 className="font-semibold text-sm tracking-wider uppercase text-slate-400">Live Traffic Logs</h3>
        <span className="flex h-2 w-2 relative">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
        </span>
      </div>
      <div className="p-4 flex-1 overflow-y-auto font-mono text-xs flex flex-col gap-1">
        {logs.length === 0 ? (
          <div className="text-slate-600 italic">Waiting for log stream...</div>
        ) : (
          logs.map((log, i) => (
            <div key={i} className={`py-1 border-b border-slate-800/50 ${log.level === 'ERROR' ? 'text-rose-400' : 'text-emerald-400/70'}`}>
              <span className="text-slate-500 mr-2">[{log.timestamp}]</span>
              <span className="font-semibold mr-2">[{log.service}]</span>
              {log.message}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
