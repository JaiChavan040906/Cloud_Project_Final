import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import client from "@/api/client"
import type { SimulatorState, SimulatorNext } from "@/types"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Activity, ChevronLeft, ChevronRight, RotateCcw, LogIn } from "lucide-react"

export default function Simulator() {
  const [state, setState] = useState<SimulatorState | null>(null)
  const [lastEvent, setLastEvent] = useState<SimulatorNext | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  useEffect(() => {
    client.get<SimulatorState>("/api/simulator/state").then((res) => {
      setState(res.data)
    })
  }, [])

    async function handleNext() {
    setLoading(true)
    setError("")
    try {
      const res = await client.post<SimulatorNext>("/api/simulator/next")
      setLastEvent(res.data)
      const stateRes = await client.get<SimulatorState>("/api/simulator/state")
      setState(stateRes.data)
    } catch (err: unknown) {
      let msg = "Failed to process event"
      if (err && typeof err === "object" && "response" in err) {
        const axiosErr = err as { response?: { status?: number; data?: unknown } }
        const data = axiosErr.response?.data
        if (typeof data === "object" && data && "detail" in data) {
          msg = String((data as Record<string, unknown>).detail)
        } else if (typeof data === "string") {
          msg = data
        }
      }
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  async function handlePrevious() {
    setLoading(true)
    setError("")
    try {
      const res = await client.post<SimulatorNext>("/api/simulator/previous")
      setLastEvent(res.data)
      const stateRes = await client.get<SimulatorState>("/api/simulator/state")
      setState(stateRes.data)
    } catch (err: unknown) {
      let msg = "Failed to undo event"
      if (err && typeof err === "object" && "response" in err) {
        const axiosErr = err as { response?: { status?: number; data?: unknown } }
        const data = axiosErr.response?.data
        if (typeof data === "object" && data && "detail" in data) {
          msg = String((data as Record<string, unknown>).detail)
        } else if (typeof data === "string") {
          msg = data
        }
      }
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  async function handleReset() {
    setLoading(true)
    setError("")
    try {
      await client.post("/api/simulator/reset")
      setLastEvent(null)
      const stateRes = await client.get<SimulatorState>("/api/simulator/state")
      setState(stateRes.data)
    } catch {
      setError("Failed to reset simulator")
    } finally {
      setLoading(false)
    }
  }

  const progress = state
    ? Math.round((state.current_step / state.total_events) * 100)
    : 0
  const isComplete = state ? state.current_step >= state.total_events : false

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-muted/30 p-4">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-primary" />
            <CardTitle>Event Simulator</CardTitle>
          </div>
          <CardDescription>
            Step through predefined hospital events to populate the system
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-6">
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Progress</span>
              <span className="font-medium">
                {state?.current_step ?? 0} / {state?.total_events ?? 0}
              </span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>

          <div className="flex gap-3">
            <Button
              onClick={handlePrevious}
              disabled={loading || !state || state.current_step <= 0}
              variant="outline"
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </Button>
            <Button
              onClick={handleNext}
              disabled={loading || isComplete}
              className="flex-1"
            >
              <ChevronRight className="h-4 w-4" />
              {isComplete ? "Complete" : loading ? "Processing..." : "Next Event"}
            </Button>
            <Button
              onClick={handleReset}
              variant="outline"
              disabled={loading}
            >
              <RotateCcw className="h-4 w-4" />
              Reset
            </Button>
          </div>

          {error && (
            <div className="rounded-md bg-destructive/15 p-3 text-sm text-destructive">
              {error}
            </div>
          )}

          {lastEvent && (
            <div className="rounded-lg border p-4">
              <h4 className="mb-3 text-sm font-medium">Last Event</h4>
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Type</dt>
                  <dd className="font-medium">{lastEvent.step.event_type}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Patient</dt>
                  <dd className="font-medium">{lastEvent.step.patient_id}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Description</dt>
                  <dd className="text-right">{lastEvent.step.description}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Recipients</dt>
                  <dd className="font-medium">
                    {lastEvent.recipients.join(", ")}
                  </dd>
                </div>
              </dl>
            </div>
          )}

          <div className="text-center text-sm text-muted-foreground">
            <Link
              to="/login"
              className="inline-flex items-center gap-1 hover:text-foreground"
            >
              <LogIn className="h-3 w-3" />
              Go to login
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
