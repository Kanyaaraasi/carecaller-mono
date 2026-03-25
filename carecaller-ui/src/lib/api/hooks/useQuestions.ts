import { useQuery } from "@tanstack/react-query"
import { apiClient } from "../client"
import { ENDPOINTS } from "../endpoints"
import type { GetQuestionsResponse } from "../types"

export function useQuestions() {
  return useQuery({
    queryKey: ["questions"],
    queryFn: async () => {
      const { data } = await apiClient.get<GetQuestionsResponse>(
        ENDPOINTS.questions,
      )
      return data.questions
    },
  })
}
