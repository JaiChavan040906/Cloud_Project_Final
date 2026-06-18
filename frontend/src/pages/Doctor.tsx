import { useState, useEffect } from "react"
import { useSearchParams } from "react-router-dom"
import client from "@/api/client"
import type { Review, Patient, PatientHistory } from "@/types"
import PaginatedTable from "@/components/PaginatedTable"
import type { Column } from "@/components/PaginatedTable"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { X } from "lucide-react"

const tabs = [
  { key: "reviews", label: "Review Queue" },
  { key: "critical", label: "Critical Patients" },
  { key: "prescriptions", label: "Prescribe Medication" },
  { key: "submit-review", label: "Submit Review" },
  { key: "discharge", label: "Discharge" },
]

function Modal({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: string; children: React.ReactNode }) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <Card className="w-full max-w-2xl max-h-[80vh] overflow-y-auto">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>{title}</CardTitle>
          <button onClick={onClose} className="rounded-full p-1 hover:bg-accent">
            <X className="h-4 w-4" />
          </button>
        </CardHeader>
        <CardContent>{children}</CardContent>
      </Card>
    </div>
  )
}

export default function Doctor() {
  const [searchParams, setSearchParams] = useSearchParams()
  const activeTab = searchParams.get("tab") || "reviews"

  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    const interval = setInterval(() => setRefreshKey((k) => k + 1), 15000)
    return () => clearInterval(interval)
  }, [])

  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null)
  const [submitting, setSubmitting] = useState(false)

  // History modal
  const [historyModal, setHistoryModal] = useState<string | null>(null)
  const [patientHistory, setPatientHistory] = useState<PatientHistory | null>(null)
  const [loadingHistory, setLoadingHistory] = useState(false)

  // Review detail
  const [selectedReview, setSelectedReview] = useState<Review | null>(null)

  // Prescription form
  const [prescription, setPrescription] = useState({ medication_id: "", patient_id: "", medicine_name: "", prescribed_by: "doctor" })

  // Review form
  const [reviewForm, setReviewForm] = useState({ review_id: "", patient_id: "", doctor_id: "doctor", review_note: "", review_status: "Completed" })

  // Discharge form
  const [dischargePatientId, setDischargePatientId] = useState("")

  function showToast(message: string, type: "success" | "error") {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3000)
  }

  function setTab(tab: string) {
    if (tab === "reviews") {
      setSearchParams({})
    } else {
      setSearchParams({ tab })
    }
  }

  async function openHistory(patientId: string) {
    setHistoryModal(patientId)
    setLoadingHistory(true)
    setPatientHistory(null)
    try {
      const res = await client.get<PatientHistory>(`/api/patients/${patientId}/history`)
      setPatientHistory(res.data)
    } catch {
      showToast("Failed to load patient history", "error")
    } finally {
      setLoadingHistory(false)
    }
  }

  async function handlePrescribe(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    try {
      await client.post("/api/prescriptions", prescription)
      showToast("Prescription created", "success")
      setPrescription({ medication_id: "", patient_id: "", medicine_name: "", prescribed_by: "doctor" })
      setRefreshKey((k) => k + 1)
    } catch {
      showToast("Failed to create prescription", "error")
    } finally {
      setSubmitting(false)
    }
  }

  async function handleSubmitReview(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    try {
      await client.post("/api/reviews", reviewForm)
      showToast("Review submitted", "success")
      setReviewForm({ review_id: "", patient_id: "", doctor_id: "doctor", review_note: "", review_status: "Completed" })
      setRefreshKey((k) => k + 1)
    } catch {
      showToast("Failed to submit review", "error")
    } finally {
      setSubmitting(false)
    }
  }

  async function handleDischarge(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    try {
      await client.put(`/api/discharge/${dischargePatientId}/approve`)
      showToast("Discharge approved", "success")
      setDischargePatientId("")
      setRefreshKey((k) => k + 1)
    } catch {
      showToast("Failed to approve discharge", "error")
    } finally {
      setSubmitting(false)
    }
  }

  const reviewColumns: Column<Review>[] = [
    { key: "review_id", label: "Review ID", sortable: true },
    { key: "patient_id", label: "Patient ID", sortable: true },
    { key: "review_status", label: "Status", sortable: true },
  ]

  const criticalColumns: Column<Patient>[] = [
    { key: "patient_id", label: "Patient ID", sortable: true },
    { key: "name", label: "Name", sortable: true },
    {
      key: "actions",
      label: "Actions",
      render: (item) => (
        <Button
          size="sm"
          variant="outline"
          onClick={(e) => {
            e.stopPropagation()
            openHistory(item.patient_id)
          }}
        >
          View History
        </Button>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Doctor Dashboard</h1>
        <p className="text-muted-foreground">Patient reviews, critical care, and prescriptions</p>
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

      {activeTab === "reviews" && (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Review Queue</CardTitle>
              <CardDescription>Click a review to see details</CardDescription>
            </CardHeader>
            <CardContent>
              <PaginatedTable
                key={`reviews-${refreshKey}`}
                endpoint="/api/reviews/queue"
                columns={reviewColumns}
                searchPlaceholder="Search reviews..."
                pageSize={10}
                onRowClick={(item) => setSelectedReview(item)}
              />
            </CardContent>
          </Card>

          {selectedReview && (
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-lg">Review Detail</CardTitle>
                <Button variant="ghost" size="sm" onClick={() => setSelectedReview(null)}>
                  <X className="h-4 w-4" />
                </Button>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <span className="text-muted-foreground">Review ID:</span>
                    <p className="font-medium">{selectedReview.review_id}</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Patient ID:</span>
                    <p className="font-medium">{selectedReview.patient_id}</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Doctor ID:</span>
                    <p className="font-medium">{selectedReview.doctor_id}</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Status:</span>
                    <p className="font-medium">{selectedReview.review_status}</p>
                  </div>
                </div>
                {selectedReview.review_note && (
                  <div>
                    <span className="text-sm text-muted-foreground">Notes:</span>
                    <p className="mt-1 rounded-md bg-muted p-3 text-sm">{selectedReview.review_note}</p>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {activeTab === "critical" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Critical Patients</CardTitle>
            <CardDescription>Patients requiring immediate attention</CardDescription>
          </CardHeader>
          <CardContent>
            <PaginatedTable
              endpoint="/api/patients/critical"
              columns={criticalColumns}
              searchPlaceholder="Search patients..."
              pageSize={10}
            />
          </CardContent>
        </Card>
      )}

      {activeTab === "prescriptions" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Prescribe Medication</CardTitle>
            <CardDescription>Order new medication for a patient</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handlePrescribe} className="max-w-md space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Medication ID</label>
                <Input
                  required
                  value={prescription.medication_id}
                  onChange={(e) => setPrescription((f) => ({ ...f, medication_id: e.target.value }))}
                  placeholder="e.g. MED001"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Patient ID</label>
                <Input
                  required
                  value={prescription.patient_id}
                  onChange={(e) => setPrescription((f) => ({ ...f, patient_id: e.target.value }))}
                  placeholder="e.g. P001"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Medicine Name</label>
                <Input
                  required
                  value={prescription.medicine_name}
                  onChange={(e) => setPrescription((f) => ({ ...f, medicine_name: e.target.value }))}
                  placeholder="e.g. Metformin"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Prescribed By</label>
                <Input
                  disabled
                  value={prescription.prescribed_by}
                  className="opacity-60"
                />
              </div>
              <Button type="submit" disabled={submitting}>
                {submitting ? "Prescribing..." : "Submit Prescription"}
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      {activeTab === "submit-review" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Submit Review</CardTitle>
            <CardDescription>Submit a patient review</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmitReview} className="max-w-md space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Review ID</label>
                <Input
                  required
                  value={reviewForm.review_id}
                  onChange={(e) => setReviewForm((f) => ({ ...f, review_id: e.target.value }))}
                  placeholder="e.g. REV001"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Patient ID</label>
                <Input
                  required
                  value={reviewForm.patient_id}
                  onChange={(e) => setReviewForm((f) => ({ ...f, patient_id: e.target.value }))}
                  placeholder="e.g. P001"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Doctor ID</label>
                <Input
                  disabled
                  value={reviewForm.doctor_id}
                  className="opacity-60"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Review Notes</label>
                <textarea
                  required
                  value={reviewForm.review_note}
                  onChange={(e) => setReviewForm((f) => ({ ...f, review_note: e.target.value }))}
                  placeholder="Enter review notes..."
                  className="flex min-h-[100px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                />
              </div>
              <Button type="submit" disabled={submitting}>
                {submitting ? "Submitting..." : "Submit Review"}
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      {activeTab === "discharge" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Approve Discharge</CardTitle>
            <CardDescription>Approve a patient for discharge</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleDischarge} className="max-w-md space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Patient ID</label>
                <Input
                  required
                  value={dischargePatientId}
                  onChange={(e) => setDischargePatientId(e.target.value)}
                  placeholder="e.g. P001"
                />
              </div>
              <Button type="submit" disabled={submitting}>
                {submitting ? "Approving..." : "Approve Discharge"}
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      <Modal open={!!historyModal} onClose={() => setHistoryModal(null)} title="Patient History">
        {loadingHistory ? (
          <div className="flex items-center justify-center py-8">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          </div>
        ) : patientHistory ? (
    <div className="space-y-4">
            <div className="rounded-md bg-muted p-4">
              <h3 className="mb-2 font-medium">{patientHistory.patient.name} ({patientHistory.patient.patient_id})</h3>
              <div className="grid grid-cols-3 gap-2 text-sm text-muted-foreground">
                <span>Age: {patientHistory.patient.age}</span>
                <span>Gender: {patientHistory.patient.gender}</span>
                <span>Status: {patientHistory.patient.status}</span>
                <span>Department: {patientHistory.patient.department}</span>
                <span>Ward: {patientHistory.patient.ward}</span>
              </div>
            </div>

            {patientHistory.events.length > 0 && (
              <div>
                <h4 className="mb-2 text-sm font-medium">Events</h4>
                <div className="space-y-2">
                  {patientHistory.events.map((ev) => (
                    <div key={ev.event_id} className="rounded-md border p-3 text-sm">
                      <div className="font-medium">{ev.event_type}</div>
                      <div className="text-muted-foreground">{ev.description}</div>
                      <div className="text-xs text-muted-foreground">{ev.timestamp}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {patientHistory.reviews.length > 0 && (
              <div>
                <h4 className="mb-2 text-sm font-medium">Reviews</h4>
                <div className="space-y-2">
                  {patientHistory.reviews.map((rev) => (
                    <div key={rev.review_id} className="rounded-md border p-3 text-sm">
                      <div className="font-medium">{rev.review_status} — {rev.doctor_id}</div>
                      {rev.review_note && <div className="text-muted-foreground">{rev.review_note}</div>}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {patientHistory.medications.length > 0 && (
              <div>
                <h4 className="mb-2 text-sm font-medium">Medications</h4>
                <div className="space-y-2">
                  {patientHistory.medications.map((med) => (
                    <div key={med.medication_id} className="rounded-md border p-3 text-sm">
                      <div className="font-medium">{med.medicine_name}</div>
                      <div className="text-muted-foreground">Prescribed by {med.prescribed_by} — {med.status}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="py-8 text-center text-muted-foreground">Failed to load history</div>
        )}
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
