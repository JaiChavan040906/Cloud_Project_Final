import { cn } from "@/lib/utils"

interface SeverityBadgeProps {
  severity: string
}

const severityStyles: Record<string, string> = {
  normal: "bg-green-100 text-green-800",
  warning: "bg-yellow-100 text-yellow-800",
  critical: "bg-red-100 text-red-800",
}

export default function SeverityBadge({ severity }: SeverityBadgeProps) {
  const key = severity.toLowerCase()
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        severityStyles[key] ?? "bg-gray-100 text-gray-800",
      )}
    >
      {severity}
    </span>
  )
}
