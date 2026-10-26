import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import MatchupDetailCard from "../components/MatchupDetailCard";
import { Matchup } from "../api/odds";

type Props = {
  matchup: Matchup;
  dateLabel?: string;
  onBack: () => void;
};

export default function MatchupDetailScreen({ matchup, dateLabel, onBack }: Props) {
  return (
    <View style={styles.container}>
      <View style={styles.headerRow}>
        <TouchableOpacity onPress={onBack} hitSlop={12}>
          <Text style={styles.backText}>← Back</Text>
        </TouchableOpacity>
        <Text style={styles.heading}>Matchup Deep Dive</Text>
        <View style={{ width: 48 }} />
      </View>

      {dateLabel ? <Text style={styles.dateLabel}>{dateLabel}</Text> : null}

      <MatchupDetailCard matchup={matchup} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#020617",
    paddingHorizontal: 16,
    paddingTop: 12,
  },
  headerRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 8,
  },
  backText: {
    color: "#93c5fd",
    fontSize: 16,
    fontWeight: "700",
    minWidth: 48,
  },
  heading: {
    color: "#f8fafc",
    fontSize: 24,
    fontWeight: "800",
    textAlign: "center",
    flex: 1,
  },
  dateLabel: {
    color: "#94a3b8",
    fontSize: 14,
    marginBottom: 12,
    textAlign: "center",
  },
});
