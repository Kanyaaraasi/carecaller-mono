import { useRef, useEffect, useState } from "react"
import { useParams, useNavigate } from "@tanstack/react-router"
import { useQueryState } from "nuqs"
import { toast } from "sonner"
import {
  ResizablePanelGroup,
  ResizablePanel,
  ResizableHandle,
} from "@/components/ui/resizable"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Input } from "@/components/ui/input"
import { Separator } from "@/components/ui/separator"
import {
  RiPhoneLine,
  RiPhoneFill,
  RiMicLine,
  RiMicOffLine,
  RiSettings3Line,
  RiSendPlane2Fill,
  RiTimeLine,
  RiCheckLine,
  RiErrorWarningLine,
  RiArrowLeftLine,
} from "@remixicon/react"
import { Inspector } from "@/components/call/Inspector"
import { VoiceVisualizer } from "@/components/call/VoiceVisualizer"
import { ThemeToggle } from "@/components/ThemeToggle"
import type { ImperativePanelHandle } from "react-resizable-panels"

import {
  usePatient,
  useQuestions,
  useStartCall,
  useSendMessage,
  useEndCall,
  useCallResponses,
} from "@/lib/api/hooks"
import { useCallStore } from "@/stores/call-store"

export function ActiveCall() {
  const { callId } = useParams({ from: "/call/$callId" })
  const [patientId] = useQueryState("patientId")
  const navigate = useNavigate()
  const inspectorRef = useRef<ImperativePanelHandle>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const [inspectorCollapsed, setInspectorCollapsed] = useState(false)
  const [messageInput, setMessageInput] = useState("")

  // Zustand store
  const store = useCallStore()

  // Init store when route mounts
  useEffect(() => {
    if (callId && patientId) {
      store.initCall(callId, patientId)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [callId, patientId])

  // API hooks
  const { data: patient, isLoading: patientLoading, isError: patientError } = usePatient(patientId ?? "")
  const { data: questions } = useQuestions()
  const startCall = useStartCall()
  const sendMessage = useSendMessage()
  const endCall = useEndCall()
  const { data: callResponsesData } = useCallResponses(
    callId,
    store.callStatus === "in-progress",
  )

  // Init responses from questions
  useEffect(() => {
    if (questions && store.responses.length === 0) {
      store.setResponses(
        questions.map((q) => ({
          question_index: q.index,
          question: q.text,
          answer: null,
          status: "pending",
        })),
      )
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [questions])

  // Sync polled responses
  useEffect(() => {
    if (callResponsesData?.responses) {
      store.setResponses(callResponsesData.responses)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [callResponsesData])

  // Call timer
  useEffect(() => {
    if (store.callStatus !== "in-progress") return
    const interval = setInterval(() => store.incrementElapsed(), 1000)
    return () => clearInterval(interval)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [store.callStatus])

  // Auto-scroll transcript
  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    })
  }, [store.transcript])

  // Error state: no patientId or patient fetch failed
  if (!patientId || patientError) {
    return (
      <div className="flex h-svh flex-col items-center justify-center gap-4 px-4 text-center">
        <div className="flex size-16 items-center justify-center rounded-full bg-destructive/10 text-destructive">
          <RiErrorWarningLine className="size-8" />
        </div>
        <div>
          <p className="font-medium">
            {!patientId ? "No patient selected" : "Failed to load patient"}
          </p>
          <p className="text-muted-foreground mt-1 text-sm">
            {!patientId
              ? "Go back and select a patient to call."
              : "The patient could not be found. Please try again."}
          </p>
        </div>
        <Button variant="outline" onClick={() => navigate({ to: "/" })}>
          <RiArrowLeftLine className="size-4" />
          Back to patients
        </Button>
      </div>
    )
  }

  // Loading state while patient data loads
  if (patientLoading && !patient) {
    return (
      <div className="flex h-svh flex-col items-center justify-center gap-3">
        <div className="bg-primary/10 text-primary flex size-12 animate-pulse items-center justify-center rounded-full">
          <RiPhoneLine className="size-6" />
        </div>
        <p className="text-muted-foreground text-sm">Loading patient...</p>
      </div>
    )
  }

  function formatTime(seconds: number) {
    const m = Math.floor(seconds / 60)
    const s = seconds % 60
    return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`
  }

  function handleStartCall() {
    store.setCallStatus("connecting")
    const start = Date.now()
    startCall.mutate(
      { patient_id: patientId ?? "", config: store.config },
      {
        onSuccess: (data) => {
          store.logApi("POST", "/api/call/start", 200, data, Date.now() - start)
          toast.success("Call connected")
          store.setCallStatus("in-progress")
          store.addTranscriptMessage({
            id: crypto.randomUUID(),
            role: "agent",
            text: data.greeting_message,
            timestamp: 0,
          })
          if (store.responses.length > 0) {
            store.updateResponse({
              ...store.responses[0],
              status: "asking",
            })
          }
        },
        onError: (err) => {
          store.logApi("POST", "/api/call/start", 500, { error: String(err) }, Date.now() - start)
          toast.error("Failed to connect call")
          store.setCallStatus("idle")
        },
      },
    )
  }

  function handleEndCall() {
    const start = Date.now()
    endCall.mutate(
      { call_id: callId, reason: "completed" },
      {
        onSuccess: (data) => {
          store.logApi("POST", `/api/call/${callId}/end`, 200, data, Date.now() - start)
          toast.info("Call ended")
          store.setCallStatus("completed")
          navigate({ to: "/call/$callId/summary", params: { callId } })
        },
        onError: (err) => {
          store.logApi("POST", `/api/call/${callId}/end`, 500, { error: String(err) }, Date.now() - start)
          store.setCallStatus("completed")
          navigate({ to: "/call/$callId/summary", params: { callId } })
        },
      },
    )
  }

  function handleSendMessage() {
    if (!messageInput.trim() || store.callStatus !== "in-progress") return

    const text = messageInput.trim()
    const userMsgId = crypto.randomUUID()
    store.addTranscriptMessage({
      id: userMsgId,
      role: "user",
      text,
      timestamp: store.elapsed,
    })
    setMessageInput("")

    const start = Date.now()
    sendMessage.mutate(
      { call_id: callId, message: text, timestamp: store.elapsed },
      {
        onSuccess: (data) => {
          store.logApi("POST", `/api/call/${callId}/message`, 200, data, Date.now() - start)
          store.addTranscriptMessage({
            id: crypto.randomUUID(),
            role: "agent",
            text: data.agent_message,
            timestamp: store.elapsed,
          })
          if (data.captured_response) {
            store.updateResponse(data.captured_response)
            store.attachCapturedAnswer(userMsgId, {
              questionIndex: data.captured_response.question_index,
              question: data.captured_response.question,
              answer: data.captured_response.answer ?? "",
            })
          }
          store.setCallStatus(data.call_status)
        },
        onError: (err) => {
          store.logApi("POST", `/api/call/${callId}/message`, 500, { error: String(err) }, Date.now() - start)
          toast.error("Failed to send message")
        },
      },
    )
  }

  function toggleInspector() {
    const panel = inspectorRef.current
    if (!panel) return
    if (inspectorCollapsed) {
      panel.expand()
    } else {
      panel.collapse()
    }
  }

  const statusColor: Record<string, string> = {
    idle: "bg-muted-foreground",
    connecting: "bg-amber-500 animate-pulse",
    "in-progress": "bg-emerald-500 animate-pulse",
    completed: "bg-red-500",
    escalated: "bg-red-500",
  }

  const answeredCount = store.responses.filter((r) => r.status === "answered").length

  return (
    <div className="flex h-svh flex-col">
      {/* Top bar */}
      <div className="border-b bg-card px-4 py-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`size-2 rounded-full ${statusColor[store.callStatus]}`} />
            <span className="text-sm font-medium capitalize">
              {store.callStatus === "idle" ? "Ready" : store.callStatus}
            </span>
            {store.callStatus !== "idle" && (
              <>
                <Separator orientation="vertical" className="h-4" />
                <span className="text-muted-foreground flex items-center gap-1 font-mono text-xs">
                  <RiTimeLine className="size-3" />
                  {formatTime(store.elapsed)}
                </span>
                <Separator orientation="vertical" className="h-4" />
                <span className="text-muted-foreground text-xs">
                  {answeredCount}/{store.responses.length} answered
                </span>
              </>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="font-mono text-xs">
              {callId}
            </Badge>
            <ThemeToggle />
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={toggleInspector}
              aria-label="Toggle inspector"
            >
              <RiSettings3Line className="size-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Main content */}
      <ResizablePanelGroup direction="horizontal" className="flex-1">
        {/* Phone pane */}
        <ResizablePanel defaultSize={50} minSize={35}>
          <div className="flex h-full flex-col items-center justify-center bg-background p-6">
            <div className="flex w-full max-w-md flex-1 flex-col overflow-hidden rounded-2xl border shadow-lg">
              {/* Phone header */}
              <div className="border-b bg-card px-4 py-3">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">
                      {patient?.name ?? "Patient Call"}
                    </p>
                    <p className="text-muted-foreground text-xs">
                      {patient?.medication
                        ? `${patient.medication} · ${answeredCount}/${store.responses.length} answered`
                        : `${answeredCount}/${store.responses.length} questions answered`}
                    </p>
                  </div>
                  <div
                    className={`size-2.5 rounded-full ${statusColor[store.callStatus]}`}
                  />
                </div>
              </div>

              {/* Transcript area */}
              <ScrollArea className="flex-1 bg-muted/30" ref={scrollRef}>
                <div className="flex flex-col gap-3 p-4">
                  {store.callStatus === "idle" && (
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

                  {store.callStatus === "connecting" && (
                    <div className="flex flex-col items-center gap-3 py-16 text-center">
                      <div className="flex size-16 animate-pulse items-center justify-center rounded-full bg-amber-500/10 text-amber-500">
                        <RiPhoneFill className="size-8" />
                      </div>
                      <p className="text-muted-foreground text-sm">
                        Connecting...
                      </p>
                    </div>
                  )}

                  {store.transcript.map((msg) => (
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
              </ScrollArea>

              {/* Voice visualizer */}
              {(store.callStatus === "in-progress" || store.callStatus === "connecting") && (
                <div className="border-t bg-card/50 px-6 py-2">
                  <VoiceVisualizer
                    active={store.callStatus === "in-progress" && !store.isMuted}
                    className="h-8"
                  />
                </div>
              )}

              {/* Phone controls */}
              <div className="border-t bg-card p-3">
                {store.callStatus === "idle" ? (
                  <Button className="w-full" onClick={handleStartCall}>
                    <RiPhoneFill className="size-4" />
                    Start Call
                  </Button>
                ) : store.callStatus === "connecting" ? (
                  <Button className="w-full" disabled>
                    Connecting...
                  </Button>
                ) : store.callStatus === "in-progress" ? (
                  <div className="flex flex-col gap-2">
                    <form
                      className="flex gap-2"
                      onSubmit={(e) => {
                        e.preventDefault()
                        handleSendMessage()
                      }}
                    >
                      <Input
                        placeholder="Type a response..."
                        value={messageInput}
                        onChange={(e) => setMessageInput(e.target.value)}
                        className="flex-1"
                      />
                      <Button
                        type="submit"
                        size="icon"
                        disabled={!messageInput.trim()}
                      >
                        <RiSendPlane2Fill className="size-4" />
                      </Button>
                    </form>
                    <div className="flex items-center justify-center gap-2">
                      <Button
                        variant={store.isMuted ? "destructive" : "outline"}
                        size="icon-sm"
                        onClick={() => store.toggleMute()}
                      >
                        {store.isMuted ? (
                          <RiMicOffLine className="size-4" />
                        ) : (
                          <RiMicLine className="size-4" />
                        )}
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={handleEndCall}
                      >
                        <RiPhoneFill className="size-3" />
                        End Call
                      </Button>
                    </div>
                  </div>
                ) : (
                  <Button
                    className="w-full"
                    variant="outline"
                    onClick={() => navigate({ to: "/" })}
                  >
                    New Call
                  </Button>
                )}
              </div>
            </div>
          </div>
        </ResizablePanel>

        <ResizableHandle withHandle />

        {/* Inspector pane */}
        <ResizablePanel
          ref={inspectorRef}
          defaultSize={50}
          minSize={25}
          collapsible
          collapsedSize={0}
          onCollapse={() => setInspectorCollapsed(true)}
          onExpand={() => setInspectorCollapsed(false)}
        >
          <Inspector />
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  )
}
