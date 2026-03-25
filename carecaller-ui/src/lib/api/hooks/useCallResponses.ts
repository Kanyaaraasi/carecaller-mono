import { useQuery } from "@tanstack/react-query"
import { apiClient } from "../client"
import { ENDPOINTS } from "../endpoints"
import type { GetResponsesResponse } from "../types"

export function useCallResponses(callId: string, enabled: boolean) {
  return useQuery({
    queryKey: ["call-responses", callId],
    queryFn: async () => {
      const { data } = await apiClient.get<GetResponsesResponse>(
        ENDPOINTS.call.responses(callId),
      )
      return data
    },
    enabled,
    refetchInterval: enabled ? 2000 : false,
  })
}
