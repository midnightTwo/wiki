import { useEffect } from 'react'

export default function Toast({ message, type = 'success', onClose }) {
  useEffect(() => {
    const timer = setTimeout(onClose, 4000)
    return () => clearTimeout(timer)
  }, [onClose])

  return (
    <div className="toast-container">
      <div className={`toast toast-${type} animate-slide-in`}>
        <span>{type === 'success' ? '✓' : type === 'error' ? '✕' : '⚠'}</span>
        <span>{message}</span>
        <button className="toast-close" onClick={onClose}>✕</button>
      </div>
    </div>
  )
}
