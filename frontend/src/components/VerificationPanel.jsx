import TrustStamp from './TrustStamp.jsx'

function summarize(v) {
  const problems = []
  if (v.invalid_citations.length > 0) problems.push('cited a source that was never shown to it')
  if (!v.integrity_ok) problems.push("a cited log line doesn't match what's on record")
  if (v.unsupported_claims.length > 0) problems.push('made a claim without pointing to a source')

  if (problems.length === 0) {
    return 'Every claim in this answer points back to a real log line.'
  }
  return `Something to double-check: the answer ${problems.join(', and ')}.`
}

export default function VerificationPanel({ verification }) {
  if (!verification) return null

  return (
    <div className="panel">
      <h2>How sure can you be?</h2>

      <div className="verify-top">
        <TrustStamp score={verification.trust_score} />
        <div className="verify-summary">
          <div className="headline">{summarize(verification)}</div>
          <div>We check every citation against the original log line before you see it.</div>
        </div>
      </div>

      <div className="check-row">
        <span>Sources it actually cited</span>
        <span className="status-ok">{verification.valid_citations.join(', ') || '—'}</span>
      </div>

      <div className="check-row">
        <span>Sources it made up</span>
        <span className={verification.invalid_citations.length ? 'status-bad' : 'status-ok'}>
          {verification.invalid_citations.join(', ') || 'none'}
        </span>
      </div>

      <div className="check-row">
        <span>Log lines match the original</span>
        <span className={verification.integrity_ok ? 'status-ok' : 'status-bad'}>
          {verification.integrity_ok ? 'Yes' : 'No — mismatch found'}
        </span>
      </div>

      {verification.unsupported_claims.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <div style={{ fontSize: 13, color: 'var(--ink-dim)', marginBottom: 6 }}>
            Said without pointing to a source:
          </div>
          {verification.unsupported_claims.map((claim, i) => (
            <div className="claim" key={i}>{claim}</div>
          ))}
        </div>
      )}
    </div>
  )
}
