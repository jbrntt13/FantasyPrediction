import { useState } from "react";
import { LayoutChangeEvent, StyleSheet, Text, View } from "react-native";
import { Matchup } from "../api/odds";
import { NeedleGauge } from "./Speedometer";

type Props = {
  matchup: Matchup;
};

const formatPercent = (value: number) => `${(value * 100).toFixed(1)}%`;

export default function MatchupDetailCard({ matchup }: Props) {
  const [cardWidth, setCardWidth] = useState(0);

  const handleLayout = (event: LayoutChangeEvent) => {
    const width = Math.round(event.nativeEvent.layout.width);
    if (width !== cardWidth) {
      setCardWidth(width);
    }
  };

  const contentWidth = cardWidth - 32; // padding 16 left + right
  const gaugeSize =
    contentWidth > 0 ? Math.min(360, contentWidth) : undefined;

  const homeFavored = matchup.home_win_prob >= matchup.away_win_prob;
  const favoredTeam = homeFavored ? matchup.home_team : matchup.away_team;
  const spread = Math.abs(matchup.home_avg - matchup.away_avg).toFixed(1);

  return (
    <View style={styles.card} onLayout={handleLayout}>
      <View style={styles.header}>
        <Text style={styles.title}>
          {matchup.home_team} vs {matchup.away_team}
        </Text>
        <Text style={styles.favored}>{favoredTeam} favored</Text>
      </View>

      <NeedleGauge
        size={gaugeSize}
        value={matchup.home_win_prob}
        leftLabel={matchup.away_team}
        rightLabel={matchup.home_team}
      />

      <View style={styles.grid}>
        <View style={styles.statBlock}>
          <Text style={styles.label}>Expected score</Text>
          <Text style={styles.value}>
            {matchup.home_avg} · {matchup.away_avg}
          </Text>
        </View>

        <View style={styles.statBlock}>
          <Text style={styles.label}>Win probability</Text>
          <Text style={styles.value}>
            Home {formatPercent(matchup.home_win_prob)}
          </Text>
          <Text style={styles.subvalue}>
            Away {formatPercent(matchup.away_win_prob)}
          </Text>
        </View>

        <View style={styles.statBlock}>
          <Text style={styles.label}>Projected edge</Text>
          <Text style={styles.value}>
            {favoredTeam} by {spread}
          </Text>
        </View>

        <View style={styles.statBlock}>
          <Text style={styles.label}>Simulated</Text>
          <Text style={styles.value}>{matchup.trials.toLocaleString()}</Text>
          {matchup.tie_prob > 0 && (
            <Text style={styles.subvalue}>
              Tie {formatPercent(matchup.tie_prob)}
            </Text>
          )}
        </View>
      </View>
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
    borderRadius: 14,
    padding: 16,
  },
  header: {
    marginBottom: 8,
  },
  title: {
    color: "#e5e7eb",
    fontSize: 18,
    fontWeight: "800",
  },
  favored: {
    color: "#a5b4fc",
    fontSize: 13,
    marginTop: 2,
    fontWeight: "600",
  },
  grid: {
    marginTop: 8,
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "space-between",
  },
  statBlock: {
    width: "48%",
    marginBottom: 12,
    padding: 10,
    borderRadius: 10,
    backgroundColor: "#0f172a",
    borderWidth: 1,
    borderColor: "#1f2937",
  },
  label: {
    color: "#94a3b8",
    fontSize: 12,
    marginBottom: 4,
  },
  value: {
    color: "#f8fafc",
    fontSize: 15,
    fontWeight: "700",
  },
  subvalue: {
    color: "#cbd5e1",
    fontSize: 12,
    marginTop: 2,
  },
});
