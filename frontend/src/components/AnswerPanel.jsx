export default function AnswerPanel({ answer }) {
  const parts = answer.split(/(\[\d+\])/g) 

  return (
    <div className="panel">
      <h2>Here's what I found</h2>
      <div className="answer-text">
        {parts.map((part, i) =>
          /^\[\d+\]$/.test(part) ? (
            <span className="cite" key={i}>{part}</span>
          ) : (
            <span key={i}>{part}</span>
          )
        )}
      </div>
    </div>
  )
}
