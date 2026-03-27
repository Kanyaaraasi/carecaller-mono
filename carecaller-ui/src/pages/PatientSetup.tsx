import { useNavigate } from "@tanstack/react-router"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"
import { Separator } from "@/components/ui/separator"
import {
  RiPhoneLine,
  RiHeartPulseLine,
  RiShieldCheckLine,
  RiUserLine,
  RiMedicineBottleLine,
  RiCalendarLine,
  RiStoreLine,
  RiPhoneFill,
  RiVoiceprintLine,
  RiBarChartBoxLine,
  RiTimeLine,
  RiArrowRightLine,
  RiArrowLeftLine,
  RiStethoscopeLine,
  RiDatabase2Line,
} from "@remixicon/react"
import { ThemeToggle } from "@/components/ThemeToggle"
import { TypingAnimation } from "@/components/ui/typing-animation"
import { NumberTicker } from "@/components/ui/number-ticker"
import { ShimmerButton } from "@/components/ui/shimmer-button"
import { BlurFade } from "@/components/ui/blur-fade"
import { DotPattern } from "@/components/ui/dot-pattern"
import { usePatients } from "@/lib/api/hooks"
import { useState } from "react"

const FEATURES = [
  {
    icon: RiVoiceprintLine,
    title: "Voice & Text",
    description: "Natural voice calls or text-based chat with AI agent",
  },
  {
    icon: RiShieldCheckLine,
    title: "14-Point Check-in",
    description: "Structured health questionnaire with real-time capture",
  },
  {
    icon: RiBarChartBoxLine,
    title: "Live Dashboard",
    description: "Monitor responses, transcript, and call progress in real-time",
  },
  {
    icon: RiDatabase2Line,
    title: "Patient Memory",
    description: "DB-enriched context from prior calls and health history",
  },
]

export function PatientSetup() {
  const navigate = useNavigate()
  const { data: patients, isLoading, isError } = usePatients()
  const [showPatients, setShowPatients] = useState(false)

  function handleSelectPatient(patientId: string) {
    const callId = crypto.randomUUID().slice(0, 8)
    navigate({
      to: `/call/${callId}?patientId=${patientId}` as never,
    })
  }

  return (
    <div className="relative flex min-h-svh flex-col">
      {/* Top bar */}
      <div className="flex items-center justify-between border-b px-6 py-3">
        <div className="flex items-center gap-2.5">
          <div className="bg-primary/10 text-primary flex size-8 items-center justify-center rounded-lg">
            <RiHeartPulseLine className="size-4" />
          </div>
          <span className="text-sm font-semibold tracking-tight">CareCaller</span>
        </div>
        <ThemeToggle />
      </div>

      {!showPatients ? (
        <div className="flex flex-1 flex-col">
          {/* Hero section with dot pattern background */}
          <div className="relative flex flex-col items-center gap-6 px-4 pt-16 pb-12 text-center overflow-hidden">
            <DotPattern className="opacity-30 [mask-image:radial-gradient(400px_circle_at_center,white,transparent)]" />

            <BlurFade delay={0.1}>
              <Badge variant="secondary" className="gap-1.5 px-3 py-1 text-xs">
                <RiStethoscopeLine className="size-3" />
                AI-Powered Healthcare Calls
              </Badge>
            </BlurFade>

            <BlurFade delay={0.2}>
              <div className="flex flex-col items-center gap-3">
                <h1 className="max-w-2xl text-4xl font-bold tracking-tight sm:text-5xl">
                  Medication Refill{" "}
                  <span className="text-primary">Check-in Calls</span>
                  {" "}Made Intelligent
                </h1>
                <TypingAnimation
                  as="p"
                  className="text-muted-foreground max-w-lg text-balance text-lg"
                  words={[
                    "Conducts natural patient conversations over voice.",
                    "Captures structured health data in real-time.",
                    "Detects quality issues with AI-powered analysis.",
                    "Remembers patient history across calls.",
                  ]}
                  duration={40}
                  deleteSpeed={20}
                  pauseDelay={2000}
                  loop
                  showCursor
                  cursorStyle="line"
                />
              </div>
            </BlurFade>

            <BlurFade delay={0.35}>
              <div className="flex items-center gap-3 pt-2">
                <ShimmerButton
                  className="shadow-lg"
                  onClick={() => setShowPatients(true)}
                >
                  <span className="flex items-center gap-2 text-sm font-medium text-white">
                    <RiPhoneLine className="size-4" />
                    Start New Call
                    <RiArrowRightLine className="size-4" />
                  </span>
                </ShimmerButton>
              </div>
            </BlurFade>

            {/* Stats strip with number tickers */}
            <BlurFade delay={0.5}>
              <div className="mt-4 flex items-center gap-10">
                <div className="flex flex-col items-center gap-0.5">
                  <NumberTicker value={14} className="text-2xl font-bold tracking-tight" />
                  <span className="text-muted-foreground text-xs">Health Questions</span>
                </div>
                <div className="flex flex-col items-center gap-0.5">
                  <span className="text-2xl font-bold tracking-tight">~3 min</span>
                  <span className="text-muted-foreground text-xs">Avg Call Duration</span>
                </div>
                <div className="flex flex-col items-center gap-0.5">
                  <NumberTicker value={5} className="text-2xl font-bold tracking-tight" />
                  <span className="text-muted-foreground text-xs">Seeded Patients</span>
                </div>
              </div>
            </BlurFade>
          </div>

          <Separator />

          {/* Features grid with staggered blur fade */}
          <div className="mx-auto w-full max-w-4xl px-6 py-12">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {FEATURES.map((feature, i) => (
                <BlurFade key={feature.title} delay={0.6 + i * 0.1}>
                  <div className="group flex gap-4 rounded-xl border bg-card p-5 transition-colors hover:border-primary/20 hover:bg-primary/[0.02]">
                    <div className="bg-primary/10 text-primary flex size-10 shrink-0 items-center justify-center rounded-lg transition-colors group-hover:bg-primary/15">
                      <feature.icon className="size-5" />
                    </div>
                    <div className="flex flex-col gap-1">
                      <span className="text-sm font-medium">{feature.title}</span>
                      <span className="text-muted-foreground text-xs leading-relaxed">
                        {feature.description}
                      </span>
                    </div>
                  </div>
                </BlurFade>
              ))}
            </div>
          </div>

          {/* Footer */}
          <div className="mt-auto border-t px-6 py-4">
            <div className="text-muted-foreground flex items-center justify-between text-xs">
              <div className="flex items-center gap-4">
                <span className="flex items-center gap-1">
                  <RiVoiceprintLine className="size-3" />
                  LiveKit + Deepgram
                </span>
                <span className="flex items-center gap-1">
                  <RiTimeLine className="size-3" />
                  Groq LLM
                </span>
              </div>
              <span>CareCaller Hackathon 2026</span>
            </div>
          </div>
        </div>
      ) : (
        <div className="flex flex-1 flex-col items-center px-4 pt-12">
          <div className="flex w-full max-w-lg flex-col gap-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Button
                  variant="ghost"
                  size="icon-sm"
                  onClick={() => setShowPatients(false)}
                >
                  <RiArrowLeftLine className="size-4" />
                </Button>
                <div>
                  <h2 className="text-lg font-semibold">Select a Patient</h2>
                  <p className="text-muted-foreground text-sm">
                    Choose a patient to start the check-in call
                  </p>
                </div>
              </div>
            </div>

            <Separator />

            {isLoading && (
              <div className="flex flex-col gap-3">
                {Array.from({ length: 4 }).map((_, i) => (
                  <Skeleton key={i} className="h-20 w-full rounded-xl" />
                ))}
              </div>
            )}

            {isError && (
              <div className="flex flex-col items-center gap-3 py-12 text-center">
                <div className="bg-destructive/10 text-destructive flex size-12 items-center justify-center rounded-full">
                  <RiPhoneLine className="size-5" />
                </div>
                <div>
                  <p className="text-sm font-medium">Connection failed</p>
                  <p className="text-muted-foreground mt-1 text-xs">
                    Could not load patients. Is the API server running on :8004?
                  </p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => window.location.reload()}
                >
                  Retry
                </Button>
              </div>
            )}

            {patients && (
              <ScrollArea className="max-h-[420px]">
                <div className="flex flex-col gap-2">
                  {patients.map((patient) => (
                    <Card
                      key={patient.id}
                      size="sm"
                      className="group cursor-pointer border transition-all hover:border-primary/30 hover:bg-primary/[0.02] hover:shadow-sm"
                      onClick={() => handleSelectPatient(patient.id)}
                    >
                      <CardContent>
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <div className="bg-muted flex size-9 items-center justify-center rounded-full transition-colors group-hover:bg-primary/10">
                              <RiUserLine className="text-muted-foreground size-4 transition-colors group-hover:text-primary" />
                            </div>
                            <div className="flex flex-col gap-1">
                              <span className="text-sm font-medium">
                                {patient.name}
                              </span>
                              <div className="text-muted-foreground flex items-center gap-3 text-xs">
                                <span className="flex items-center gap-1">
                                  <RiCalendarLine className="size-3" />
                                  {patient.date_of_birth}
                                </span>
                                <span className="flex items-center gap-1">
                                  <RiMedicineBottleLine className="size-3" />
                                  {patient.medication}
                                </span>
                                <span className="flex items-center gap-1">
                                  <RiStoreLine className="size-3" />
                                  {patient.pharmacy}
                                </span>
                              </div>
                            </div>
                          </div>
                          <div className="text-muted-foreground transition-colors group-hover:text-primary">
                            <RiPhoneFill className="size-4" />
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </ScrollArea>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
