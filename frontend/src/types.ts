export interface Summary {
  player_id: number;
  name: string;
  position: string;
  league: string;
  latest_season: number;
  age: number;
  latest_value_eur: number | null;
}

export interface Card {
  player_id: number;
  name: string;
  position: string;
  position_code: string;
  sub_position: string | null;
  league: string;
  club_id: number;
  club_name: string | null;
  season: number;
  age: number | null;
  minutes: number;
  goals: number;
  assists: number;
  market_value_eur: number | null;
}

export interface SeasonRow {
  season: number;
  age: number | null;
  league: string;
  club_id: number;
  club_name: string | null;
  appearances: number;
  minutes: number;
  goals: number;
  assists: number;
  goals_per90: number | null;
  assists_per90: number | null;
  yellow_cards: number;
  red_cards: number;
  market_value_eur: number | null;
}

export interface Trend {
  value_change_12m_pct: number | null;
  annual_growth_pct: number | null;
  peak_value_eur: number | null;
  peak_date: string | null;
  form_goals_p90: number | null;
  form_assists_p90: number | null;
}

export interface ValuePoint {
  date: string;
  value_eur: number;
}

export interface Profile extends Card {
  country: string | null;
  foot: string | null;
  height_cm: number | null;
  first_season: number;
  is_active: boolean;
  seasons: SeasonRow[];
  value_history: ValuePoint[];
  trend: Trend;
  percentiles: Record<string, number | null>;
  radar_labels: Record<string, string>;
}

export interface Factor {
  concept: string;
  effect_pct: number;
  effect_eur: number;
  log_effect: number;
}

export interface Forecast {
  for_season: number;
  forecast_eur: number;
  low_eur: number;
  high_eur: number;
  expected_change_pct: number | null;
  actual_value_eur: number | null;
}

export interface Valuation {
  player_id: number;
  season: number;
  age: number | null;
  value_date: string | null;
  market_value_eur: number;
  model_value_eur: number;
  low_eur: number;
  high_eur: number;
  gap_pct: number | null;
  market_within_range: boolean;
  in_sample: boolean;
  baseline_value_eur: number;
  factors: Factor[];
  forecast: Forecast;
  warnings: string[];
}

export interface RankRow {
  rank: number;
  player_id: number;
  name: string;
  position_code: string;
  position: string;
  sub_position: string | null;
  league: string;
  club_id: number;
  club_name: string | null;
  age: number | null;
  minutes: number;
  goals: number;
  assists: number;
  goals_per90: number | null;
  assists_per90: number | null;
  market_value_eur: number;
  model_value_eur: number;
  low_eur: number;
  high_eur: number;
  gap_pct: number | null;
  forecast_eur: number;
  forecast_change_pct: number | null;
  outside_range: "below" | "above" | null;
}

export interface Rankings {
  sort: string;
  label: string;
  season: number;
  total_matching: number;
  min_minutes: number;
  min_value_eur: number | null;
  max_value_eur: number | null;
  rows: RankRow[];
}

export type SimilarPlayer = Card & { distance: number; match_pct: number };
export interface Similar {
  in_pool: boolean;
  players: SimilarPlayer[];
}

export interface Teammates {
  total: number;
  players: Card[];
}

export type PathStep =
  | (Card & { type: "player" })
  | { type: "club"; club_id: number; club_name: string | null; season: number };

export interface Connection {
  separation: number | null;
  path: PathStep[];
}

export interface Overview {
  season: number;
  players_assessed: number;
  below_range: number;
  inside_range: number;
  above_range: number;
  median_gap_pct: number | null;
  total_market_value_eur: number | null;
}

export interface ModelPoint {
  season: number;
  date: string | null;
  market_value_eur: number | null;
  model_value_eur: number;
  low_eur: number;
  high_eur: number;
  in_sample: boolean;
}

export interface Meta {
  players: number;
  player_seasons: number;
  overview: Overview;
  typical_error_pct: number | null;
  max_season: number;
  first_season: number;
  test_from_season: number;
  leagues: Record<string, string>;
  positions: Record<string, string>;
  rankings: { id: string; label: string }[];
  has_club_names: boolean;
}

export interface ModelInfo {
  valuation: Record<string, number>;
  range: Record<string, number>;
  forecast: Record<string, number>;
  trained_before_season: number;
  data: {
    players: number;
    player_seasons: number;
    first_season: number;
    last_season: number;
    leagues: Record<string, string>;
  };
  global_importance: { concept: string; avg_effect_pct: number }[];
}
