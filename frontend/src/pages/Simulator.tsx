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
import { Activity, ChevronRight, RotateCcw, LogIn } from "lucide-react"

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
    <div className="flex min-h-screen flex-col items-center justify-center bg-muted/30 p-8">
      <Card className="w-full max-w-2xl">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-primary" />
            <CardTitle>Event Simulator</CardTitle>
          </div>
          <CardDescription>
            Step through predefined hospital events to populate the system
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-8">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Progress</span>
              <span className="text-lg font-medium">
                {state?.current_step ?? 0} / {state?.total_events ?? 0}
              </span>
            </div>
            <div className="h-4 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>

          <div className="flex gap-4">
            <Button
              onClick={handleNext}
              disabled={loading || isComplete}
              className="flex-1 h-12 text-base"
            >
              <ChevronRight className="h-5 w-5" />
              {isComplete ? "Complete" : loading ? "Processing..." : "Next Event"}
            </Button>
            <Button
              onClick={handleReset}
              variant="outline"
              disabled={loading}
              className="h-12"
            >
              <RotateCcw className="h-5 w-5" />
              Reset
            </Button>
          </div>

          {error && (
            <div className="rounded-md bg-destructive/15 p-4 text-sm text-destructive">
              {error}
            </div>
          )}

          {lastEvent && (
            <div className="rounded-lg border p-6">
              <h4 className="mb-4 text-base font-medium">Last Event</h4>
              <dl className="space-y-3">
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
                  <dd className="text-right font-medium">{lastEvent.step.description}</dd>
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

          <div className="text-center">
            <Link
              to="/login"
              className="inline-flex items-center gap-2 text-base hover:text-foreground"
            >
              <LogIn className="h-4 w-4" />
              Go to login
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
