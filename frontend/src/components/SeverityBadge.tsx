import { cn } from "@/lib/utils"

interface SeverityBadgeProps {
  severity: string
}

const severityStyles: Record<string, string> = {
  normal: "bg-green-900/60 text-green-300",
  warning: "bg-yellow-900/60 text-yellow-300",
  critical: "bg-red-900/60 text-red-300",
}

export default function SeverityBadge({ severity }: SeverityBadgeProps) {
  const key = severity.toLowerCase()
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        severityStyles[key] ?? "bg-gray-800 text-gray-300",
      )}
    >
      {severity}
    </span>
  )
}
