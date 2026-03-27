import { memo, useEffect, useRef } from "react"
import { RiPhoneLine, RiPhoneFill, RiCheckLine } from "@remixicon/react"
import { useCallStore } from "@/stores/call-store"
import { formatTime } from "@/lib/utils"

export const Transcript = memo(function Transcript() {
  const scrollRef = useRef<HTMLDivElement>(null)
  const callStatus = useCallStore((s) => s.callStatus)
  const transcript = useCallStore((s) => s.transcript)

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    })
  }, [transcript])

  return (
    <div className="flex-1 overflow-y-auto bg-muted/30 min-h-0" ref={scrollRef}>
      <div className="flex flex-col gap-3 p-4">
        {callStatus === "idle" && (
          <div className="flex flex-1 flex-col items-center justify-center gap-4 py-16 text-center">
            <div className="bg-primary/10 text-primary flex size-16 items-center justify-center rounded-full">
              <RiPhoneLine className="size-8" />
            </div>
            <div>
              <p className="font-medium">Ready to start</p>
              <p className="text-muted-foreground mt-1 text-xs">
                Press the call button to begin
              </p>
            </div>
          </div>
        )}

        {callStatus === "connecting" && (
          <div className="flex flex-col items-center gap-3 py-16 text-center">
            <div className="flex size-16 animate-pulse items-center justify-center rounded-full bg-amber-500/10 text-amber-500">
              <RiPhoneFill className="size-8" />
            </div>
            <p className="text-muted-foreground text-sm">Connecting...</p>
          </div>
        )}

        {transcript.map((msg) => (
          <div
            key={msg.id}
            className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"}`}
          >
            <div
              className={`max-w-[80%] rounded-xl px-3 py-2 text-sm ${
                msg.role === "user"
                  ? "bg-primary text-primary-foreground"
                  : "bg-card border"
              }`}
            >
              {msg.text}
              <span
                className={`mt-1 block text-right font-mono text-[10px] ${
                  msg.role === "user"
                    ? "text-primary-foreground/60"
                    : "text-muted-foreground"
                }`}
              >
                {formatTime(msg.timestamp)}
              </span>
            </div>
            {msg.capturedAnswer && (
              <span className="mt-1 inline-flex items-center gap-1 rounded-md bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-600 dark:text-emerald-400">
                <RiCheckLine className="size-2.5" />
                Q{msg.capturedAnswer.questionIndex + 1} captured
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  )
})
