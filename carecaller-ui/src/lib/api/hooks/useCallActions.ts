/**
 * Custom hook encapsulating all call lifecycle actions.
 * Supports both text mode and voice mode (Phase 5).
 */

import { useState } from "react"
import { useNavigate } from "@tanstack/react-router"
import { toast } from "sonner"
import { useStartCall, useStartVoiceCall, useSendMessage, useEndCall } from "@/lib/api/hooks"
import { useCallStore } from "@/stores/call-store"

export function useCallActions(callId: string, patientId: string) {
  const navigate = useNavigate()
  const [messageInput, setMessageInput] = useState("")
  const startCall = useStartCall()
  const startVoiceCall = useStartVoiceCall()
  const sendMessage = useSendMessage()
  const endCall = useEndCall()

  const callStatus = useCallStore((s) => s.callStatus)
  const setCallStatus = useCallStore((s) => s.setCallStatus)
  const elapsed = useCallStore((s) => s.elapsed)
  const config = useCallStore((s) => s.config)
  const responses = useCallStore((s) => s.responses)
  const isVoiceMode = useCallStore((s) => s.isVoiceMode)
  const setLivekitConnection = useCallStore((s) => s.setLivekitConnection)
  const addTranscriptMessage = useCallStore((s) => s.addTranscriptMessage)
  const removeTranscriptMessage = useCallStore((s) => s.removeTranscriptMessage)
  const updateResponse = useCallStore((s) => s.updateResponse)
  const attachCapturedAnswer = useCallStore((s) => s.attachCapturedAnswer)
  const logApi = useCallStore((s) => s.logApi)

  function handleStartCall() {
    if (isVoiceMode) {
      handleStartVoiceCall()
    } else {
      handleStartTextCall()
    }
  }

  function handleStartTextCall() {
    setCallStatus("connecting")
    const start = Date.now()
    startCall.mutate(
      { patient_id: patientId, call_id: callId, config },
      {
        onSuccess: (data) => {
          logApi("POST", "/api/call/start", 200, data, Date.now() - start)
          toast.success("Call connected")
          setCallStatus("in-progress")
          addTranscriptMessage({
            id: crypto.randomUUID(),
            role: "agent",
            text: data.greeting_message,
            timestamp: 0,
          })
          if (responses.length > 0) {
            updateResponse({ ...responses[0], status: "asking" })
          }
        },
        onError: (err) => {
          logApi("POST", "/api/call/start", 500, { error: String(err) }, Date.now() - start)
          toast.error("Failed to connect call")
          setCallStatus("idle")
        },
      },
    )
  }

  function handleStartVoiceCall() {
    setCallStatus("connecting")
    const start = Date.now()
    startVoiceCall.mutate(
      { patient_id: patientId, call_id: callId, config },
      {
        onSuccess: (data) => {
          logApi("POST", "/api/call/start-voice", 200, data, Date.now() - start)
          setLivekitConnection(data.livekit_url, data.livekit_token)
          toast.success("Voice call connecting...")
          setCallStatus("in-progress")
        },
        onError: (err) => {
          logApi("POST", "/api/call/start-voice", 500, { error: String(err) }, Date.now() - start)
          toast.error("Failed to start voice call")
          setCallStatus("idle")
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
          logApi("POST", `/api/call/${callId}/end`, 200, data, Date.now() - start)
          toast.info("Call ended")
          setCallStatus("completed")
          navigate({ to: "/call/$callId/summary", params: { callId } })
        },
        onError: (err) => {
          logApi("POST", `/api/call/${callId}/end`, 500, { error: String(err) }, Date.now() - start)
          setCallStatus("completed")
          navigate({ to: "/call/$callId/summary", params: { callId } })
        },
      },
    )
  }

  function handleSendMessage() {
    if (!messageInput.trim() || callStatus !== "in-progress") return

    const text = messageInput.trim()
    const savedInput = messageInput
    const userMsgId = crypto.randomUUID()
    addTranscriptMessage({ id: userMsgId, role: "user", text, timestamp: elapsed })
    setMessageInput("")

    const start = Date.now()
    sendMessage.mutate(
      { call_id: callId, message: text, timestamp: elapsed },
      {
        onSuccess: (data) => {
          logApi("POST", `/api/call/${callId}/message`, 200, data, Date.now() - start)
          addTranscriptMessage({
            id: crypto.randomUUID(),
            role: "agent",
            text: data.agent_message,
            timestamp: elapsed,
          })
          if (data.captured_response) {
            updateResponse(data.captured_response)
            attachCapturedAnswer(userMsgId, {
              questionIndex: data.captured_response.question_index,
              question: data.captured_response.question,
              answer: data.captured_response.answer ?? "",
            })
          }
          setCallStatus(data.call_status)
        },
        onError: (err) => {
          logApi("POST", `/api/call/${callId}/message`, 500, { error: String(err) }, Date.now() - start)
          removeTranscriptMessage(userMsgId)
          setMessageInput(savedInput)
          toast.error("Failed to send message")
        },
      },
    )
  }

  return {
    messageInput,
    setMessageInput,
    handleStartCall,
    handleEndCall,
    handleSendMessage,
    isSending: sendMessage.isPending,
  }
}
