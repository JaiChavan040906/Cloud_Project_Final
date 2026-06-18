import { useState } from "react"
import { Outlet, useNavigate, useLocation } from "react-router-dom"
import { useAuth } from "@/context/AuthContext"
import NotificationPanel from "@/components/NotificationPanel"
import type { UserRole } from "@/types"
import {
  LayoutDashboard,
  Users,
  AlertTriangle,
  Pill,
  ClipboardList,
  Activity,
  LogOut,
  Menu,
  X,
  Syringe,
  UserCheck,
} from "lucide-react"

interface NavItem {
  label: string
  icon: React.ReactNode
  path: string
  roles: UserRole[]
}

const navItems: NavItem[] = [
  {
    label: "Overview",
    icon: <LayoutDashboard className="h-4 w-4" />,
    path: "/dashboard/admin",
    roles: ["admin"],
  },
  {
    label: "Admissions",
    icon: <UserCheck className="h-4 w-4" />,
    path: "/dashboard/admin?tab=admissions",
    roles: ["admin"],
  },
  {
    label: "Alerts",
    icon: <AlertTriangle className="h-4 w-4" />,
    path: "/dashboard/admin?tab=alerts",
    roles: ["admin"],
  },
  {
    label: "Patients",
    icon: <Users className="h-4 w-4" />,
    path: "/dashboard/reception",
    roles: ["reception"],
  },
  {
    label: "Assigned Patients",
    icon: <UserCheck className="h-4 w-4" />,
    path: "/dashboard/nurse",
    roles: ["nurse", "admin"],
  },
  {
    label: "Vitals",
    icon: <Activity className="h-4 w-4" />,
    path: "/dashboard/nurse?tab=vitals",
    roles: ["nurse"],
  },
  {
    label: "Medications",
    icon: <Pill className="h-4 w-4" />,
    path: "/dashboard/nurse?tab=medications",
    roles: ["nurse"],
  },
  {
    label: "Review Queue",
    icon: <ClipboardList className="h-4 w-4" />,
    path: "/dashboard/doctor",
    roles: ["doctor", "admin"],
  },
  {
    label: "Prescriptions",
    icon: <Syringe className="h-4 w-4" />,
    path: "/dashboard/doctor?tab=prescriptions",
    roles: ["doctor"],
  },
]

const roleLabels: Record<UserRole, string> = {
  admin: "Administrator",
  doctor: "Doctor",
  nurse: "Nurse",
  reception: "Receptionist",
}

export default function DashboardLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const filteredItems = navItems.filter(
    (item) => user && item.roles.includes(user.role as UserRole),
  )

  function handleNav(path: string) {
    navigate(path)
    setSidebarOpen(false)
  }

  return (
    <div className="flex h-screen overflow-hidden bg-muted/30">
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 transform border-r bg-background transition-transform duration-200 ease-in-out lg:static lg:translate-x-0 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex h-14 items-center border-b px-6">
          <div className="flex items-center gap-2 font-semibold">
            <Activity className="h-5 w-5 text-primary" />
            <span>Hospital Events</span>
          </div>
        </div>

        <div className="flex flex-1 flex-col gap-1 p-4">
          {filteredItems.map((item) => {
            const isActive = location.pathname + location.search === item.path
            return (
              <button
                key={item.path}
                onClick={() => handleNav(item.path)}
                className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                }`}
              >
                {item.icon}
                {item.label}
              </button>
            )
          })}
        </div>

        <div className="border-t p-4">
          <div className="mb-2 px-3 text-xs text-muted-foreground">
            {user?.username} ({roleLabels[user?.role as UserRole] ?? user?.role})
          </div>
          <button
            onClick={() => {
              logout()
              navigate("/login")
            }}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
          >
            <LogOut className="h-4 w-4" />
            Sign out
          </button>
        </div>
      </aside>

      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex h-14 items-center border-b bg-background px-4 lg:px-6">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="mr-4 lg:hidden"
          >
            {sidebarOpen ? (
              <X className="h-5 w-5" />
            ) : (
              <Menu className="h-5 w-5" />
            )}
          </button>

          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Activity className="h-4 w-4" />
            <span>Hospital Event Simulation</span>
          </div>

          <div className="ml-auto flex items-center gap-3">
            <NotificationPanel />
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-2 lg:p-4">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
