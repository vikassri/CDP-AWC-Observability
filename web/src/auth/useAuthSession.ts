import { useCallback, useEffect, useState } from "react"
import { fetchAuthMe, login as apiLogin, logout as apiLogout } from "../api"

type AuthState =
  | { status: "loading" }
  | { status: "anonymous"; error: string | null }
  | { status: "authenticated"; username: string }

export function useAuthSession() {
  const [state, setState] = useState<AuthState>({ status: "loading" })

  const refresh = useCallback(async () => {
    try {
      const me = await fetchAuthMe()
      setState({ status: "authenticated", username: me.username })
    } catch {
      setState({ status: "anonymous", error: null })
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const login = useCallback(
    async (username: string, password: string) => {
      setState({ status: "anonymous", error: null })
      try {
        const me = await apiLogin(username, password)
        setState({ status: "authenticated", username: me.username })
      } catch (err) {
        const message = err instanceof Error ? err.message : "Login failed"
        setState({ status: "anonymous", error: message })
      }
    },
    []
  )

  const logout = useCallback(async () => {
    try {
      await apiLogout()
    } finally {
      setState({ status: "anonymous", error: null })
    }
  }, [])

  return { state, login, logout, refresh }
}
