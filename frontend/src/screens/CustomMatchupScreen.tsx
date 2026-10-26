import { useEffect, useState } from "react";
import {
  KeyboardAvoidingView,
  Linking,
  Platform,
  Share,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import MatchupDetailCard from "../components/MatchupDetailCard";
import { API_BASE_URL, Matchup, getCustomOdds } from "../api/odds";

type Props = {
  onBack?: () => void;
};

export default function CustomMatchupScreen({ onBack }: Props) {
  const [team1, setTeam1] = useState("");
  const [team2, setTeam2] = useState("");
  const [trials, setTrials] = useState("20000");
  const [result, setResult] = useState<Matchup | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Bonus: parse initial deep link to prefill and auto-fetch
  useEffect(() => {
    const hydrateFromLink = async () => {
      const url = await Linking.getInitialURL();
      if (!url) return;
      try {
        const parsed = new URL(url);
        const t1 = parsed.searchParams.get("team1");
        const t2 = parsed.searchParams.get("team2");
        const tr = parsed.searchParams.get("trials");
        if (t1) setTeam1(t1);
        if (t2) setTeam2(t2);
        if (tr) setTrials(tr);
        if (t1 && t2) {
          handleSubmit(t1, t2, tr ? parseInt(tr, 10) : undefined);
        }
      } catch {
        // ignore malformed URLs
      }
    };
    hydrateFromLink();
  }, []);

  const handleSubmit = async (t1?: string, t2?: string, tr?: number) => {
    const teamA = (t1 ?? team1).trim();
    const teamB = (t2 ?? team2).trim();
    const trialCount = tr ?? (parseInt(trials, 10) || 20000);

    if (!teamA || !teamB) {
      setError("Enter both team names");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const data = await getCustomOdds(teamA, teamB, trialCount);
      setResult(data);
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : "Failed to fetch matchup");
    } finally {
      setLoading(false);
    }
  };

  const shareLink = async () => {
    const teamA = team1.trim();
    const teamB = team2.trim();
    if (!teamA || !teamB) return;
    const url = `${API_BASE_URL}/odds/custom?team1=${encodeURIComponent(teamA)}&team2=${encodeURIComponent(teamB)}&trials=${trials}`;
    await Share.share({ message: url });
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <View style={styles.headerRow}>
        {onBack ? (
          <TouchableOpacity onPress={onBack} hitSlop={12}>
            <Text style={styles.backText}>← Back</Text>
          </TouchableOpacity>
        ) : (
          <View style={{ width: 48 }} />
        )}
        <Text style={styles.heading}>Custom Matchup</Text>
        <View style={{ width: 48 }} />
      </View>

      <Text style={styles.subhead}>Compare any two fantasy teams</Text>

      <View style={styles.formRow}>
        <TextInput
          style={styles.input}
          placeholder="Team 1"
          placeholderTextColor="#64748b"
          value={team1}
          onChangeText={setTeam1}
          autoCapitalize="words"
        />
        <TextInput
          style={styles.input}
          placeholder="Team 2"
          placeholderTextColor="#64748b"
          value={team2}
          onChangeText={setTeam2}
          autoCapitalize="words"
        />
        <TextInput
          style={styles.input}
          placeholder="Trials (optional)"
          placeholderTextColor="#64748b"
          value={trials}
          onChangeText={setTrials}
          keyboardType="numeric"
        />
        <TouchableOpacity
          style={[styles.button, loading ? styles.buttonDisabled : null]}
          onPress={() => handleSubmit()}
          disabled={loading}
          activeOpacity={0.85}
        >
          <Text style={styles.buttonText}>{loading ? "Running..." : "Run Simulation"}</Text>
        </TouchableOpacity>
      </View>

      {error ? <Text style={styles.error}>{error}</Text> : null}

      {result ? (
        <>
          <View style={styles.shareRow}>
            <TouchableOpacity style={styles.shareBtn} onPress={shareLink}>
              <Text style={styles.shareText}>Share this matchup link</Text>
            </TouchableOpacity>
          </View>
          <MatchupDetailCard matchup={result} />
        </>
      ) : null}
    </KeyboardAvoidingView>
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
  subhead: {
    color: "#94a3b8",
    fontSize: 14,
    marginBottom: 12,
    textAlign: "center",
  },
  formRow: {
    gap: 8,
    marginBottom: 12,
  },
  input: {
    backgroundColor: "#0b1224",
    borderColor: "#1f2937",
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    color: "#e5e7eb",
    fontSize: 15,
  },
  button: {
    backgroundColor: "#2563eb",
    paddingVertical: 12,
    borderRadius: 10,
    alignItems: "center",
  },
  buttonDisabled: {
    opacity: 0.7,
  },
  buttonText: {
    color: "#f8fafc",
    fontSize: 16,
    fontWeight: "700",
  },
  error: {
    color: "#fca5a5",
    marginBottom: 8,
  },
  shareRow: {
    marginBottom: 10,
    alignItems: "flex-end",
  },
  shareBtn: {
    paddingVertical: 8,
    paddingHorizontal: 10,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#1d4ed8",
    backgroundColor: "#0f172a",
  },
  shareText: {
    color: "#93c5fd",
    fontSize: 14,
    fontWeight: "600",
  },
});
