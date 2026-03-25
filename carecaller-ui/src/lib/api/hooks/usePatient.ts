import { useQuery } from "@tanstack/react-query"
import { apiClient } from "../client"
import { ENDPOINTS } from "../endpoints"
import type { Patient } from "../types"

export function usePatient(patientId: string) {
  return useQuery({
    queryKey: ["patient", patientId],
    queryFn: async () => {
      const { data } = await apiClient.get<Patient>(
        ENDPOINTS.patient(patientId),
      )
      return data
    },
    enabled: !!patientId,
  })
}
