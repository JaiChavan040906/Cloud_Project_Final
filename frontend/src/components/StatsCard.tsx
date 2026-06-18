import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

interface StatsCardProps {
  title: string
  value: number
  icon?: React.ReactNode
}

export default function StatsCard({ title, value, icon }: StatsCardProps) {
  return (
    <Card className="p-3">
      <CardHeader className="flex flex-row items-center justify-between pb-2 px-0 pt-0">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        {icon && <div className="text-muted-foreground">{icon}</div>}
      </CardHeader>
      <CardContent className="px-0 pb-0">
        <div className="text-2xl font-bold">{value}</div>
      </CardContent>
    </Card>
  )
}
