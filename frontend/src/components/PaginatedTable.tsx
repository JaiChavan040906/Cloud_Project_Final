import { useState, useEffect, useMemo, type ReactNode } from "react"
import client from "@/api/client"
import { useDebounce } from "@/hooks/useDebounce"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

export interface Column<T> {
  key: string
  label: string
  sortable?: boolean
  render?: (item: T) => ReactNode
}

interface PaginatedTableProps<T> {
  endpoint: string
  columns: Column<T>[]
  searchPlaceholder?: string
  defaultSort?: string
  defaultSortOrder?: "asc" | "desc"
  onRowClick?: (item: T) => void
  statusFilter?: boolean
  statusOptions?: { label: string; value: string }[]
  pageSize?: number
  extraParams?: Record<string, string>
}

interface PageResponse<T> {
  items: T[]
  total: number
  page: number
  limit: number
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export default function PaginatedTable<T = any>({
  endpoint,
  columns,
  searchPlaceholder = "Search...",
  defaultSort,
  defaultSortOrder = "asc",
  onRowClick,
  statusFilter = false,
  statusOptions = [],
  pageSize = 20,
  extraParams,
}: PaginatedTableProps<T>) {
  const stableExtraParams = useMemo(() => extraParams ?? {}, [extraParams])
  const [data, setData] = useState<T[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState("")
  const [status, setStatus] = useState("")
  const [sortBy, setSortBy] = useState(defaultSort ?? "")
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">(defaultSortOrder)
  const [loading, setLoading] = useState(true)

  const debouncedSearch = useDebounce(search, 300)
  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  useEffect(() => {
    let cancelled = false
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true)

    const params: Record<string, string | number> = {
      page,
      limit: pageSize,
      ...stableExtraParams,
    }
    if (debouncedSearch) params.search = debouncedSearch
    if (status) params.status = status
    if (sortBy) {
      params.sort_by = sortBy
      params.sort_order = sortOrder
    }

    client.get<PageResponse<T>>(endpoint, { params })
      .then((res) => {
        if (!cancelled) {
          setData(res.data.items)
          setTotal(res.data.total)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setData([])
          setTotal(0)
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => { cancelled = true }
  }, [endpoint, page, pageSize, debouncedSearch, status, sortBy, sortOrder, stableExtraParams])

  function handleSort(key: string) {
    if (sortBy === key) {
      setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"))
    } else {
      setSortBy(key)
      setSortOrder("asc")
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <Input
          placeholder={searchPlaceholder}
          value={search}
          onChange={(e) => {
            setSearch(e.target.value)
            setPage(1)
          }}
          className="max-w-sm"
        />
        {statusFilter && statusOptions.length > 0 && (
          <Select value={status} onValueChange={(v) => {
            setStatus(v)
            setPage(1)
          }}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="All statuses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value=" ">All statuses</SelectItem>
              {statusOptions.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
        <div className="ml-auto text-sm text-muted-foreground">
          {total} result{total !== 1 ? "s" : ""}
        </div>
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              {columns.map((col) => (
                <TableHead
                  key={col.key}
                  className={col.sortable ? "cursor-pointer select-none" : ""}
                  onClick={() => col.sortable && handleSort(col.key)}
                >
                  <span className="flex items-center gap-1">
                    {col.label}
                    {col.sortable && sortBy === col.key && (
                      <span>{sortOrder === "asc" ? "↑" : "↓"}</span>
                    )}
                  </span>
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i}>
                  {columns.map((col) => (
                    <TableCell key={col.key}>
                      <div className="h-4 w-full animate-pulse rounded bg-muted" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : data.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={columns.length}
                  className="py-8 text-center text-muted-foreground"
                >
                  No results found
                </TableCell>
              </TableRow>
            ) : (
              data.map((item, i) => (
                  <TableRow
                    key={((item as Record<string, unknown>).id as number) ?? i}
                  className={onRowClick ? "cursor-pointer" : ""}
                  onClick={() => onRowClick?.(item)}
                >
                  {columns.map((col) => (
                    <TableCell key={col.key}>
                      {col.render
                        ? col.render(item)
                        : ((item as Record<string, unknown>)[col.key] as ReactNode) ?? "-"}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <div className="flex items-center justify-between">
        <div className="text-sm text-muted-foreground">
          Page {page} of {totalPages}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1 || loading}
            className="inline-flex h-8 items-center justify-center rounded-md border border-input bg-background px-3 text-sm font-medium hover:bg-accent disabled:pointer-events-none disabled:opacity-50"
          >
            Previous
          </button>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages || loading}
            className="inline-flex h-8 items-center justify-center rounded-md border border-input bg-background px-3 text-sm font-medium hover:bg-accent disabled:pointer-events-none disabled:opacity-50"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  )
}
