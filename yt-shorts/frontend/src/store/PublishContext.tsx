import { createContext, useContext, useState } from 'react'

const GATE_ITEMS = [
  'Video plays start to finish without issues',
  'Hook lands in the first 3 seconds',
  'Captions are readable and accurate',
  'No copyrighted music or footage',
  'Loop is seamless (first = last clip)',
]

interface Ctx {
  jobId: string | null; setJobId: (id: string | null) => void
  checks: boolean[]; toggleCheck: (i: number) => void
  allChecked: boolean; gateItems: string[]; resetChecks: () => void
}

const PublishContext = createContext<Ctx | null>(null)

export function PublishProvider({ children }: { children: React.ReactNode }) {
  const [jobId, setJobId] = useState<string | null>(null)
  const [checks, setChecks] = useState<boolean[]>(Array(GATE_ITEMS.length).fill(false))
  const toggleCheck = (i: number) => setChecks(p => p.map((v, idx) => idx === i ? !v : v))
  const resetChecks = () => setChecks(Array(GATE_ITEMS.length).fill(false))
  return (
    <PublishContext.Provider value={{ jobId, setJobId, checks, toggleCheck, allChecked: checks.every(Boolean), gateItems: GATE_ITEMS, resetChecks }}>
      {children}
    </PublishContext.Provider>
  )
}

export function usePublishContext() {
  const ctx = useContext(PublishContext)
  if (!ctx) throw new Error('usePublishContext must be inside PublishProvider')
  return ctx
}
