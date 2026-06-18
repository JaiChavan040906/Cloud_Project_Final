import { Navigate, Outlet, useParams } from "react-router-dom"
import { useAuth } from "@/context/AuthContext"
import type { UserRole } from "@/types"

const roleHierarchy: Record<UserRole, UserRole[]> = {
  admin: ["admin", "doctor", "nurse", "reception"],
  doctor: ["doctor", "admin"],
  nurse: ["nurse", "admin"],
  reception: ["reception", "admin"],
}

export default function ProtectedRoute() {
  const { user, isLoading } = useAuth()
  const { role } = useParams<{ role: string }>()

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        Loading...
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  if (role && role !== user.role) {
    const allowed = roleHierarchy[user.role] ?? [user.role]
    if (!allowed.includes(role as UserRole)) {
      return (
        <div className="flex h-screen items-center justify-center">
          <div className="text-center">
            <h1 className="text-2xl font-bold text-destructive">403</h1>
            <p className="mt-2 text-muted-foreground">
              You do not have access to this dashboard.
            </p>
          </div>
        </div>
      )
    }
  }

  return <Outlet />
}
