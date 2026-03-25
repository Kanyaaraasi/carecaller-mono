import { useMutation } from "@tanstack/react-query"
import { apiClient } from "../client"
import { ENDPOINTS } from "../endpoints"
import type { EndCallRequest, EndCallResponse } from "../types"

export function useEndCall() {
  return useMutation({
    mutationFn: async (req: EndCallRequest) => {
      const { data } = await apiClient.post<EndCallResponse>(
        ENDPOINTS.call.end(req.call_id),
        req,
      )
      return data
    },
  })
}
