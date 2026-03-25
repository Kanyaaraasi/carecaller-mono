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
} from "@remixicon/react"
import { ThemeToggle } from "@/components/ThemeToggle"
import { usePatients } from "@/lib/api/hooks"
import { useState } from "react"

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
    <div className="relative flex flex-1 flex-col items-center justify-center gap-8 px-4">
      <div className="absolute top-4 right-4">
        <ThemeToggle />
      </div>

      {!showPatients ? (
        <>
          <div className="flex flex-col items-center gap-3 text-center">
            <div className="bg-primary/10 text-primary flex size-14 items-center justify-center rounded-2xl">
              <RiHeartPulseLine className="size-7" />
            </div>
            <h1 className="text-3xl font-semibold tracking-tight">
              CareCaller
            </h1>
            <p className="text-muted-foreground max-w-sm text-balance">
              AI Voice Agent Simulator for medication refill check-in calls.
            </p>
          </div>

          <div className="text-muted-foreground flex items-center gap-6 text-sm">
            <span className="flex items-center gap-1.5">
              <RiPhoneLine className="size-4" />
              14 health questions
            </span>
            <span className="text-border">|</span>
            <span className="flex items-center gap-1.5">
              <RiShieldCheckLine className="size-4" />
              Real-time capture
            </span>
          </div>

          <Button size="lg" onClick={() => setShowPatients(true)}>
            <RiPhoneLine className="size-4" />
            Start New Call
          </Button>
        </>
      ) : (
        <div className="flex w-full max-w-lg flex-col gap-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold">Select a Patient</h2>
              <p className="text-muted-foreground text-sm">
                Choose who to call
              </p>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowPatients(false)}
            >
              Back
            </Button>
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
            <div className="text-muted-foreground py-8 text-center text-sm">
              Failed to load patients. Is the API running?
            </div>
          )}

          {patients && (
            <ScrollArea className="max-h-[400px]">
              <div className="flex flex-col gap-2">
                {patients.map((patient) => (
                  <Card
                    key={patient.id}
                    size="sm"
                    className="cursor-pointer transition-colors hover:bg-muted/50"
                    onClick={() => handleSelectPatient(patient.id)}
                  >
                    <CardContent>
                      <div className="flex items-center justify-between">
                        <div className="flex flex-col gap-1.5">
                          <div className="flex items-center gap-2">
                            <RiUserLine className="text-muted-foreground size-4" />
                            <span className="font-medium">{patient.name}</span>
                          </div>
                          <div className="text-muted-foreground flex items-center gap-4 text-xs">
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
                        <Button variant="ghost" size="icon-sm">
                          <RiPhoneFill className="text-primary size-4" />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </ScrollArea>
          )}
        </div>
      )}
    </div>
  )
}
