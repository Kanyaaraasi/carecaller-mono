# Evaluation Criteria Mapping

How the CareCaller Voice Agent Simulator maps to the hackathon scoring criteria.

## Scoring Breakdown

| Criteria | Weight | What Judges Look For |
|---|---|---|
| Conversation Quality | 30% | Natural flow, appropriate responses, handles interruptions |
| Response Accuracy | 30% | Correctly captures all 14 questionnaire answers |
| Edge Case Handling | 20% | Pricing questions, reschedules, opt-outs, escalations |
| Technical Implementation | 10% | Code quality, architecture, documentation |
| Demo & Presentation | 10% | Live demo of agent handling a simulated call |

## How Our UI Addresses Each

### Conversation Quality (30%)

**What the judges see:** The phone UI on the left pane shows a real-time chat-style transcript with agent messages (left) and patient messages (right). It looks and feels like a real call.

**Key features:**
- Chat bubbles with timestamps for natural conversation feel
- Typing/connecting indicators show the agent is "thinking"
- Voice waveform visualizer pulses during active call
- Mute toggle for realistic call control

**Demo tip:** Collapse the inspector (click the gear icon) during this part. Full-screen phone mode makes it feel like a product, not a dev tool.

### Response Accuracy (30%)

**What the judges see:** The Inspector's Responses tab shows all 14 questions with real-time status updates as answers are captured.

**Key features:**
- Live checklist: pending (circle) → asking (spinner) → answered (checkmark)
- Each answered question shows the captured text
- Progress bar at the bottom shows completion percentage
- Captured response chips appear inline in the transcript ("Q3 captured")

**Demo tip:** Open the inspector to the Responses tab. As the call progresses, judges can watch answers fill in live. At the end, switch to the Summary page to show the structured table.

### Edge Case Handling (20%)

**What the judges see:** The system handles various patient scenarios — opt-outs, wrong numbers, escalations, pricing questions — gracefully.

**Key features:**
- Scenarios are baked into the patient data from the backend
- Different patients trigger different conversation paths
- Call outcomes reflect the scenario: completed, opted_out, escalated, wrong_number, etc.
- Summary page shows the correct outcome badge

**Demo tip:** Have 2-3 patients pre-loaded with different scenarios. Demo the happy path first, then show an edge case (e.g., patient opts out, wrong number). The patient picker on the landing page makes switching fast.

### Technical Implementation (10%)

**What the judges see:** Clean architecture, proper separation of concerns, type safety.

**Key features:**
- API Log tab in the inspector shows every request/response with status codes and latency
- Clean API contract (see `docs/api-contract.md`) — backend dev can build against it independently
- Zustand for client state, React Query for server state, nuqs for URL state — each tool for its strength
- Full TypeScript, no `any` types in the API layer
- 24 shadcn components used consistently

**Demo tip:** Open the API Log tab briefly to show the clean request/response flow. Mention the docs folder and API contract.

### Demo & Presentation (10%)

**What the judges see:** A polished, presentation-ready interface.

**Key features:**
- Phone UI is demo-ready out of the box — looks like a real product
- Inspector is retractable — collapse it for presentation mode, open it for technical deep-dive
- Dark mode toggle for presentation room lighting
- Patient picker makes it easy to switch between demo scenarios
- Summary page provides a clean wrap-up after each call

**Demo tip:** Start with inspector collapsed (phone only). Walk through a call. Then reveal the inspector to show the engineering. End on the summary page.

## Suggested Demo Script (5 minutes)

1. **[0:00–0:30]** Landing page. Explain what CareCaller does. Click "Start New Call". Show patient list.
2. **[0:30–1:00]** Select a patient. Inspector collapsed. Show the phone UI connecting.
3. **[1:00–3:00]** Walk through the call. Agent asks questions, patient responds. Point out the natural flow.
4. **[3:00–3:30]** Open inspector. Show Responses tab filling in live. Show a captured chip in the transcript.
5. **[3:30–4:00]** End the call. Show Summary page — outcome badge, completeness score, structured responses table.
6. **[4:00–4:30]** Quick demo of an edge case — select a different patient, show opt-out or wrong number scenario.
7. **[4:30–5:00]** Flash the API Log tab. Mention the clean API contract and how backend/frontend were built independently. Wrap up.
