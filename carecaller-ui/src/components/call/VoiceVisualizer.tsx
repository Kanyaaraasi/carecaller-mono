import { cn } from "@/lib/utils"

interface VoiceVisualizerProps {
  active: boolean
  className?: string
}

const BARS = 24
const heights = [40, 65, 30, 80, 55, 45, 70, 35, 60, 85, 50, 75, 38, 68, 42, 78, 52, 62, 48, 72, 58, 44, 82, 36]
const delays = [0, 80, 160, 40, 200, 120, 60, 180, 100, 20, 140, 220, 50, 170, 90, 30, 210, 130, 70, 190, 110, 150, 10, 240]

export function VoiceVisualizer({ active, className }: VoiceVisualizerProps) {
  return (
    <div className={cn("flex items-center justify-center gap-[3px]", className)}>
      {Array.from({ length: BARS }).map((_, i) => (
        <div
          key={i}
          className={cn(
            "w-[3px] rounded-full transition-all duration-300",
            active
              ? "bg-primary animate-[waveform_0.8s_ease-in-out_infinite_alternate]"
              : "bg-muted-foreground/20 h-1",
          )}
          style={
            active
              ? {
                  animationDelay: `${delays[i]}ms`,
                  // eslint-disable-next-line @typescript-eslint/no-explicit-any
                  ["--wave-height" as any]: `${heights[i]}%`,
                }
              : undefined
          }
        />
      ))}
    </div>
  )
}
