import { BrowserRouter, Routes, Route, Navigate, useParams } from "react-router-dom"
import { AuthProvider } from "@/context/AuthContext"
import ProtectedRoute from "@/components/ProtectedRoute"
import ErrorBoundary from "@/components/ErrorBoundary"
import DashboardLayout from "@/layouts/DashboardLayout"
import Login from "@/pages/Login"
import Simulator from "@/pages/Simulator"
import Admin from "@/pages/Admin"
import Receptionist from "@/pages/Receptionist"
import Nurse from "@/pages/Nurse"
import Doctor from "@/pages/Doctor"

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/" element={<Simulator />} />
            <Route path="/login" element={<Login />} />

            <Route path="/dashboard/:role" element={<ProtectedRoute />}>
              <Route element={<DashboardLayout />}>
                <Route index element={<DashboardRouter />} />
              </Route>
            </Route>

            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </ErrorBoundary>
  )
}

function DashboardRouter() {
  const { role } = useParams<{ role: string }>()

  switch (role) {
    case "admin":
      return <Admin />
    case "reception":
      return <Receptionist />
    case "nurse":
      return <Nurse />
    case "doctor":
      return <Doctor />
    default:
      return (
        <div className="flex items-center justify-center py-16">
          <p className="text-lg text-muted-foreground">Dashboard coming soon...</p>
        </div>
      )
  }
}
