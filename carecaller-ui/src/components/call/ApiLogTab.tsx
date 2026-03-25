import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { RiDeleteBinLine, RiArrowDownSLine } from "@remixicon/react"
import type { ApiLogEntry } from "@/lib/api/types"

interface ApiLogTabProps {
  entries: ApiLogEntry[]
  onClear: () => void
}

function statusVariant(status: number) {
  if (status >= 200 && status < 300) return "default" as const
  if (status >= 400) return "destructive" as const
  return "secondary" as const
}

export function ApiLogTab({ entries, onClear }: ApiLogTabProps) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b px-4 py-2">
        <span className="text-muted-foreground text-xs">
          {entries.length} request{entries.length !== 1 ? "s" : ""}
        </span>
        <Button
          variant="ghost"
          size="icon-xs"
          onClick={onClear}
          disabled={entries.length === 0}
        >
          <RiDeleteBinLine className="size-3" />
        </Button>
      </div>
      <ScrollArea className="flex-1">
        {entries.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <p className="text-muted-foreground text-sm">No API calls yet</p>
            <p className="text-muted-foreground text-xs">
              Requests will appear here as they happen
            </p>
          </div>
        ) : (
          <div className="flex flex-col">
            {entries.map((entry) => (
              <Collapsible key={entry.id}>
                <CollapsibleTrigger className="flex w-full items-center gap-2 border-b px-4 py-2 text-left text-xs transition-colors hover:bg-muted/50">
                  <Badge
                    variant={
                      entry.method === "GET" ? "secondary" : "outline"
                    }
                    className="font-mono text-[10px]"
                  >
                    {entry.method}
                  </Badge>
                  <span className="min-w-0 flex-1 truncate font-mono text-muted-foreground">
                    {entry.endpoint}
                  </span>
                  <Badge variant={statusVariant(entry.status)} className="font-mono text-[10px]">
                    {entry.status}
                  </Badge>
                  <span className="font-mono text-muted-foreground">
                    {entry.latencyMs}ms
                  </span>
                  <RiArrowDownSLine className="size-3 text-muted-foreground transition-transform [[data-state=open]_&]:rotate-180" />
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <pre className="max-h-40 overflow-auto border-b bg-muted/30 px-4 py-2 font-mono text-[11px] text-muted-foreground">
                    {entry.body}
                  </pre>
                </CollapsibleContent>
              </Collapsible>
            ))}
          </div>
        )}
      </ScrollArea>
    </div>
  )
}
