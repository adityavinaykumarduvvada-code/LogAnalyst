import { useState } from 'react'

const EXAMPLES = [
  'Were there any SSH brute force attempts?',
  'Did any IP attempt SQL injection on the login page?',
  'Summarize suspicious activity from 198.51.100.77',
]

export default function QueryBox({ onAsk, disabled }) {
  const [question, setQuestion] = useState('')

  function submit(text) {
    const q = text.trim()
    if (!q) return
    onAsk(q)
  }

  return (
    <>
      <div className="query-row">
        <input
          id="question"
          type="text"
          placeholder="Ask something about your logs…"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') submit(question) }}
        />
        <button className="primary" disabled={disabled} onClick={() => submit(question)}>
          Ask
        </button>
      </div>

      <div className="examples">
        Not sure where to start? Try:{' '}
        {EXAMPLES.map((ex) => (
          <button key={ex} onClick={() => { setQuestion(ex); submit(ex) }}>
            {ex.length > 28 ? ex.slice(0, 28) + '…' : ex}
          </button>
        ))}
      </div>
    </>
  )
}
