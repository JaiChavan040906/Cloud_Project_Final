import { useState, useEffect } from "react"
import { useSearchParams } from "react-router-dom"
import client from "@/api/client"
import type { Patient, Appointment } from "@/types"
import PaginatedTable from "@/components/PaginatedTable"
import type { Column } from "@/components/PaginatedTable"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { UserPlus, CalendarPlus, LogIn, FileText, X } from "lucide-react"

const tabs = [
  { key: "patients", label: "Patients" },
  { key: "appointments", label: "Appointments" },
  { key: "admissions", label: "Admissions" },
]

const quickActions = [
  { key: "register", label: "Register Patient", icon: <UserPlus className="h-5 w-5" />, description: "Add a new patient to the system" },
  { key: "appointment", label: "Create Appointment", icon: <CalendarPlus className="h-5 w-5" />, description: "Schedule a new appointment" },
  { key: "checkin", label: "Check In", icon: <LogIn className="h-5 w-5" />, description: "Check in an arriving patient" },
  { key: "admissions", label: "Admission Requests", icon: <FileText className="h-5 w-5" />, description: "View pending admission requests" },
]

function Modal({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: string; children: React.ReactNode }) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <Card className="w-full max-w-lg">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>{title}</CardTitle>
          </div>
          <button onClick={onClose} className="rounded-full p-1 hover:bg-accent">
            <X className="h-4 w-4" />
          </button>
        </CardHeader>
        <CardContent>{children}</CardContent>
      </Card>
    </div>
  )
}

export default function Receptionist() {
  const [searchParams, setSearchParams] = useSearchParams()
  const activeTab = searchParams.get("tab") || "patients"

  const [modal, setModal] = useState<string | null>(null)
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    const interval = setInterval(() => setRefreshKey((k) => k + 1), 15000)
    return () => clearInterval(interval)
  }, [])

  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const [registerForm, setRegisterForm] = useState({ patient_id: "", name: "", age: "", gender: "Male", department: "", ward: "", assigned_doctor: "", assigned_nurse: "" })
  const [appointmentForm, setAppointmentForm] = useState({ appointment_id: "", patient_id: "", date: "", time: "" })
  const [checkinForm, setCheckinForm] = useState({ patient_id: "", department: "", ward: "" })

  function showToast(message: string, type: "success" | "error") {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3000)
  }

  function setTab(tab: string) {
    if (tab === "patients") {
      setSearchParams({})
    } else {
      setSearchParams({ tab })
    }
  }

  function openModal(key: string) {
    if (key === "admissions") {
      setTab("admissions")
      return
    }
    setModal(key)
  }

  function closeModal() {
    setModal(null)
    setSubmitting(false)
  }

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    try {
      await client.post("/api/patients/register", {
        ...registerForm,
        age: parseInt(registerForm.age, 10),
      })
      showToast("Patient registered successfully", "success")
      closeModal()
      setRegisterForm({ patient_id: "", name: "", age: "", gender: "Male", department: "", ward: "", assigned_doctor: "", assigned_nurse: "" })
      setRefreshKey((k) => k + 1)
    } catch {
      showToast("Failed to register patient", "error")
    } finally {
      setSubmitting(false)
    }
  }

  async function handleCreateAppointment(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    try {
      await client.post("/api/appointments", appointmentForm)
      showToast("Appointment created successfully", "success")
      closeModal()
      setAppointmentForm({ appointment_id: "", patient_id: "", date: "", time: "" })
      setRefreshKey((k) => k + 1)
    } catch {
      showToast("Failed to create appointment", "error")
    } finally {
      setSubmitting(false)
    }
  }

  async function handleCheckIn(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    try {
      await client.post(`/api/patients/${checkinForm.patient_id}/checkin`, {
        department: checkinForm.department,
        ward: checkinForm.ward,
      })
      showToast("Patient checked in successfully", "success")
      closeModal()
      setCheckinForm({ patient_id: "", department: "", ward: "" })
      setRefreshKey((k) => k + 1)
    } catch {
      showToast("Failed to check in patient", "error")
    } finally {
      setSubmitting(false)
    }
  }

  const patientColumns: Column<Patient>[] = [
    { key: "patient_id", label: "ID", sortable: true },
    { key: "name", label: "Name", sortable: true },
    { key: "age", label: "Age" },
    { key: "gender", label: "Gender" },
    { key: "department", label: "Department", sortable: true },
    { key: "ward", label: "Ward" },
    { key: "status", label: "Status", sortable: true },
  ]

  const appointmentColumns: Column<Appointment>[] = [
    { key: "appointment_id", label: "Appointment ID", sortable: true },
    { key: "patient_id", label: "Patient ID", sortable: true },
    { key: "date", label: "Date", sortable: true },
    { key: "time", label: "Time", sortable: true },
    { key: "status", label: "Status", sortable: true },
  ]

  const admissionColumns: Column<Patient>[] = [
    { key: "patient_id", label: "ID", sortable: true },
    { key: "name", label: "Name", sortable: true },
    { key: "age", label: "Age" },
    { key: "gender", label: "Gender" },
    { key: "department", label: "Department", sortable: true },
    { key: "ward", label: "Ward" },
    { key: "status", label: "Status", sortable: true },
  ]

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Receptionist Dashboard</h1>
        <p className="text-muted-foreground">Patient registration, appointments, and admissions</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {quickActions.map((action) => (
          <button
            key={action.key}
            onClick={() => openModal(action.key)}
            className="flex flex-col items-start gap-3 rounded-lg border bg-card p-6 text-left transition-colors hover:bg-accent"
          >
            <div className="rounded-md bg-primary/10 p-3 text-primary">
              {action.icon}
            </div>
            <div className="text-base font-medium">{action.label}</div>
            <div className="text-sm text-muted-foreground">{action.description}</div>
          </button>
        ))}
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

      {activeTab === "patients" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Patients</CardTitle>
            <CardDescription>All registered patients</CardDescription>
          </CardHeader>
          <CardContent>
            <PaginatedTable
              key={`patients-${refreshKey}`}
              endpoint="/api/patients"
              columns={patientColumns}
              searchPlaceholder="Search by name or ID..."
              pageSize={10}
            />
          </CardContent>
        </Card>
      )}

      {activeTab === "appointments" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Appointments</CardTitle>
            <CardDescription>All scheduled appointments</CardDescription>
          </CardHeader>
          <CardContent>
            <PaginatedTable
              key={`appointments-${refreshKey}`}
              endpoint="/api/appointments"
              columns={appointmentColumns}
              searchPlaceholder="Search appointments..."
              pageSize={10}
            />
          </CardContent>
        </Card>
      )}

      {activeTab === "admissions" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Admission Requests</CardTitle>
            <CardDescription>Pending admission requests</CardDescription>
          </CardHeader>
          <CardContent>
            <PaginatedTable
              key={`admissions-${refreshKey}`}
              endpoint="/api/admissions"
              columns={admissionColumns}
              searchPlaceholder="Search patients..."
              pageSize={10}
              statusFilter
              statusOptions={[{ label: "Admission Requested", value: "Admission Requested" }]}
              extraParams={{ status: "Admission Requested" }}
            />
          </CardContent>
        </Card>
      )}

      <Modal open={modal === "register"} onClose={closeModal} title="Register Patient">
        <form onSubmit={handleRegister} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Patient ID</label>
              <Input required value={registerForm.patient_id} onChange={(e) => setRegisterForm((f) => ({ ...f, patient_id: e.target.value }))} placeholder="e.g. P001" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Name</label>
              <Input required value={registerForm.name} onChange={(e) => setRegisterForm((f) => ({ ...f, name: e.target.value }))} placeholder="Patient name" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Age</label>
              <Input required type="number" min={0} value={registerForm.age} onChange={(e) => setRegisterForm((f) => ({ ...f, age: e.target.value }))} placeholder="Age" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Gender</label>
              <select
                value={registerForm.gender}
                onChange={(e) => setRegisterForm((f) => ({ ...f, gender: e.target.value }))}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              >
                <option value="Male">Male</option>
                <option value="Female">Female</option>
                <option value="Other">Other</option>
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Department</label>
              <Input required value={registerForm.department} onChange={(e) => setRegisterForm((f) => ({ ...f, department: e.target.value }))} placeholder="e.g. Cardiology" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Ward</label>
              <Input required value={registerForm.ward} onChange={(e) => setRegisterForm((f) => ({ ...f, ward: e.target.value }))} placeholder="e.g. A1" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Assigned Doctor</label>
              <Input value={registerForm.assigned_doctor} onChange={(e) => setRegisterForm((f) => ({ ...f, assigned_doctor: e.target.value }))} placeholder="Doctor username" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Assigned Nurse</label>
              <Input value={registerForm.assigned_nurse} onChange={(e) => setRegisterForm((f) => ({ ...f, assigned_nurse: e.target.value }))} placeholder="Nurse username" />
            </div>
          </div>
          <div className="flex justify-end gap-3">
            <Button type="button" variant="outline" onClick={closeModal}>Cancel</Button>
            <Button type="submit" disabled={submitting}>{submitting ? "Registering..." : "Register Patient"}</Button>
          </div>
        </form>
      </Modal>

      <Modal open={modal === "appointment"} onClose={closeModal} title="Create Appointment">
        <form onSubmit={handleCreateAppointment} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Appointment ID</label>
              <Input required value={appointmentForm.appointment_id} onChange={(e) => setAppointmentForm((f) => ({ ...f, appointment_id: e.target.value }))} placeholder="e.g. APT001" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Patient ID</label>
              <Input required value={appointmentForm.patient_id} onChange={(e) => setAppointmentForm((f) => ({ ...f, patient_id: e.target.value }))} placeholder="e.g. P001" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Date</label>
              <Input required type="date" value={appointmentForm.date} onChange={(e) => setAppointmentForm((f) => ({ ...f, date: e.target.value }))} />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Time</label>
              <Input required type="time" value={appointmentForm.time} onChange={(e) => setAppointmentForm((f) => ({ ...f, time: e.target.value }))} />
            </div>
          </div>
          <div className="flex justify-end gap-3">
            <Button type="button" variant="outline" onClick={closeModal}>Cancel</Button>
            <Button type="submit" disabled={submitting}>{submitting ? "Creating..." : "Create Appointment"}</Button>
          </div>
        </form>
      </Modal>

      <Modal open={modal === "checkin"} onClose={closeModal} title="Check In Patient">
        <form onSubmit={handleCheckIn} className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Patient ID</label>
            <Input required value={checkinForm.patient_id} onChange={(e) => setCheckinForm((f) => ({ ...f, patient_id: e.target.value }))} placeholder="e.g. P001" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Department</label>
              <Input required value={checkinForm.department} onChange={(e) => setCheckinForm((f) => ({ ...f, department: e.target.value }))} placeholder="e.g. Cardiology" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Ward</label>
              <Input required value={checkinForm.ward} onChange={(e) => setCheckinForm((f) => ({ ...f, ward: e.target.value }))} placeholder="e.g. A2" />
            </div>
          </div>
          <div className="flex justify-end gap-3">
            <Button type="button" variant="outline" onClick={closeModal}>Cancel</Button>
            <Button type="submit" disabled={submitting}>{submitting ? "Checking in..." : "Check In"}</Button>
          </div>
        </form>
      </Modal>

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
