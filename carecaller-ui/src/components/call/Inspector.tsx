import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Progress } from "@/components/ui/progress"
import {
  RiCheckLine,
  RiLoader4Line,
  RiCircleLine,
  RiSkipForwardLine,
} from "@remixicon/react"
// import { ConfigTab } from "./ConfigTab"
import { ApiLogTab } from "./ApiLogTab"
import { useCallStore } from "@/stores/call-store"
import type { QuestionResponse } from "@/lib/api/types"

const statusIcon: Record<QuestionResponse["status"], React.ReactNode> = {
  pending: <RiCircleLine className="text-muted-foreground size-4" />,
  asking: <RiLoader4Line className="text-primary size-4 animate-spin" />,
  answered: <RiCheckLine className="size-4 text-emerald-500" />,
  skipped: <RiSkipForwardLine className="text-muted-foreground size-4" />,
}

export function Inspector() {
  const responses = useCallStore((s) => s.responses)
  const callStatus = useCallStore((s) => s.callStatus)
  const apiLog = useCallStore((s) => s.apiLog)
  const clearApiLog = useCallStore((s) => s.clearApiLog)

  const answeredCount = responses.filter((r) => r.status === "answered").length
  const completeness =
    responses.length > 0 ? (answeredCount / responses.length) * 100 : 0

  return (
    <div className="flex h-full flex-col border-l bg-card">
      <Tabs defaultValue="responses" className="flex flex-1 flex-col">
        <div className="border-b px-4 pt-3">
          <TabsList variant="line">
            <TabsTrigger value="responses">Responses</TabsTrigger>
            {/* Config tab commented out — static UI with no functionality for now
            <TabsTrigger value="config">Config</TabsTrigger>
            */}
            <TabsTrigger value="api">
              API Log
              {apiLog.length > 0 && (
                <span className="ml-1 font-mono text-[10px] text-muted-foreground">
                  ({apiLog.length})
                </span>
              )}
            </TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="responses" className="flex-1 overflow-hidden">
          <ScrollArea className="h-full">
            <div className="flex flex-col gap-1 p-4">
              {responses.length === 0 ? (
                <p className="text-muted-foreground py-8 text-center text-sm">
                  Questions will appear once the call starts
                </p>
              ) : (
                responses.map((r) => (
                  <div
                    key={r.question_index}
                    className={`flex items-start gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
                      r.status === "asking" ? "bg-primary/5" : ""
                    }`}
                  >
                    <span className="mt-0.5 shrink-0">
                      {statusIcon[r.status]}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p
                        className={`${r.status === "asking" ? "font-medium text-foreground" : "text-muted-foreground"}`}
                      >
                        <span className="mr-1.5 font-mono text-xs text-muted-foreground">
                          {r.question_index + 1}.
                        </span>
                        {r.question}
                      </p>
                    </div>
                  </div>
                ))
              )}
            </div>
          </ScrollArea>
          <div className="border-t px-4 py-3">
            <div className="mb-2 flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Completeness</span>
              <span className="font-mono font-medium">
                {answeredCount}/{responses.length}
              </span>
            </div>
            <Progress value={completeness} />
          </div>
        </TabsContent>

        {/* Config tab commented out — can be re-enabled when controls are wired up
        <TabsContent value="config" className="flex-1 overflow-hidden">
          <ConfigTab
            config={config}
            onConfigChange={(c) => setConfig(c)}
            disabled={isCallActive}
          />
        </TabsContent>
        */}

        <TabsContent value="api" className="flex-1 overflow-hidden">
          <ApiLogTab entries={apiLog} onClear={clearApiLog} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
