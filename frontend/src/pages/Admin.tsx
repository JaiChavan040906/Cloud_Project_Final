import { useEffect, useState, useCallback } from "react"
import { useSearchParams } from "react-router-dom"
import client from "@/api/client"
import type { AdminSummary, Alert, Patient } from "@/types"
import StatsCard from "@/components/StatsCard"
import SeverityBadge from "@/components/SeverityBadge"
import PaginatedTable from "@/components/PaginatedTable"
import type { Column } from "@/components/PaginatedTable"
import { Users, UserCheck, AlertTriangle, ClipboardList, Bell, Bed } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"

const tabs = [
  { key: "overview", label: "Overview" },
  { key: "admissions", label: "Admissions" },
  { key: "alerts", label: "Alerts" },
]

const statCards = [
  { key: "total_patients", title: "Total Patients", icon: <Users className="h-4 w-4" /> },
  { key: "admissions_pending", title: "Admissions Pending", icon: <UserCheck className="h-4 w-4" /> },
  { key: "admitted", title: "Admitted", icon: <Bed className="h-4 w-4" /> },
  { key: "critical_patients", title: "Critical Patients", icon: <AlertTriangle className="h-4 w-4 text-red-500" /> },
  { key: "pending_reviews", title: "Pending Reviews", icon: <ClipboardList className="h-4 w-4" /> },
  { key: "active_alerts", title: "Active Alerts", icon: <Bell className="h-4 w-4" /> },
]

export default function Admin() {
  const [searchParams, setSearchParams] = useSearchParams()
  const activeTab = searchParams.get("tab") || "overview"
  const [summary, setSummary] = useState<AdminSummary | null>(null)
  const [approving, setApproving] = useState<string | null>(null)
  const [refreshKey, setRefreshKey] = useState(0)
  const fetchSummary = useCallback(async () => {
    try {
      const res = await client.get<AdminSummary>("/api/admin/summary")
      setSummary(res.data)
    } catch {
      // silently fail on poll
    }
  }, [])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchSummary()
    const interval = setInterval(fetchSummary, 30000)
    return () => clearInterval(interval)
  }, [fetchSummary])

  async function handleApprove(patientId: string) {
    setApproving(patientId)
    try {
      await client.put(`/api/admissions/${patientId}/approve`)
      setRefreshKey((k) => k + 1)
      fetchSummary()
    } finally {
      setApproving(null)
    }
  }

  const admissionsColumns: Column<Patient>[] = [
    { key: "patient_id", label: "ID", sortable: true },
    { key: "name", label: "Name", sortable: true },
    { key: "age", label: "Age" },
    { key: "gender", label: "Gender" },
    { key: "department", label: "Department", sortable: true },
    { key: "ward", label: "Ward" },
    {
      key: "status",
      label: "Status",
      sortable: true,
      render: (item) => (
        <span className="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800">
          {item.status}
        </span>
      ),
    },
    {
      key: "actions",
      label: "Actions",
      render: (item) => (
        <Button
          size="sm"
          onClick={(e) => {
            e.stopPropagation()
            handleApprove(item.patient_id)
          }}
          disabled={approving === item.patient_id}
        >
          {approving === item.patient_id ? "Approving..." : "Approve"}
        </Button>
      ),
    },
  ]

  const alertColumns: Column<Alert>[] = [
    { key: "alert_id", label: "Alert ID", sortable: true },
    { key: "patient_id", label: "Patient ID", sortable: true },
    {
      key: "severity",
      label: "Severity",
      sortable: true,
      render: (item) => <SeverityBadge severity={item.severity} />,
    },
    { key: "message", label: "Message" },
    { key: "created_at", label: "Created At", sortable: true },
    { key: "status", label: "Status", sortable: true },
  ]

  function setTab(tab: string) {
    if (tab === "overview") {
      setSearchParams({})
    } else {
      setSearchParams({ tab })
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Admin Dashboard</h1>
        <p className="text-muted-foreground">
          Hospital overview and management
        </p>
      </div>

      <div className="border-b">
        <div className="flex gap-4">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setTab(tab.key)}
              className={`border-b-2 px-1 pb-3 text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {activeTab === "overview" && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            {statCards.map((stat) => (
              <StatsCard
                key={stat.key}
                title={stat.title}
                value={summary?.[stat.key as keyof AdminSummary] ?? 0}
                icon={stat.icon}
              />
            ))}
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Pending Admissions</CardTitle>
            </CardHeader>
            <CardContent>
              <PaginatedTable
                key={`admissions-${refreshKey}`}
                endpoint="/api/admin/admissions"
                columns={admissionsColumns}
                searchPlaceholder="Search patients..."
                pageSize={5}
                statusFilter
                statusOptions={[{ label: "Admission Requested", value: "Admission Requested" }]}
                extraParams={{ status: "Admission Requested" }}
              />
            </CardContent>
          </Card>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Critical Alerts</CardTitle>
              </CardHeader>
              <CardContent>
                <PaginatedTable
                  endpoint="/api/admin/critical"
                  columns={alertColumns}
                  searchPlaceholder="Search alerts..."
                  pageSize={5}
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-lg">All Active Alerts</CardTitle>
              </CardHeader>
              <CardContent>
                <PaginatedTable
                  endpoint="/api/admin/alerts"
                  columns={alertColumns}
                  searchPlaceholder="Search alerts..."
                  pageSize={5}
                />
              </CardContent>
            </Card>
          </div>
        </>
      )}

      {activeTab === "admissions" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Pending Admissions</CardTitle>
          </CardHeader>
          <CardContent>
            <PaginatedTable
              key={`admissions-full-${refreshKey}`}
              endpoint="/api/admin/admissions"
              columns={admissionsColumns}
              searchPlaceholder="Search patients..."
              statusFilter
              statusOptions={[{ label: "Admission Requested", value: "Admission Requested" }]}
              extraParams={{ status: "Admission Requested" }}
            />
          </CardContent>
        </Card>
      )}

      {activeTab === "alerts" && (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Critical Alerts</CardTitle>
            </CardHeader>
            <CardContent>
              <PaginatedTable
                endpoint="/api/admin/critical"
                columns={alertColumns}
                searchPlaceholder="Search alerts..."
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">All Active Alerts</CardTitle>
            </CardHeader>
            <CardContent>
              <PaginatedTable
                endpoint="/api/admin/alerts"
                columns={alertColumns}
                searchPlaceholder="Search alerts..."
              />
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
