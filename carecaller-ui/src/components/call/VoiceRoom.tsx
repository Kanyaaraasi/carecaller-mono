/**
 * VoiceRoom — connects to a LiveKit room for voice calls.
 *
 * Handles:
 * - Room connection with token from API
 * - Microphone audio publish
 * - Receiving agent audio
 * - Data channel events (response_captured, call_status) → store updates
 * - Mute/unmute via store
 */

import { useEffect, useRef, useCallback } from "react"
import {
  Room,
  RoomEvent,
  Track,
  RemoteTrack,
  RemoteTrackPublication,
  RemoteParticipant,
  DataPacket_Kind,
} from "livekit-client"
import { useCallStore } from "@/stores/call-store"

export function VoiceRoom() {
  const livekitUrl = useCallStore((s) => s.livekitUrl)
  const livekitToken = useCallStore((s) => s.livekitToken)
  const callStatus = useCallStore((s) => s.callStatus)
  const isMuted = useCallStore((s) => s.isMuted)
  const setCallStatus = useCallStore((s) => s.setCallStatus)
  const addTranscriptMessage = useCallStore((s) => s.addTranscriptMessage)
  const updateResponse = useCallStore((s) => s.updateResponse)
  const logApi = useCallStore((s) => s.logApi)

  const roomRef = useRef<Room | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  const handleDataReceived = useCallback(
    (payload: Uint8Array) => {
      try {
        const text = new TextDecoder().decode(payload)
        const data = JSON.parse(text)

        if (data.event === "response_captured") {
          addTranscriptMessage({
            id: crypto.randomUUID(),
            role: "agent",
            text: `[Captured Q${data.question_index + 1}: ${data.answer}]`,
            timestamp: Date.now() / 1000,
            capturedAnswer: {
              questionIndex: data.question_index,
              question: data.question,
              answer: data.answer,
            },
          })
          updateResponse({
            question_index: data.question_index,
            question: data.question,
            answer: data.answer,
            status: "answered",
          })
          logApi("WS", "data_channel/response_captured", 200, data, 0)
        }

        if (data.event === "call_status") {
          if (data.status === "completed" || data.status === "escalated") {
            setCallStatus(data.status === "escalated" ? "escalated" : "completed")
          }
          logApi("WS", "data_channel/call_status", 200, data, 0)
        }
      } catch {
        // ignore non-JSON data
      }
    },
    [addTranscriptMessage, updateResponse, setCallStatus, logApi],
  )

  // Connect to room
  useEffect(() => {
    if (!livekitUrl || !livekitToken || callStatus !== "in-progress") return

    const room = new Room()
    roomRef.current = room

    // Handle agent audio tracks
    const handleTrackSubscribed = (
      track: RemoteTrack,
      _pub: RemoteTrackPublication,
      _participant: RemoteParticipant,
    ) => {
      if (track.kind === Track.Kind.Audio) {
        const el = track.attach()
        el.autoplay = true
        audioRef.current = el
        document.body.appendChild(el)
      }
    }

    const handleTrackUnsubscribed = (track: RemoteTrack) => {
      track.detach().forEach((el) => el.remove())
    }

    room.on(RoomEvent.TrackSubscribed, handleTrackSubscribed)
    room.on(RoomEvent.TrackUnsubscribed, handleTrackUnsubscribed)
    room.on(RoomEvent.DataReceived, handleDataReceived)
    room.on(RoomEvent.Disconnected, () => {
      setCallStatus("completed")
    })

    const connect = async () => {
      try {
        await room.connect(livekitUrl, livekitToken)
        // Publish microphone
        await room.localParticipant.setMicrophoneEnabled(true)
      } catch (err) {
        console.error("Failed to connect to LiveKit room:", err)
        setCallStatus("idle")
      }
    }

    connect()

    return () => {
      room.disconnect()
      roomRef.current = null
      if (audioRef.current) {
        audioRef.current.remove()
        audioRef.current = null
      }
    }
  }, [livekitUrl, livekitToken, callStatus, setCallStatus, handleDataReceived])

  // Sync mute state
  useEffect(() => {
    const room = roomRef.current
    if (!room?.localParticipant) return
    room.localParticipant.setMicrophoneEnabled(!isMuted)
  }, [isMuted])

  // No visible UI — this component just manages the connection
  return null
}
