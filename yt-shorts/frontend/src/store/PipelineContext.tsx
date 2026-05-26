import { createContext, useCallback, useContext, useState } from 'react'

interface Ctx {
  activeJobId: string | null
  isRunning: boolean
  setActiveJob: (id: string) => void
  setRunning: (v: boolean) => void
}

const PipelineContext = createContext<Ctx | null>(null)

export function PipelineProvider({ children }: { children: React.ReactNode }) {
  const [activeJobId, setActiveJobId] = useState<string | null>(null)
  const [isRunning, setIsRunning] = useState(false)
  const setActiveJob = useCallback((id: string) => setActiveJobId(id), [])
  const setRunning = useCallback((v: boolean) => setIsRunning(v), [])
  return (
    <PipelineContext.Provider value={{ activeJobId, isRunning, setActiveJob, setRunning }}>
      {children}
    </PipelineContext.Provider>
  )
}

export function usePipelineContext() {
  const ctx = useContext(PipelineContext)
  if (!ctx) throw new Error('usePipelineContext must be inside PipelineProvider')
  return ctx
}
