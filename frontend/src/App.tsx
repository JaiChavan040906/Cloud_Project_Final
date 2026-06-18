import { BrowserRouter, Routes, Route, Navigate, useParams } from "react-router-dom"
import { AuthProvider } from "@/context/AuthContext"
import ProtectedRoute from "@/components/ProtectedRoute"
import DashboardLayout from "@/layouts/DashboardLayout"
import Login from "@/pages/Login"
import Admin from "@/pages/Admin"

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />

          <Route path="/dashboard/:role" element={<ProtectedRoute />}>
            <Route element={<DashboardLayout />}>
              <Route index element={<DashboardRouter />} />
            </Route>
          </Route>

          <Route path="/" element={<Navigate to="/login" replace />} />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

function DashboardRouter() {
  const { role } = useParams<{ role: string }>()

  switch (role) {
    case "admin":
      return <Admin />
    default:
      return (
        <div className="flex items-center justify-center py-16">
          <p className="text-lg text-muted-foreground">Dashboard coming soon...</p>
        </div>
      )
  }
}
