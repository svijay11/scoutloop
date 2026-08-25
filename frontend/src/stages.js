export const ALL_STAGES = [
  "NEW",
  "RESEARCHED",
  "BRIEFED",
  "QUALIFIED",
  "DISQUALIFIED",
  "DRAFTED",
  "APPROVED",
  "SENT",
  "REPLIED",
  "MEETING_BOOKED",
  "NURTURE",
  "CLOSED_LOST",
  "UNSUBSCRIBED",
  "NEEDS_HUMAN_REVIEW",
];

export const FAIL_STAGES = new Set([
  "DISQUALIFIED",
  "CLOSED_LOST",
  "UNSUBSCRIBED",
  "NEEDS_HUMAN_REVIEW",
]);

export const PASS_STAGES = new Set(["QUALIFIED", "APPROVED", "SENT", "MEETING_BOOKED"]);
export const DRAFT_STAGES = new Set(["DRAFTED", "APPROVED", "SENT", "MEETING_BOOKED"]);

export function pillTone(stage) {
  if (FAIL_STAGES.has(stage)) return "fail";
  if (PASS_STAGES.has(stage)) return "pass";
  return "pending";
}

export function stageLabel(stage) {
  if (stage === "MEETING_BOOKED") return "MEETING";
  if (stage === "NEEDS_HUMAN_REVIEW") return "REVIEW";
  if (stage === "CLOSED_LOST") return "LOST";
  return stage;
}
