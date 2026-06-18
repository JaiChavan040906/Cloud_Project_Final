import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from "react"
import client from "@/api/client"
import type { LoginRequest, LoginResponse, AuthUser } from "@/types"

interface AuthContextType {
  user: AuthUser | null
  isLoading: boolean
  login: (data: LoginRequest) => Promise<LoginResponse>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => {
    const token = localStorage.getItem("token")
    const stored = localStorage.getItem("user")
    if (token && stored) {
      try {
        return JSON.parse(stored)
      } catch {
        localStorage.removeItem("token")
        localStorage.removeItem("user")
      }
    }
    return null
  })
  const [isLoading] = useState(false)

  const login = useCallback(async (data: LoginRequest) => {
    const res = await client.post<LoginResponse>("/auth/login", data)
    const { access_token, role, username } = res.data
    const authUser: AuthUser = { username, role, token: access_token }
    localStorage.setItem("token", access_token)
    localStorage.setItem("user", JSON.stringify(authUser))
    setUser(authUser)
    return res.data
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem("token")
    localStorage.removeItem("user")
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used within AuthProvider")
  return ctx
}
