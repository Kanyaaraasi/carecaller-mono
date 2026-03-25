import { useMutation } from "@tanstack/react-query"
import { apiClient } from "../client"
import { ENDPOINTS } from "../endpoints"
import type { StartCallRequest, StartCallResponse } from "../types"

export function useStartCall() {
  return useMutation({
    mutationFn: async (req: StartCallRequest) => {
      const { data } = await apiClient.post<StartCallResponse>(
        ENDPOINTS.call.start,
        req,
      )
      return data
    },
  })
}
