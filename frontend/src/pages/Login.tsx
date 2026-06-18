import { useState, type FormEvent } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "@/context/AuthContext"
import { AxiosError } from "axios"
import type { UserRole } from "@/types"
import { Activity, Shield, Stethoscope, Syringe, UserCheck, ArrowLeft } from "lucide-react"

interface RoleConfig {
  role: UserRole
  label: string
  description: string
  icon: React.ReactNode
}

const roles: RoleConfig[] = [
  {
    role: "admin",
    label: "Admin",
    description: "Full system access & management",
    icon: <Shield className="h-6 w-6" />,
  },
  {
    role: "doctor",
    label: "Doctor",
    description: "Reviews, prescriptions & discharge",
    icon: <Stethoscope className="h-6 w-6" />,
  },
  {
    role: "nurse",
    label: "Nurse",
    description: "Vitals, alerts & medication",
    icon: <Syringe className="h-6 w-6" />,
  },
  {
    role: "reception",
    label: "Receptionist",
    description: "Registration, appointments & check-in",
    icon: <UserCheck className="h-6 w-6" />,
  },
]

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [selectedRole, setSelectedRole] = useState<RoleConfig | null>(null)
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)

  function selectRole(role: RoleConfig) {
    setSelectedRole(role)
    setUsername("")
    setPassword("")
    setError("")
  }

  function back() {
    setSelectedRole(null)
    setUsername("")
    setPassword("")
    setError("")
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError("")

    if (!username.trim() || !password.trim()) {
      setError("Please fill all fields")
      return
    }

    setIsSubmitting(true)
    try {
      const res = await login({ username, password })
      navigate(`/dashboard/${res.role}`)
    } catch (err) {
      if (err instanceof AxiosError) {
        if (err.response?.status === 401) {
          setError("Invalid credentials")
        } else if (err.response?.status === 422) {
          setError("Please fill all fields")
        } else {
          setError("An error occurred. Please try again.")
        }
      } else {
        setError("An error occurred. Please try again.")
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  if (selectedRole) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-muted/30 p-4">
        <div className="w-full max-w-sm">
          <button
            type="button"
            onClick={back}
            className="mb-4 flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to role selection
          </button>

          <div className="rounded-lg border bg-background p-8 shadow-sm">
            <div className="mb-6 text-center">
              <div className="mb-2 flex items-center justify-center gap-2">
                <div className="text-primary">{selectedRole.icon}</div>
                <h1 className="text-xl font-bold">{selectedRole.label} Login</h1>
              </div>
              <p className="text-sm text-muted-foreground">
                {selectedRole.description}
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <label htmlFor="username" className="text-sm font-medium leading-none">
                  Username
                </label>
                <input
                  id="username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Enter username"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  autoFocus
                />
              </div>

              <div className="space-y-2">
                <label htmlFor="password" className="text-sm font-medium leading-none">
                  Password
                </label>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter password"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                />
              </div>

              {error && (
                <div className="rounded-md bg-destructive/15 p-3 text-sm text-destructive">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={isSubmitting}
                className="inline-flex h-10 w-full items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50"
              >
                {isSubmitting ? "Signing in..." : "Sign in"}
              </button>
            </form>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-muted/30 p-4">
      <div className="mb-6 text-center">
        <div className="mb-2 flex items-center justify-center gap-2">
          <Activity className="h-6 w-6 text-primary" />
          <h1 className="text-2xl font-bold">Hospital Event Simulation</h1>
        </div>
        <p className="text-sm text-muted-foreground">
          Select your role to sign in
        </p>
      </div>

      <div className="grid w-full max-w-lg gap-3 sm:grid-cols-2">
        {roles.map((role) => (
          <button
            key={role.role}
            type="button"
            onClick={() => selectRole(role)}
            className="group flex items-center gap-3 rounded-lg border bg-background p-4 text-left shadow-sm transition-all hover:border-primary hover:shadow-md"
          >
            <div className="shrink-0 text-muted-foreground group-hover:text-primary transition-colors">
              {role.icon}
            </div>
            <div className="min-w-0">
              <div className="font-medium">{role.label}</div>
              <div className="truncate text-xs text-muted-foreground">{role.description}</div>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
