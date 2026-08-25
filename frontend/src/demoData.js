export const LANDING_STAGES = ["QUALIFIED", "DRAFTED", "APPROVED", "SENT", "MEETING_BOOKED"];

export const LANDING_LEADS = [
  {
    id: "d1",
    github_handle: "nivedita-labs",
    project: "token-shepherd",
    stage: "SENT",
    fit_score: 86,
  },
  {
    id: "d2",
    github_handle: "kai-okonkwo",
    project: "context-fuse",
    stage: "APPROVED",
    fit_score: 74,
  },
  {
    id: "d3",
    github_handle: "theo-voss",
    project: "rate-gate",
    stage: "MEETING_BOOKED",
    fit_score: 91,
  },
  {
    id: "d4",
    github_handle: "ada-quist",
    project: "window-saw",
    stage: "QUALIFIED",
    fit_score: 68,
  },
  {
    id: "d5",
    github_handle: "jonah-feld",
    project: "tool-loop",
    stage: "DRAFTED",
    fit_score: 79,
  },
  {
    id: "d6",
    github_handle: "priya-shah",
    project: "span-cache",
    stage: "SENT",
    fit_score: 81,
  },
];

export const FALLBACK_STATS = {
  raw_tokens: 30720,
  brief_tokens: 1043,
  saved_pct: 97,
};
