import { useEffect, useRef } from 'react'

export function useSSE(url: string | null, onMessage: (line: string) => void, onDone?: () => void) {
  const msgRef = useRef(onMessage)
  const doneRef = useRef(onDone)
  msgRef.current = onMessage
  doneRef.current = onDone

  useEffect(() => {
    if (!url) return
    const es = new EventSource(url)
    es.onmessage = (e) => {
      if (e.data === '[DONE]') { doneRef.current?.(); es.close() }
      else msgRef.current(e.data)
    }
    es.onerror = () => es.close()
    return () => es.close()
  }, [url])
}
