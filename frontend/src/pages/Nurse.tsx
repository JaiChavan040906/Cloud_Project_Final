import { useState, useEffect } from "react"
import { useSearchParams } from "react-router-dom"
import client from "@/api/client"
import type { Patient, Alert, Medication, VitalsRecord, VitalsResponse } from "@/types"
import PaginatedTable from "@/components/PaginatedTable"
import type { Column } from "@/components/PaginatedTable"
import SeverityBadge from "@/components/SeverityBadge"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

const tabs = [
  { key: "assigned", label: "Assigned Patients" },
  { key: "vitals", label: "Record Vitals" },
  { key: "alerts", label: "Alerts" },
  { key: "medications", label: "Medications Queue" },
]

function validateVitals(v: VitalsRecord): string | null {
  if (v.heart_rate < 0 || v.heart_rate > 300) return "Heart rate must be 0-300"
  if (v.oxygen_level < 0 || v.oxygen_level > 100) return "Oxygen level must be 0-100"
  if (v.temperature < 90 || v.temperature > 110) return "Temperature must be 90-110°F"
  if (v.blood_sugar < 0 || v.blood_sugar > 1000) return "Blood sugar must be 0-1000"
  if (v.blood_pressure_systolic < 0 || v.blood_pressure_systolic > 300) return "Systolic BP must be 0-300"
  if (v.blood_pressure_diastolic < 0 || v.blood_pressure_diastolic > 200) return "Diastolic BP must be 0-200"
  return null
}

export default function Nurse() {
  const [searchParams, setSearchParams] = useSearchParams()
  const activeTab = searchParams.get("tab") || "assigned"

  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    const interval = setInterval(() => setRefreshKey((k) => k + 1), 15000)
    return () => clearInterval(interval)
  }, [])

  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null)
  const [submitting, setSubmitting] = useState(false)

  // Vitals form
  const [vitals, setVitals] = useState<VitalsRecord>({
    patient_id: "",
    heart_rate: 0,
    blood_pressure_systolic: 0,
    blood_pressure_diastolic: 0,
    oxygen_level: 0,
    temperature: 0,
    blood_sugar: 0,
  })
  const [vitalsResult, setVitalsResult] = useState<VitalsResponse | null>(null)
  const [vitalsError, setVitalsError] = useState<string | null>(null)

  function showToast(message: string, type: "success" | "error") {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3000)
  }

  function setTab(tab: string) {
    if (tab === "assigned") {
      setSearchParams({})
    } else {
      setSearchParams({ tab })
    }
  }

  async function handleRecordVitals(e: React.FormEvent) {
    e.preventDefault()
    setVitalsResult(null)
    setVitalsError(null)
    const validationError = validateVitals(vitals)
    if (validationError) {
      setVitalsError(validationError)
      return
    }
    setSubmitting(true)
    try {
      const res = await client.post<VitalsResponse>("/api/vitals", vitals)
      setVitalsResult(res.data)
      showToast("Vitals recorded successfully", "success")
      setRefreshKey((k) => k + 1)
    } catch {
      showToast("Failed to record vitals", "error")
    } finally {
      setSubmitting(false)
    }
  }

  async function handleAdminister(medicationId: string) {
    try {
      await client.put(`/api/medications/${medicationId}/administer`)
      showToast("Medication administered", "success")
      setRefreshKey((k) => k + 1)
    } catch {
      showToast("Failed to administer medication", "error")
    }
  }

  async function handleCompleteCheckup(patientId: string) {
    try {
      await client.put(`/api/checkups/${patientId}/complete`)
      showToast("Checkup completed", "success")
      setRefreshKey((k) => k + 1)
    } catch {
      showToast("Failed to complete checkup", "error")
    }
  }

  const assignedColumns: Column<Patient>[] = [
    { key: "patient_id", label: "ID", sortable: true },
    { key: "name", label: "Name", sortable: true },
    { key: "status", label: "Status", sortable: true },
    { key: "ward", label: "Ward" },
    {
      key: "actions",
      label: "Actions",
      render: (item) => (
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            className="hover:bg-green-900/60 hover:text-green-300"
            onClick={(e) => {
              e.stopPropagation()
              setVitals((prev) => ({ ...prev, patient_id: item.patient_id }))
              setTab("vitals")
            }}
          >
            Record Vitals
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="hover:bg-yellow-900/60 hover:text-yellow-300"
            onClick={(e) => {
              e.stopPropagation()
              handleCompleteCheckup(item.patient_id)
            }}
          >
            Checkup
          </Button>
        </div>
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
  ]

  const medicationColumns: Column<Medication>[] = [
    { key: "medication_id", label: "Medication ID", sortable: true },
    { key: "medicine_name", label: "Medicine", sortable: true },
    { key: "patient_id", label: "Patient ID", sortable: true },
    { key: "prescribed_by", label: "Prescribed By" },
    { key: "status", label: "Status", sortable: true },
    {
      key: "actions",
      label: "Actions",
      render: (item) =>
        item.status === "Prescribed" ? (
          <Button
            size="sm"
            onClick={(e) => {
              e.stopPropagation()
              handleAdminister(item.medication_id)
            }}
          >
            Administer
          </Button>
        ) : (
          <span className="text-sm text-muted-foreground">Done</span>
        ),
    },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Nurse Dashboard</h1>
        <p className="text-muted-foreground">Patient care, vitals, and medication management</p>
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

      {activeTab === "assigned" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Assigned Patients</CardTitle>
            <CardDescription>Patients assigned to your care</CardDescription>
          </CardHeader>
          <CardContent>
            <PaginatedTable
              key={`assigned-${refreshKey}`}
              endpoint="/api/patients/assigned"
              columns={assignedColumns}
              searchPlaceholder="Search patients..."
              pageSize={10}
            />
          </CardContent>
        </Card>
      )}

      {activeTab === "vitals" && (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Record Vitals</CardTitle>
              <CardDescription>Enter patient vitals to assess risk</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleRecordVitals} className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Patient ID</label>
                  <Input
                    required
                    value={vitals.patient_id}
                    onChange={(e) => setVitals((f) => ({ ...f, patient_id: e.target.value }))}
                    placeholder="e.g. P001"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Heart Rate (0-300)</label>
                    <Input
                      required
                      type="number"
                      value={vitals.heart_rate || ""}
                      onChange={(e) => setVitals((f) => ({ ...f, heart_rate: parseFloat(e.target.value) || 0 }))}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">SpO2 (0-100)</label>
                    <Input
                      required
                      type="number"
                      step="0.1"
                      value={vitals.oxygen_level || ""}
                      onChange={(e) => setVitals((f) => ({ ...f, oxygen_level: parseFloat(e.target.value) || 0 }))}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">BP Systolic (0-300)</label>
                    <Input
                      required
                      type="number"
                      value={vitals.blood_pressure_systolic || ""}
                      onChange={(e) => setVitals((f) => ({ ...f, blood_pressure_systolic: parseFloat(e.target.value) || 0 }))}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">BP Diastolic (0-200)</label>
                    <Input
                      required
                      type="number"
                      value={vitals.blood_pressure_diastolic || ""}
                      onChange={(e) => setVitals((f) => ({ ...f, blood_pressure_diastolic: parseFloat(e.target.value) || 0 }))}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Temperature (90-110°F)</label>
                    <Input
                      required
                      type="number"
                      step="0.1"
                      value={vitals.temperature || ""}
                      onChange={(e) => setVitals((f) => ({ ...f, temperature: parseFloat(e.target.value) || 0 }))}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Blood Sugar (0-1000)</label>
                    <Input
                      required
                      type="number"
                      step="0.1"
                      value={vitals.blood_sugar || ""}
                      onChange={(e) => setVitals((f) => ({ ...f, blood_sugar: parseFloat(e.target.value) || 0 }))}
                    />
                  </div>
                </div>
                {vitalsError && (
                  <div className="rounded-md bg-red-900/50 px-3 py-2 text-sm text-red-200">
                    {vitalsError}
                  </div>
                )}
                <Button type="submit" disabled={submitting}>
                  {submitting ? "Recording..." : "Submit Vitals"}
                </Button>
              </form>
            </CardContent>
          </Card>

          {vitalsResult && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Result</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center gap-3">
                  <span className="text-sm text-muted-foreground">Severity:</span>
                  <SeverityBadge severity={vitalsResult.severity} />
                </div>
                {vitalsResult.reasons.length > 0 && (
                  <div className="space-y-2">
                    <span className="text-sm text-muted-foreground">Reasons:</span>
                    <ul className="list-inside list-disc space-y-1 text-sm">
                      {vitalsResult.reasons.map((r, i) => (
                        <li key={i} className="text-muted-foreground">{r}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {activeTab === "alerts" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Active Alerts</CardTitle>
            <CardDescription>All active patient alerts</CardDescription>
          </CardHeader>
          <CardContent>
            <PaginatedTable
              endpoint="/api/alerts"
              columns={alertColumns}
              searchPlaceholder="Search alerts..."
              pageSize={10}
            />
          </CardContent>
        </Card>
      )}

      {activeTab === "medications" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Medications Queue</CardTitle>
            <CardDescription>Prescribed medications awaiting administration</CardDescription>
          </CardHeader>
          <CardContent>
            <PaginatedTable
              key={`medications-${refreshKey}`}
              endpoint="/api/medications/queue"
              columns={medicationColumns}
              searchPlaceholder="Search medications..."
              pageSize={10}
            />
          </CardContent>
        </Card>
      )}

      {toast && (
        <div className={`fixed bottom-4 right-4 z-50 rounded-md px-4 py-3 shadow-lg ${
          toast.type === "success" ? "bg-green-900 text-green-100" : "bg-red-900 text-red-100"
        }`}>
          {toast.message}
        </div>
      )}
    </div>
  )
}
