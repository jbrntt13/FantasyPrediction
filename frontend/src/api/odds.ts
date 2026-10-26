export interface Matchup {
  home_team: string;
  away_team: string;
  home_avg: number;
  away_avg: number;
  home_win_prob: number;
  away_win_prob: number;
  tie_prob: number;
  trials: number;
  home_team_url: string;
  away_team_url: string;
  home_current_score?: number;
  away_current_score?: number;
  daily_scores?: number[];
  home_today_score?: number;
  away_today_score?: number;
  home_today_remaining_proj?: number;
  away_today_remaining_proj?: number;
  home_today_total_proj?: number;
  away_today_total_proj?: number;
}

export interface OddsResponse {
  week_start: string;
  week_end: string;
  date: string;
  runtime_seconds?: number;
  matchups: Matchup[];
  proj_scores: Record<string, number>;
  win_probs: Record<string, number>;
  current_scores: Record<string, number>;
  is_live: boolean;
  // Demo mode fields (only present when server runs with DEMO_DATE set)
  demo_mode?: boolean;
  demo_speed?: number;
  game_fraction?: number;
}
// Switch between prod and local:
export const API_BASE_URL = "https://fantasyprediction.onrender.com";
//export const API_BASE_URL = "http://192.168.179.204:8000";
export async function getTodayOdds(): Promise<OddsResponse> {
  const response = await fetch(`${API_BASE_URL}/odds/weekly`);

  if (!response.ok) {
    const message = await response.text().catch(() => response.statusText);
    throw new Error(message || `Request failed with status ${response.status}`);
  }

  const data = (await response.json()) as OddsResponse;
  return data;
}

export async function demoReset(): Promise<void> {
  await fetch(`${API_BASE_URL}/demo/reset`, { method: "POST" });
}

export async function demoSkip(hours: number): Promise<void> {
  await fetch(`${API_BASE_URL}/demo/skip?hours=${hours}`, { method: "POST" });
}

export async function demoSetFraction(fraction: number): Promise<void> {
  await fetch(`${API_BASE_URL}/demo/set-fraction?fraction=${fraction}`, { method: "POST" });
}

export async function demoSetSpeed(speed: number): Promise<void> {
  await fetch(`${API_BASE_URL}/demo/set-speed?speed=${speed}`, { method: "POST" });
}

export async function getTodayDayOdds(): Promise<OddsResponse> {
  const response = await fetch(`${API_BASE_URL}/odds/today`);

  if (!response.ok) {
    const message = await response.text().catch(() => response.statusText);
    throw new Error(message || `Request failed with status ${response.status}`);
  }

  const data = (await response.json()) as OddsResponse;
  return data;
}

export async function getCustomOdds(
  team1: string,
  team2: string,
  trials = 20000,
): Promise<Matchup> {
  const params = new URLSearchParams({
    team1,
    team2,
    trials: trials.toString(),
  });

  const response = await fetch(`${API_BASE_URL}/odds/custom?${params.toString()}`);

  if (!response.ok) {
    const message = await response.text().catch(() => response.statusText);
    throw new Error(message || `Request failed with status ${response.status}`);
  }

  const data = (await response.json()) as Matchup;
  return data;
}
