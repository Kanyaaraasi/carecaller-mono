import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Slider } from "@/components/ui/slider"
import { Separator } from "@/components/ui/separator"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import type { CallConfig, Tone } from "@/lib/api/types"

interface ConfigTabProps {
  config: CallConfig
  onConfigChange: (config: Partial<CallConfig>) => void
  disabled?: boolean
}

const TONES: { value: Tone; label: string }[] = [
  { value: "friendly", label: "Friendly" },
  { value: "neutral", label: "Neutral" },
  { value: "formal", label: "Formal" },
]

export function ConfigTab({
  config,
  onConfigChange,
  disabled,
}: ConfigTabProps) {
  return (
    <ScrollArea className="h-full">
      <div className="flex flex-col gap-6 p-4">
        {/* Tone */}
        <div className="flex flex-col gap-2">
          <Label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Agent Tone
          </Label>
          <Select
            value={config.tone}
            onValueChange={(val) => onConfigChange({ tone: val as Tone })}
            disabled={disabled}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {TONES.map((t) => (
                <SelectItem key={t.value} value={t.value}>
                  {t.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Speed */}
        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <Label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Response Speed
            </Label>
            <span className="font-mono text-xs text-muted-foreground">
              {config.speed.toFixed(1)}x
            </span>
          </div>
          <Slider
            value={[config.speed]}
            onValueChange={([val]) => onConfigChange({ speed: val })}
            min={0.5}
            max={2.0}
            step={0.1}
            disabled={disabled}
          />
        </div>

        <Separator />

        {/* Toggles */}
        <div className="flex flex-col gap-4">
          <Label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Agent Behavior
          </Label>
          <div className="flex items-center justify-between">
            <Label className="text-sm">Auto-greet patient</Label>
            <Switch
              checked={config.auto_greet}
              onCheckedChange={(checked) =>
                onConfigChange({ auto_greet: !!checked })
              }
              disabled={disabled}
            />
          </div>
          <div className="flex items-center justify-between">
            <Label className="text-sm">Skip answered questions</Label>
            <Switch
              checked={config.skip_answered}
              onCheckedChange={(checked) =>
                onConfigChange({ skip_answered: !!checked })
              }
              disabled={disabled}
            />
          </div>
        </div>

        <Separator />

        <p className="text-xs text-muted-foreground">
          Scenario and edge cases are determined by the patient data from the
          backend and are not configurable here.
        </p>
      </div>
    </ScrollArea>
  )
}
