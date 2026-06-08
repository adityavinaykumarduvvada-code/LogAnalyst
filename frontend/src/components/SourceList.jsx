import SourceCard from './SourceCard.jsx'

export default function SourceList({ sources }) {
  if (!sources || sources.length === 0) return null

  return (
    <div className="panel">
      <h2>The evidence ({sources.length})</h2>
      {sources.map((source) => (
        <SourceCard source={source} key={source.chunk_id} />
      ))}
    </div>
  )
}
