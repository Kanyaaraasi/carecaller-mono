import { useRef, useEffect, useState } from "react"
import { useParams, useNavigate } from "@tanstack/react-router"
import { useQueryState } from "nuqs"
import {
  ResizablePanelGroup,
  ResizablePanel,
  ResizableHandle,
} from "@/components/ui/resizable"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import {
  RiPhoneLine,
  RiSettings3Line,
  RiTimeLine,
  RiErrorWarningLine,
  RiArrowLeftLine,
} from "@remixicon/react"
import { Inspector } from "@/components/call/Inspector"
import { Transcript } from "@/components/call/Transcript"
import { PhoneControls } from "@/components/call/PhoneControls"
import { VoiceVisualizer } from "@/components/call/VoiceVisualizer"
import { VoiceRoom } from "@/components/call/VoiceRoom"
import { ThemeToggle } from "@/components/ThemeToggle"
import type { ImperativePanelHandle } from "react-resizable-panels"

import { usePatient, useQuestions, useCallResponses, useCallActions } from "@/lib/api/hooks"
import { useCallStore } from "@/stores/call-store"
import { formatTime } from "@/lib/utils"

const STATUS_COLORS: Record<string, string> = {
  idle: "bg-muted-foreground",
  connecting: "bg-amber-500 animate-pulse",
  "in-progress": "bg-emerald-500 animate-pulse",
  completed: "bg-red-500",
  escalated: "bg-red-500",
}

export function ActiveCall() {
  const { callId } = useParams({ from: "/call/$callId" })
  const [patientId] = useQueryState("patientId")
  const navigate = useNavigate()
  const inspectorRef = useRef<ImperativePanelHandle>(null)
  const [inspectorCollapsed, setInspectorCollapsed] = useState(false)

  // Store selectors — individual selectors are fine here since each
  // value is a primitive or used directly in render
  const callStatus = useCallStore((s) => s.callStatus)
  const elapsed = useCallStore((s) => s.elapsed)
  const responses = useCallStore((s) => s.responses)
  const isMuted = useCallStore((s) => s.isMuted)
  const isVoiceMode = useCallStore((s) => s.isVoiceMode)
  const initCall = useCallStore((s) => s.initCall)
  const setResponses = useCallStore((s) => s.setResponses)
  const incrementElapsed = useCallStore((s) => s.incrementElapsed)

  // Call actions hook — encapsulates start/send/end logic
  const {
    messageInput,
    setMessageInput,
    handleStartCall,
    handleEndCall,
    handleSendMessage,
  } = useCallActions(callId, patientId ?? "")

  // API hooks
  const { data: patient, isLoading: patientLoading, isError: patientError } = usePatient(patientId ?? "")
  const { data: questions } = useQuestions()
  const { data: callResponsesData } = useCallResponses(callId, callStatus === "in-progress" && !isVoiceMode)

  // Init store when route mounts
  useEffect(() => {
    if (callId && patientId) {
      initCall(callId, patientId)
    }
  }, [callId, patientId, initCall])

  // Init responses from questions
  useEffect(() => {
    if (questions && responses.length === 0) {
      setResponses(
        questions.map((q) => ({
          question_index: q.index,
          question: q.text,
          answer: null,
          status: "pending",
        })),
      )
    }
  }, [questions, responses.length, setResponses])

  // Sync polled responses
  useEffect(() => {
    if (callResponsesData?.responses) {
      setResponses(callResponsesData.responses)
    }
  }, [callResponsesData, setResponses])

  // Call timer
  useEffect(() => {
    if (callStatus !== "in-progress") return
    const interval = setInterval(incrementElapsed, 1000)
    return () => clearInterval(interval)
  }, [callStatus, incrementElapsed])

  // Error state
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

  // Loading state
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

  const answeredCount = responses.filter((r) => r.status === "answered").length

  return (
    <div className="flex h-svh flex-col">
      {/* Top bar */}
      <div className="border-b bg-card px-4 py-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`size-2 rounded-full ${STATUS_COLORS[callStatus]}`} />
            <span className="text-sm font-medium capitalize">
              {callStatus === "idle" ? "Ready" : callStatus}
            </span>
            {callStatus !== "idle" && (
              <>
                <Separator orientation="vertical" className="h-4" />
                <span className="text-muted-foreground flex items-center gap-1 font-mono text-xs">
                  <RiTimeLine className="size-3" />
                  {formatTime(elapsed)}
                </span>
                <Separator orientation="vertical" className="h-4" />
                <span className="text-muted-foreground text-xs">
                  {answeredCount}/{responses.length} answered
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
              onClick={() => {
                const panel = inspectorRef.current
                if (!panel) return
                if (inspectorCollapsed) panel.expand()
                else panel.collapse()
              }}
              aria-label="Toggle inspector"
            >
              <RiSettings3Line className="size-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* LiveKit voice connection (invisible — just manages audio) */}
      {isVoiceMode && <VoiceRoom />}

      {/* Main content */}
      <ResizablePanelGroup direction="horizontal" className="flex-1">
        {/* Phone pane */}
        <ResizablePanel defaultSize={50} minSize={35}>
          <div className="flex h-full min-h-0 flex-col items-center justify-center bg-background p-6">
            <div className="flex w-full max-w-md flex-1 flex-col overflow-hidden rounded-2xl border shadow-lg min-h-0">
              {/* Phone header */}
              <div className="shrink-0 border-b bg-card px-4 py-3">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">
                      {patient?.name ?? "Patient Call"}
                    </p>
                    <p className="text-muted-foreground text-xs">
                      {patient?.medication
                        ? `${patient.medication} · ${answeredCount}/${responses.length} answered`
                        : `${answeredCount}/${responses.length} questions answered`}
                    </p>
                  </div>
                  <div className={`size-2.5 rounded-full ${STATUS_COLORS[callStatus]}`} />
                </div>
              </div>

              <Transcript />

              {/* Voice visualizer */}
              {(callStatus === "in-progress" || callStatus === "connecting") && (
                <div className="shrink-0 border-t bg-card/50 px-6 py-2">
                  <VoiceVisualizer
                    active={callStatus === "in-progress" && !isMuted}
                    className="h-8"
                  />
                </div>
              )}

              <PhoneControls
                messageInput={messageInput}
                onMessageInputChange={setMessageInput}
                onStartCall={handleStartCall}
                onEndCall={handleEndCall}
                onSendMessage={handleSendMessage}
              />
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
