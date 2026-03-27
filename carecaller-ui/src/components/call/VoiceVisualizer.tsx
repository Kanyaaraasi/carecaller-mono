import { memo } from "react"
import { cn } from "@/lib/utils"

interface VoiceVisualizerProps {
  active: boolean
  className?: string
}

/** Number of vertical bars in the waveform display. */
const BAR_COUNT = 24

/** Animation duration for each bar's waveform cycle (seconds). */
const ANIMATION_DURATION = 0.8

/** Target height (%) for each bar — creates an organic, non-uniform wave pattern. */
const BAR_HEIGHTS = [
  40, 65, 30, 80, 55, 45, 70, 35, 60, 85, 50, 75,
  38, 68, 42, 78, 52, 62, 48, 72, 58, 44, 82, 36,
] as const

/** Staggered start delay (ms) for each bar — prevents all bars animating in sync. */
const BAR_DELAYS = [
   0,  80, 160,  40, 200, 120,  60, 180, 100,  20, 140, 220,
  50, 170,  90,  30, 210, 130,  70, 190, 110, 150,  10, 240,
] as const

export const VoiceVisualizer = memo(function VoiceVisualizer({
  active,
  className,
}: VoiceVisualizerProps) {
  return (
    <div className={cn("flex items-center justify-center gap-[3px]", className)}>
      {Array.from({ length: BAR_COUNT }).map((_, i) => (
        <div
          key={i}
          className={cn(
            "w-[3px] rounded-full transition-all duration-300",
            active
              ? `bg-primary animate-[waveform_${ANIMATION_DURATION}s_ease-in-out_infinite_alternate]`
              : "bg-muted-foreground/20 h-1",
          )}
          style={
            active
              ? ({
                  animationDelay: `${BAR_DELAYS[i]}ms`,
                  "--wave-height": `${BAR_HEIGHTS[i]}%`,
                } as React.CSSProperties)
              : undefined
          }
        />
      ))}
    </div>
  )
})
