function trustLevel(score) {
  if (score >= 0.75) return { color: 'var(--teal)', word: 'Checks out' }
  if (score >= 0.4) return { color: 'var(--amber)', word: 'Mixed' }
  return { color: 'var(--rust)', word: 'Caution' }
}

export default function TrustStamp({ score }) {
  const { color, word } = trustLevel(score)
  return (
    <div className="stamp" style={{ '--stamp-color': color }}>
      <div className="pct">{Math.round(score * 100)}%</div>
      <div className="label">{word}</div>
    </div>
  )
}
