import { useMutation } from "@tanstack/react-query"
import { apiClient } from "../client"
import { ENDPOINTS } from "../endpoints"
import type { StartVoiceCallRequest, StartVoiceCallResponse } from "../types"

export function useStartVoiceCall() {
  return useMutation({
    mutationFn: async (req: StartVoiceCallRequest) => {
      const { data } = await apiClient.post<StartVoiceCallResponse>(
        ENDPOINTS.call.startVoice,
        req,
      )
      return data
    },
  })
}
