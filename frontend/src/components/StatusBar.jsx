export default function StatusBar({ status }) {
  if (!status) {
    return (
      <div className="status-bar">
        <span><span className="dot"></span>Checking what's already indexed…</span>
      </div>
    )
  }

  if (!status.index_ready) {
    return (
      <div className="status-bar empty">
        <span><span className="dot"></span>Nothing indexed yet — add some logs above to get started</span>
      </div>
    )
  }

  return (
    <div className="status-bar ready">
      <span><span className="dot"></span>Ready — {status.stats.chunks_indexed} log lines indexed</span>
      <span>
        {status.stats.source_files.map((f) => (
          <span className="file-chip" key={f}>{f}</span>
        ))}
      </span>
    </div>
  )
}
