import { useEffect, useRef, useState } from "react";
import {
  Animated,
  Easing,
  LayoutChangeEvent,
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
} from "react-native";
import { Matchup } from "../api/odds";
import { NeedleGauge } from "../components/Speedometer";
import { StackedProjectionBar } from "./StackedProjectionBar";

type Props = {
  matchup: Matchup;
  isLive?: boolean;
  currentScores?: Record<string, number>;
  projScores?: Record<string, number>;
  winProbs?: Record<string, number>;
};

const formatPercent = (value: number) => `${(value * 100).toFixed(1)}%`;

export default function MatchupCard({
  matchup,
  isLive = false,
  currentScores,
  projScores,
  winProbs,
}: Props) {
  const [cardWidth, setCardWidth] = useState(0);
  const [expanded, setExpanded] = useState(false);
  const livePulse = useRef(new Animated.Value(0)).current;
  const initialScoresRef = useRef<{
    home: number;
    away: number;
  } | undefined>(undefined);
  const initialWinProbRef = useRef<{
    home: number;
    away: number;
  } | undefined>(undefined);

  const handleLayout = (event: LayoutChangeEvent) => {
    const width = Math.round(event.nativeEvent.layout.width);
    if (width !== cardWidth) {
      setCardWidth(width);
    }
  };

  const isResolved =
    matchup.home_win_prob >= 0.999 || matchup.away_win_prob >= 0.999;
  const showLiveIndicator = isLive && !isResolved;

  const baseHomeScore =
    projScores?.[matchup.home_team] ?? matchup.home_avg ?? 0;
  const baseAwayScore =
    projScores?.[matchup.away_team] ?? matchup.away_avg ?? 0;

  // default to provided win_probs or 50/50 if missing
  const baseHomeProb =
    typeof winProbs?.[matchup.home_team] === "number"
      ? winProbs[matchup.home_team]
      : typeof matchup.home_win_prob === "number"
        ? matchup.home_win_prob
        : 0.5;
  const baseAwayProb =
    typeof winProbs?.[matchup.away_team] === "number"
      ? winProbs[matchup.away_team]
      : typeof matchup.away_win_prob === "number"
        ? matchup.away_win_prob
        : 0.5;

  if (!initialScoresRef.current) {
    initialScoresRef.current = {
      home: baseHomeScore,
      away: baseAwayScore,
    };
  }

  if (!initialWinProbRef.current) {
    initialWinProbRef.current = {
      home: baseHomeProb,
      away: baseAwayProb,
    };
  }

  const awayCurrentScore =
    isLive && currentScores?.[matchup.away_team] != null
      ? currentScores[matchup.away_team]
      : initialScoresRef.current.away;
  const homeCurrentScore =
    isLive && currentScores?.[matchup.home_team] != null
      ? currentScores[matchup.home_team]
      : initialScoresRef.current.home;

  const awayScoreDelta =
    isLive ? awayCurrentScore - initialScoresRef.current.away : null;
  const homeScoreDelta =
    isLive ? homeCurrentScore - initialScoresRef.current.home : null;

  const awayScoreDisplayDelta = matchup.away_avg - initialScoresRef.current.away;
  const homeScoreDisplayDelta = matchup.home_avg - initialScoresRef.current.home;

  const awayWinProbDisplayDelta =
    matchup.away_win_prob - initialWinProbRef.current.away;
  const homeWinProbDisplayDelta =
    matchup.home_win_prob - initialWinProbRef.current.home;

  const formatDelta = (value: number | null | undefined, digits = 1) => {
    if (value == null) return "";
    const display = value >= 0 ? `+${value.toFixed(digits)}` : value.toFixed(digits);
    return ` (${display})`;
  };
  const formatScoreDelta = (value: number) =>
    value >= 0 ? `+${value.toFixed(1)}` : value.toFixed(1);

  const awayApiScore = matchup.away_current_score;
  const homeApiScore = matchup.home_current_score;
  const awayApiProj = projScores?.[matchup.away_team] ?? matchup.away_avg;
  const homeApiProj = projScores?.[matchup.home_team] ?? matchup.home_avg;
  const awayApiWinProb = winProbs?.[matchup.away_team] ?? matchup.away_win_prob;
  const homeApiWinProb = winProbs?.[matchup.home_team] ?? matchup.home_win_prob;
  const awayCurrentMap = currentScores?.[matchup.away_team];
  const homeCurrentMap = currentScores?.[matchup.home_team];
  const dailyScoreDisplay = Array.isArray(matchup.daily_scores)
    ? matchup.daily_scores.map((n) => n.toFixed(1)).join(", ")
    : null;
  const awayTodayTotalProj =
    matchup.away_today_total_proj ??
    (matchup.away_today_score ?? 0) + (matchup.away_today_remaining_proj ?? 0);
  const homeTodayTotalProj =
    matchup.home_today_total_proj ??
    (matchup.home_today_score ?? 0) + (matchup.home_today_remaining_proj ?? 0);
  const maxBarScale = Math.max(
    awayApiProj ?? 0,
    homeApiProj ?? 0,
    awayTodayTotalProj,
    homeTodayTotalProj,
    awayApiScore ?? 0,
    homeApiScore ?? 0,
    1,
  );

  useEffect(() => {
    if (!showLiveIndicator) {
      livePulse.setValue(0);
      return;
    }

    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(livePulse, {
          toValue: 1,
          duration: 700,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
        Animated.timing(livePulse, {
          toValue: 0.2,
          duration: 700,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
        Animated.delay(1200),
      ]),
    );

    loop.start();

    return () => {
      loop.stop();
    };
  }, [livePulse, showLiveIndicator]);

  // Fill most of the padded area; cap to avoid overflow on larger screens.
  const contentWidth = cardWidth - 24; // padding: 12 left + 12 right
  const gaugeSize = contentWidth > 0
    ? Math.max(160, Math.min(260, contentWidth - 2 * 150)) // leave space for side graphs
    : undefined;

  return (
    <View style={styles.card} onLayout={handleLayout}>
      <View style={styles.titleRow}>
        <View style={styles.teamWithLive}>
          {showLiveIndicator && (
            <Animated.View style={[styles.liveDot, { opacity: livePulse }]} />
          )}
          <View>
            <Text style={styles.teamName}>{matchup.away_team}</Text>
          {currentScores?.[matchup.away_team] != null && (
            <Text style={styles.scoreText}>
              Current Total Points: {awayApiScore}
            </Text>
          )}
        </View>
      </View>
      <View style={styles.teamWithScore}>
        <Text style={styles.teamName}>{matchup.home_team}</Text>
        {currentScores?.[matchup.home_team] != null && (
          <Text style={[styles.scoreText, styles.scoreRight]}>
            Current Total Points: {homeApiScore}
          </Text>
        )}
      </View>
      </View>
      <View style={styles.gaugeRow}>
        <View style={[styles.graphBlock, styles.graphBlockTight]}>
          <Text style={styles.graphTitle}>{matchup.away_team}</Text>
          <StackedProjectionBar
            width={140}
            height={360}
            currentTotal={awayApiScore ?? 0}
            projectedTodayTotal={awayTodayTotalProj - 200}
            projectedWeekTotal={awayApiProj}
            maxScale={maxBarScale}
          />
        </View>

        <View style={[styles.gaugeContainer, { width: gaugeSize ?? 220 }]}>
          <NeedleGauge
            size={gaugeSize}
            value={matchup.home_win_prob}
            leftLabel={matchup.away_team}
            rightLabel={matchup.home_team}
            leftImageUrl={matchup.away_team_url}
            rightImageUrl={matchup.home_team_url}
          />
        </View>

        <View style={[styles.graphBlock, styles.graphBlockTight]}>
          <Text style={styles.graphTitle}>{matchup.home_team}</Text>
          <StackedProjectionBar
            width={140}
            height={360}
            currentTotal={homeApiScore ?? 0}
            projectedTodayTotal={homeTodayTotalProj}
            projectedWeekTotal={homeApiProj}
            maxScale={maxBarScale}
          />
        </View>
      </View>
      <View style={styles.avgRow}>
        <View style={styles.avgBlockLeft}>
          <Text style={styles.label}>Projected Score</Text>
          <Text style={styles.avgValue}>
            {matchup.away_avg.toFixed(1)}
            <Text
              style={[
                styles.deltaText,
                awayScoreDisplayDelta >= 0 ? styles.deltaPositive : styles.deltaNegative,
              ]}
            >
              ({formatScoreDelta(awayScoreDisplayDelta)})
            </Text>
          </Text>
        </View>
        <View style={styles.avgBlockRight}>
          <Text style={[styles.label, styles.labelRight]}>Projected Score</Text>
          <Text style={[styles.avgValue, styles.avgValueRight]}>
            {matchup.home_avg.toFixed(1)}
            <Text
              style={[
                styles.deltaText,
                homeScoreDisplayDelta >= 0 ? styles.deltaPositive : styles.deltaNegative,
              ]}
            >
              ({formatScoreDelta(homeScoreDisplayDelta)})
            </Text>
          </Text>
        </View>
      </View>

      <View style={styles.avgRow}>
        <View style={styles.avgBlockLeft}>
          <Text style={styles.label}>Win %</Text>
          <Text style={styles.avgValue}>
            {formatPercent(matchup.away_win_prob)}
            <Text
              style={[
                styles.deltaText,
                awayWinProbDisplayDelta >= 0
                  ? styles.deltaPositive
                  : styles.deltaNegative,
              ]}
            >
              {formatDelta(
                awayWinProbDisplayDelta * 100,
                1,
              )}
            </Text>
          </Text>
        </View>
        <View style={styles.avgBlockRight}>
          <Text style={[styles.label, styles.labelRight]}>Win %</Text>
          <Text style={[styles.avgValue, styles.avgValueRight]}>
            {formatPercent(matchup.home_win_prob)}
            <Text
              style={[
                styles.deltaText,
                homeWinProbDisplayDelta >= 0
                  ? styles.deltaPositive
                  : styles.deltaNegative,
              ]}
            >
              {formatDelta(
                homeWinProbDisplayDelta * 100,
                1,
              )}
            </Text>
          </Text>
        </View>
      </View>

      {matchup.tie_prob > 0 && (
        <Text style={styles.subtext}>
          Tie chance: {formatPercent(matchup.tie_prob)}
        </Text>
      )}

      <Text style={styles.subtext}>
        Simulated {matchup.trials.toLocaleString()} trials
      </Text>

      <TouchableOpacity 
        style={styles.expandButton}
        onPress={() => setExpanded((prev) => !prev)}
        activeOpacity={0.8}
      >
        <Text style={styles.expandButtonText}>
          {expanded ? "Hide details" : "Show details"}
        </Text>
      </TouchableOpacity>

      {expanded && (
        <View style={styles.expandBox}>
          <Text style={styles.expandTitle}>API Data</Text>
          <View style={styles.expandRow}>
            <Text style={styles.expandLabel}>Home projected</Text>
            <Text style={styles.expandValue}>{homeApiProj.toFixed(1)}</Text>
          </View>
          <View style={styles.expandRow}>
            <Text style={styles.expandLabel}>Away projected</Text>
            <Text style={styles.expandValue}>{awayApiProj.toFixed(1)}</Text>
          </View>
          <View style={styles.expandRow}>
            <Text style={styles.expandLabel}>Home win prob</Text>
            <Text style={styles.expandValue}>{formatPercent(homeApiWinProb)}</Text>
          </View>
          <View style={styles.expandRow}>
            <Text style={styles.expandLabel}>Away win prob</Text>
            <Text style={styles.expandValue}>{formatPercent(awayApiWinProb)}</Text>
          </View>
          <View style={styles.expandRow}>
            <Text style={styles.expandLabel}>Tie prob</Text>
            <Text style={styles.expandValue}>{formatPercent(matchup.tie_prob)}</Text>
          </View>
          <View style={styles.expandRow}>
            <Text style={styles.expandLabel}>Trials</Text>
            <Text style={styles.expandValue}>{matchup.trials.toLocaleString()}</Text> 
          </View>
          <View style={styles.expandRow}>
            <Text style={styles.expandLabel}>Home current score</Text>
            <Text style={styles.expandValue}>
              {homeApiScore != null ? homeApiScore : "—"}
            </Text>
          </View>
          <View style={styles.expandRow}>
            <Text style={styles.expandLabel}>Away current score</Text>
            <Text style={styles.expandValue}>
              {awayApiScore != null ? awayApiScore : "—"}
            </Text>
          </View>
          <View style={styles.expandRow}>
            <Text style={styles.expandLabel}>Home current (map)</Text>
            <Text style={styles.expandValue}>
              {homeCurrentMap != null ? homeCurrentMap : "—"}
            </Text>
          </View>
          <View style={styles.expandRow}>
            <Text style={styles.expandLabel}>Away current (map)</Text>
            <Text style={styles.expandValue}>
              {awayCurrentMap != null ? awayCurrentMap : "—"}
            </Text>
          </View>
          {dailyScoreDisplay ? (
            <View style={styles.expandRow}>
              <Text style={styles.expandLabel}>Daily scores</Text>
              <Text style={styles.expandValueSmall}>{dailyScoreDisplay}</Text>
            </View>
          ) : null}
          <View style={styles.expandRow}>
            <Text style={styles.expandLabel}>Home logo URL</Text>
            <Text style={styles.expandValueSmall}>{matchup.home_team_url}</Text>
          </View>
          <View style={styles.expandRow}>
            <Text style={styles.expandLabel}>Away logo URL</Text>
            <Text style={styles.expandValueSmall}>{matchup.away_team_url}</Text>
          </View>
          <View style={styles.expandRow}>
            <Text style={styles.expandLabel}>Raw API data</Text>
            <Text style={styles.expandValueSmall}>
              {JSON.stringify(matchup)}
            </Text>
          </View>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flex: 1,
    minWidth: 0,
    backgroundColor: "#0b1224",
    borderColor: "#1f2937",
    borderWidth: 1,
    borderRadius: 12,
    padding: 12,
    marginBottom: 0,
  },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
  },
  label: {
    color: "#9ca3af",
    fontSize: 14,
  },
  labelRight: {
    textAlign: "right",
  },
  titleRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 12,
  },
  teamWithLive: {
    flexDirection: "row",
    alignItems: "center",
  },
  teamWithScore: {
    alignItems: "flex-end",
  },
  liveDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: "#ef4444",
    marginRight: 6,
  },
  teamName: {
    color: "#e5e7eb",
    fontSize: 18,
    fontWeight: "700",
  },
  scoreText: {
    color: "#f97316",
    fontSize: 14,
    fontWeight: "700",
    marginTop: 2,
  },
  scoreRight: {
    textAlign: "right",
  },
  value: {
    color: "#f3f4f6",
    fontSize: 15,
    fontWeight: "600",
  },
  subtext: {
    color: "#9ca3af",
    fontSize: 13,
  },
  avgRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 8,
    marginTop: 4,
  },
  avgBlockLeft: {
    alignItems: "flex-start",
  },
  avgBlockRight: {
    alignItems: "flex-end",
  },
  avgValue: {
    color: "#f3f4f6",
    fontSize: 16,
    fontWeight: "700",
  },
  avgValueRight: {
    textAlign: "right",
  },
  deltaText: {
    fontSize: 13,
    fontWeight: "700",
  },
  deltaPositive: {
    color: "#10b981",
  },
  deltaNegative: {
    color: "#ef4444",
  },
  gaugeRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-evenly",
    paddingVertical: 12,
  },
  gaugeContainer: {
    alignItems: "center",
  },
  graphBlock: {
    alignItems: "center",
    borderRadius: 1,
    borderWidth: 1,
    borderColor: "#1f2937",
    paddingVertical: 8,
    backgroundColor: "#0f172a",
    width: 150,
  },
  graphBlockTight: {
    flexGrow: 0,
  },
  graphTitle: {
    color: "#bfdbfe",
    fontWeight: "800",
    marginBottom: 8,
  },
  expandButton: {
    marginTop: 8,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#1f2937",
    backgroundColor: "#0f172a",
    alignItems: "center",
  },
  expandButtonText: {
    color: "#bfdbfe",
    fontWeight: "700",
    fontSize: 14,
  },
  expandBox: {
    marginTop: 8,
    padding: 10,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#1f2937",
    backgroundColor: "#0b1224",
    gap: 6,
  },
  expandTitle: {
    color: "#f8fafc",
    fontWeight: "800",
    fontSize: 14,
    marginBottom: 4,
  },
  expandRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  expandLabel: {
    color: "#9ca3af",
    fontSize: 13,
  },
  expandValue: {
    color: "#e5e7eb",
    fontSize: 13,
    fontWeight: "700",
    textAlign: "right",
    maxWidth: "55%",
  },
  expandValueSmall: {
    color: "#cbd5e1",
    fontSize: 11,
    textAlign: "right",
    flex: 1,
    marginLeft: 10,
  },
});
