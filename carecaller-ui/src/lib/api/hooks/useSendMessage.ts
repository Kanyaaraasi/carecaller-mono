import { useMutation } from "@tanstack/react-query"
import { apiClient } from "../client"
import { ENDPOINTS } from "../endpoints"
import type { SendMessageRequest, SendMessageResponse } from "../types"

export function useSendMessage() {
  return useMutation({
    mutationFn: async (req: SendMessageRequest) => {
      const { data } = await apiClient.post<SendMessageResponse>(
        ENDPOINTS.call.message(req.call_id),
        req,
      )
      return data
    },
  })
}
