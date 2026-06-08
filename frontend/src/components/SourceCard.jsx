export default function SourceCard({ source }) {
  return (
    <div className="source">
      <div className="source-meta">
        <span>
          <span className="idx">[{source.index}]</span>{' '}
          {source.source_file}:{source.lines[0]}-{source.lines[1]} ·{' '}
          {source.log_types.join(',')} · rel {source.relevance}
        </span>
        <span className="hash">{source.hash.slice(0, 12)}…</span>
      </div>
      <div className="source-text">{source.text}</div>
    </div>
  )
}
