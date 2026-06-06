import { useState, useEffect } from 'react'
import UploadZone from './components/UploadZone.jsx'
import StatusBar from './components/StatusBar.jsx'
import QueryBox from './components/QueryBox.jsx'
import AnswerPanel from './components/AnswerPanel.jsx'
import VerificationPanel from './components/VerificationPanel.jsx'
import SourceList from './components/SourceList.jsx'
import { fetchStatus, askQuestion } from './api.js'

export default function App() {
  const [status, setStatus] = useState(null)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function refreshStatus() {
    try {
      const data = await fetchStatus()
      setStatus(data)
    } catch {
      setStatus({ index_ready: false, stats: null })
    }
  }

  useEffect(() => {
    refreshStatus()
  }, [])

  async function handleAsk(question) {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await askQuestion(question)
      if (data.error) {
        setError(data.error)
      } else {
        setResult(data)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <header>
        <div className="brand">Log Analyst</div>
        <div className="tagline">Ask questions about your logs. Every answer points back to the exact line it came from.</div>
      </header>

      <main>
        <UploadZone onUploaded={refreshStatus} />
        <StatusBar status={status} />

        <QueryBox onAsk={handleAsk} disabled={loading} />

        {loading && <p className="loading">Reading through the evidence…</p>}
        {error && <p className="error">{error}</p>}

        {result && (
          <>
            <AnswerPanel answer={result.answer} />
            <VerificationPanel verification={result.verification} />
            <SourceList sources={result.sources} />
          </>
        )}
      </main>
    </>
  )
}
