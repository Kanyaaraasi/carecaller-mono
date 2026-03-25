import { useQuery } from "@tanstack/react-query"
import { apiClient } from "../client"
import { ENDPOINTS } from "../endpoints"
import type { GetPatientsResponse } from "../types"

export function usePatients() {
  return useQuery({
    queryKey: ["patients"],
    queryFn: async () => {
      const { data } = await apiClient.get<GetPatientsResponse>(
        ENDPOINTS.patients,
      )
      return data.patients
    },
  })
}
