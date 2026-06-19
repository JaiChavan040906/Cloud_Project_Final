import { useState, useEffect, useRef } from "react"
import client from "@/api/client"
import { useAuth } from "@/context/AuthContext"
import type { Notification } from "@/types"
import { Bell } from "lucide-react"

interface NotificationPanelProps {
  dashboardRole?: string
}

export default function NotificationPanel({ dashboardRole }: NotificationPanelProps) {
  const { user } = useAuth()
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  const unreadCount = notifications.filter((n) => n.status === "Unread").length

  const params = dashboardRole ? { role: dashboardRole } : undefined

  useEffect(() => {
    if (!user) return
    async function fetch() {
      try {
        const res = await client.get<Notification[]>("/api/notifications", { params })
        setNotifications(res.data)
      } catch {
        // ignore
      }
    }
    fetch()
    const interval = setInterval(fetch, 10000)
    return () => clearInterval(interval)
  }, [user, dashboardRole])

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener("mousedown", handleClick)
    return () => document.removeEventListener("mousedown", handleClick)
  }, [])

  async function handleMarkRead(id: string) {
    await client.put(`/api/notifications/${id}/read`, undefined, { params })
    setNotifications((prev) => prev.filter((n) => n.notification_id !== id))
  }

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="relative rounded-full p-2 hover:bg-accent"
      >
        <Bell className="h-5 w-5 text-muted-foreground" />
        {unreadCount > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-destructive text-[10px] font-medium text-destructive-foreground">
            {unreadCount}
          </span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 z-50 mt-2 w-80 rounded-md border bg-card shadow-lg">
          <div className="border-b px-4 py-2 text-sm font-medium">Notifications</div>
          <div className="max-h-64 overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="px-4 py-6 text-center text-sm text-muted-foreground">
                No new notifications
              </div>
            ) : (
              notifications.map((n) => (
                <button
                  key={n.notification_id}
                  onClick={() => handleMarkRead(n.notification_id)}
                  className="flex w-full items-start gap-2 border-b px-4 py-3 text-left text-sm hover:bg-accent"
                >
                  <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-primary" />
                  <span className="text-muted-foreground">{n.message}</span>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}
