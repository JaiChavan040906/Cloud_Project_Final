import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { AuthProvider } from "@/context/AuthContext"
import ProtectedRoute from "@/components/ProtectedRoute"
import Login from "@/pages/Login"

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />

          <Route path="/dashboard/:role" element={<ProtectedRoute />}>
            <Route index element={<DashboardPlaceholder />} />
          </Route>

          <Route path="/" element={<Navigate to="/login" replace />} />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

function DashboardPlaceholder() {
  return (
    <div className="flex h-screen items-center justify-center">
      <p className="text-lg text-muted-foreground">
        Dashboard coming soon...
      </p>
    </div>
  )
}
