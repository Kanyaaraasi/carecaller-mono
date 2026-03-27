import { memo } from "react"
import { useNavigate } from "@tanstack/react-router"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  RiPhoneFill,
  RiMicLine,
  RiMicOffLine,
  RiSendPlane2Fill,
} from "@remixicon/react"
import { useCallStore } from "@/stores/call-store"

interface PhoneControlsProps {
  messageInput: string
  onMessageInputChange: (value: string) => void
  onStartCall: () => void
  onEndCall: () => void
  onSendMessage: () => void
}

export const PhoneControls = memo(function PhoneControls({
  messageInput,
  onMessageInputChange,
  onStartCall,
  onEndCall,
  onSendMessage,
}: PhoneControlsProps) {
  const navigate = useNavigate()
  const callStatus = useCallStore((s) => s.callStatus)
  const isMuted = useCallStore((s) => s.isMuted)
  const toggleMute = useCallStore((s) => s.toggleMute)

  if (callStatus === "idle") {
    return (
      <div className="shrink-0 border-t bg-card p-3">
        <Button className="w-full" onClick={onStartCall}>
          <RiPhoneFill className="size-4" />
          Start Call
        </Button>
      </div>
    )
  }

  if (callStatus === "connecting") {
    return (
      <div className="shrink-0 border-t bg-card p-3">
        <Button className="w-full" disabled>
          Connecting...
        </Button>
      </div>
    )
  }

  if (callStatus === "in-progress") {
    return (
      <div className="shrink-0 border-t bg-card p-3">
        <div className="flex flex-col gap-2">
          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault()
              onSendMessage()
            }}
          >
            <Input
              placeholder="Type a response..."
              value={messageInput}
              onChange={(e) => onMessageInputChange(e.target.value)}
              className="flex-1"
            />
            <Button type="submit" size="icon" disabled={!messageInput.trim()}>
              <RiSendPlane2Fill className="size-4" />
            </Button>
          </form>
          <div className="flex items-center justify-center gap-2">
            <Button
              variant={isMuted ? "destructive" : "outline"}
              size="icon-sm"
              onClick={toggleMute}
              aria-label={isMuted ? "Unmute microphone" : "Mute microphone"}
            >
              {isMuted ? (
                <RiMicOffLine className="size-4" />
              ) : (
                <RiMicLine className="size-4" />
              )}
            </Button>
            <Button variant="destructive" size="sm" onClick={onEndCall}>
              <RiPhoneFill className="size-3" />
              End Call
            </Button>
          </div>
        </div>
      </div>
    )
  }

  // completed / escalated
  return (
    <div className="shrink-0 border-t bg-card p-3">
      <Button
        className="w-full"
        variant="outline"
        onClick={() => navigate({ to: "/" })}
      >
        New Call
      </Button>
    </div>
  )
})
