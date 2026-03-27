import { useParams, useNavigate } from "@tanstack/react-router"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Progress } from "@/components/ui/progress"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  RiPhoneLine,
  RiTimeLine,
  RiCheckLine,
  RiCircleLine,
  RiSkipForwardLine,
  RiArrowLeftLine,
} from "@remixicon/react"
import { Skeleton } from "@/components/ui/skeleton"
import { useCallResponses } from "@/lib/api/hooks"
import { ThemeToggle } from "@/components/ThemeToggle"
import { formatTime } from "@/lib/utils"
import type { CallOutcome } from "@/lib/api/types"

const outcomeBadgeVariant: Record<
  CallOutcome,
  "default" | "secondary" | "destructive" | "outline"
> = {
  completed: "default",
  incomplete: "secondary",
  opted_out: "outline",
  scheduled: "secondary",
  escalated: "destructive",
  wrong_number: "destructive",
  voicemail: "outline",
}

export function CallSummary() {
  const { callId } = useParams({ from: "/call/$callId/summary" })
  const navigate = useNavigate()

  const { data: callData, isLoading, isError } = useCallResponses(callId, true)

  const responses = callData?.responses ?? []
  const transcript = callData?.transcript ?? []
  const completeness = callData?.completeness ?? 0
  const outcome = callData?.outcome ?? "incomplete"
  const duration = callData?.duration_seconds
  const answeredCount = responses.filter((r) => r.status === "answered").length

  function statusIcon(status: string) {
    switch (status) {
      case "answered":
        return <RiCheckLine className="size-4 text-emerald-500" />
      case "skipped":
        return <RiSkipForwardLine className="text-muted-foreground size-4" />
      default:
        return <RiCircleLine className="text-muted-foreground size-4" />
    }
  }

  return (
    <div className="flex h-svh flex-col">
      {/* Top bar */}
      <div className="border-b bg-card px-4 py-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() =>
                navigate({ to: "/call/$callId", params: { callId } })
              }
            >
              <RiArrowLeftLine className="size-4" />
            </Button>
            <span className="text-sm font-medium">Call Summary</span>
            <Separator orientation="vertical" className="h-4" />
            <Badge variant="outline" className="font-mono text-xs">
              {callId}
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate({ to: "/" })}
            >
              <RiPhoneLine className="size-3" />
              New Call
            </Button>
          </div>
        </div>
      </div>

      <ScrollArea className="flex-1">
        <div className="mx-auto max-w-3xl space-y-6 p-6">
          {isLoading && (
            <div className="space-y-6">
              <div className="grid grid-cols-3 gap-4">
                {Array.from({ length: 3 }).map((_, i) => (
                  <Skeleton key={i} className="h-24 rounded-xl" />
                ))}
              </div>
              <Skeleton className="h-48 rounded-xl" />
              <Skeleton className="h-64 rounded-xl" />
            </div>
          )}

          {isError && (
            <div className="flex flex-col items-center gap-4 py-16 text-center">
              <p className="text-muted-foreground text-sm">
                Failed to load call summary. Is the API running?
              </p>
              <Button variant="outline" size="sm" onClick={() => navigate({ to: "/" })}>
                Back to Home
              </Button>
            </div>
          )}

          {/* Overview cards */}
          <div className="grid grid-cols-3 gap-4">
            <Card size="sm">
              <CardHeader>
                <CardTitle className="text-xs font-normal text-muted-foreground">
                  Outcome
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Badge variant={outcomeBadgeVariant[outcome]}>{outcome}</Badge>
              </CardContent>
            </Card>

            <Card size="sm">
              <CardHeader>
                <CardTitle className="text-xs font-normal text-muted-foreground">
                  Duration
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-1.5 font-mono text-lg font-medium">
                  <RiTimeLine className="text-muted-foreground size-4" />
                  {duration != null ? formatTime(duration) : "—"}
                </div>
              </CardContent>
            </Card>

            <Card size="sm">
              <CardHeader>
                <CardTitle className="text-xs font-normal text-muted-foreground">
                  Completeness
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="mb-2 font-mono text-lg font-medium">
                  {answeredCount}/{responses.length}
                </p>
                <Progress value={completeness * 100} />
              </CardContent>
            </Card>
          </div>

          {/* Transcript */}
          <Card>
            <CardHeader>
              <CardTitle>Transcript</CardTitle>
            </CardHeader>
            <CardContent>
              {transcript.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No transcript data available.
                </p>
              ) : (
                <div className="flex flex-col gap-3">
                  {transcript.map((msg) => (
                    <div key={msg.id} className="flex gap-3 text-sm">
                      <span
                        className={`mt-0.5 shrink-0 font-mono text-xs font-medium ${
                          msg.role === "agent"
                            ? "text-primary"
                            : "text-muted-foreground"
                        }`}
                      >
                        {msg.role === "agent" ? "AGENT" : "USER"}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p>{msg.text}</p>
                        <span className="font-mono text-[10px] text-muted-foreground">
                          {formatTime(msg.timestamp)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Responses table */}
          <Card>
            <CardHeader>
              <CardTitle>Structured Responses</CardTitle>
            </CardHeader>
            <CardContent>
              {responses.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No response data available.
                </p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-10">#</TableHead>
                      <TableHead>Question</TableHead>
                      <TableHead>Answer</TableHead>
                      <TableHead className="w-16">Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {responses.map((r) => (
                      <TableRow key={r.question_index}>
                        <TableCell className="font-mono text-xs text-muted-foreground">
                          {r.question_index + 1}
                        </TableCell>
                        <TableCell>{r.question}</TableCell>
                        <TableCell>
                          {r.answer ? (
                            r.answer
                          ) : (
                            <span className="text-muted-foreground">—</span>
                          )}
                        </TableCell>
                        <TableCell>{statusIcon(r.status)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </div>
      </ScrollArea>
    </div>
  )
}
