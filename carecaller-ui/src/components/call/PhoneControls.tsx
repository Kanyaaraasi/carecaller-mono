import { memo } from "react"
import { useNavigate } from "@tanstack/react-router"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  RiPhoneFill,
  RiMicLine,
  RiMicOffLine,
  RiSendPlane2Fill,
  RiVoiceprintLine,
  RiChat1Line,
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
  const isVoiceMode = useCallStore((s) => s.isVoiceMode)
  const setVoiceMode = useCallStore((s) => s.setVoiceMode)

  if (callStatus === "idle") {
    return (
      <div className="shrink-0 border-t bg-card p-3">
        <div className="flex flex-col gap-2">
          {/* Voice / Text toggle */}
          <div className="flex items-center justify-center gap-1 rounded-lg bg-muted p-1">
            <button
              className={`flex flex-1 items-center justify-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                !isVoiceMode
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
              onClick={() => setVoiceMode(false)}
            >
              <RiChat1Line className="size-3.5" />
              Text
            </button>
            <button
              className={`flex flex-1 items-center justify-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                isVoiceMode
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
              onClick={() => setVoiceMode(true)}
            >
              <RiVoiceprintLine className="size-3.5" />
              Voice
            </button>
          </div>
          <Button className="w-full" onClick={onStartCall}>
            {isVoiceMode ? (
              <RiVoiceprintLine className="size-4" />
            ) : (
              <RiPhoneFill className="size-4" />
            )}
            {isVoiceMode ? "Start Voice Call" : "Start Call"}
          </Button>
        </div>
      </div>
    )
  }

  if (callStatus === "connecting") {
    return (
      <div className="shrink-0 border-t bg-card p-3">
        <Button className="w-full" disabled>
          {isVoiceMode ? "Connecting voice..." : "Connecting..."}
        </Button>
      </div>
    )
  }

  if (callStatus === "in-progress") {
    // Voice mode: no text input, just mute + end
    if (isVoiceMode) {
      return (
        <div className="shrink-0 border-t bg-card p-3">
          <div className="flex flex-col items-center gap-3">
            <p className="text-muted-foreground text-xs">
              Voice call active — speak into your microphone
            </p>
            <div className="flex items-center gap-3">
              <Button
                variant={isMuted ? "destructive" : "outline"}
                size="icon"
                onClick={toggleMute}
                aria-label={isMuted ? "Unmute microphone" : "Mute microphone"}
              >
                {isMuted ? (
                  <RiMicOffLine className="size-5" />
                ) : (
                  <RiMicLine className="size-5" />
                )}
              </Button>
              <Button variant="destructive" onClick={onEndCall}>
                <RiPhoneFill className="size-4" />
                End Call
              </Button>
            </div>
          </div>
        </div>
      )
    }

    // Text mode: message input + mute + end
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
