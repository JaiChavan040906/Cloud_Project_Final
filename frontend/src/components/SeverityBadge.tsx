import { Badge } from "@/components/ui/badge"

const severityConfig: Record<string, { variant: "default" | "secondary" | "destructive"; className: string }> = {
  normal: {
    variant: "default",
    className: "bg-green-100 text-green-800 hover:bg-green-100",
  },
  warning: {
    variant: "secondary",
    className: "bg-yellow-100 text-yellow-800 hover:bg-yellow-100",
  },
  critical: {
    variant: "destructive",
    className: "bg-red-100 text-red-800 hover:bg-red-100",
  },
}

interface SeverityBadgeProps {
  severity: string
}

export default function SeverityBadge({ severity }: SeverityBadgeProps) {
  const config = severityConfig[severity.toLowerCase()]
  if (!config) {
    return <Badge variant="outline">{severity}</Badge>
  }
  return (
    <Badge variant={config.variant} className={config.className}>
      {severity}
    </Badge>
  )
}
