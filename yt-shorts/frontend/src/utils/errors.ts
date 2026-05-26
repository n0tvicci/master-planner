export function getAxiosErrorMessage(error: unknown, fallback: string): string {
  const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
  if (detail) return detail
  if (error instanceof Error) return error.message
  return fallback
}
