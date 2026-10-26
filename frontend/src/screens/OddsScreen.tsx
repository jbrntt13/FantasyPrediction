import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  FlatList,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import MatchupCard from "../components/MatchupCard";
import {
  Matchup,
  OddsResponse,
  getTodayOdds,
  getTodayDayOdds,
  demoReset,
  demoSetFraction,
  demoSetSpeed,
} from "../api/odds";

type Props = {
  onSelectMatchup?: (matchup: Matchup, date: string) => void;
};

const SPEEDS = [1, 3, 10, 60] as const;
const THUMB_R = 7; // thumb radius in px

const getCurrentWeekLabel = () => {
  const today = new Date();
  const day = today.getDay();
  const diffToMonday = (day + 6) % 7;
  const monday = new Date(today);
  monday.setDate(today.getDate() - diffToMonday);
  const sunday = new Date(monday);
  sunday.setDate(monday.getDate() + 6);
  const fmt = (d: Date) =>
    d.toLocaleDateString("en-US", { month: "2-digit", day: "2-digit" });
  return `Weekly Matchup of ${fmt(monday)}-${fmt(sunday)}`;
};

// ── Demo toolbar ──────────────────────────────────────────────────────────────

type DemoToolbarProps = {
  serverFraction: number;
  serverSpeed: number;
  onRefresh: () => void;
};

function DemoToolbar({ serverFraction, serverSpeed, onRefresh }: DemoToolbarProps) {
  // Local fraction drives the scrub bar visually while dragging.
  // null means "use serverFraction".
  const [localFraction, setLocalFraction] = useState<number | null>(null);
  const [activeSpeed, setActiveSpeed] = useState(serverSpeed);
  const [busy, setBusy] = useState(false);
  const barWidth = useRef(0);
  const throttleTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Keep activeSpeed in sync when server responds with a new value
  useEffect(() => {
    setActiveSpeed(serverSpeed);
  }, [serverSpeed]);

  const displayFraction = localFraction ?? serverFraction;
  const pct = Math.round(displayFraction * 100);
  const statusLabel =
    pct <= 0 ? "Pre-Game" : pct >= 99 ? "Final" : `Live  ${pct}%`;

  // ── Scrub bar ─────────────────────────────────────────────────────────────

  const fractionFromTouch = (locationX: number) =>
    Math.max(0, Math.min(1, locationX / barWidth.current));

  const sendFraction = useCallback(
    (frac: number) => {
      if (throttleTimer.current) clearTimeout(throttleTimer.current);
      throttleTimer.current = setTimeout(async () => {
        await demoSetFraction(frac);
        onRefresh();
      }, 80); // throttle to ~12 fps while dragging
    },
    [onRefresh],
  );

  const scrubResponder = useMemo(
    () => ({
      onStartShouldSetResponder: () => true,
      onMoveShouldSetResponder: () => true,
      onResponderGrant: (e: any) => {
        const frac = fractionFromTouch(e.nativeEvent.locationX);
        setLocalFraction(frac);
        sendFraction(frac);
      },
      onResponderMove: (e: any) => {
        const frac = fractionFromTouch(e.nativeEvent.locationX);
        setLocalFraction(frac);
        sendFraction(frac);
      },
      onResponderRelease: async (e: any) => {
        if (throttleTimer.current) clearTimeout(throttleTimer.current);
        const frac = fractionFromTouch(e.nativeEvent.locationX);
        setLocalFraction(null); // let server value take over
        await demoSetFraction(frac);
        onRefresh();
      },
    }),
    [sendFraction, onRefresh],
  );

  // ── Speed buttons ─────────────────────────────────────────────────────────

  const handleSpeedPress = useCallback(
    async (speed: number) => {
      if (busy) return;
      setBusy(true);
      setActiveSpeed(speed);
      try {
        await demoSetSpeed(speed);
        onRefresh();
      } finally {
        setBusy(false);
      }
    },
    [busy, onRefresh],
  );

  // ── Quick actions ─────────────────────────────────────────────────────────

  const handleReset = useCallback(async () => {
    if (busy) return;
    setBusy(true);
    try {
      await demoReset();
      setLocalFraction(0);
      onRefresh();
    } finally {
      setBusy(false);
      setLocalFraction(null);
    }
  }, [busy, onRefresh]);

  const thumbLeft = barWidth.current
    ? barWidth.current * displayFraction - THUMB_R
    : 0;

  return (
    <View style={tb.bar}>
      {/* Row 1: label + status */}
      <View style={tb.row}>
        <View style={tb.tag}>
          <Text style={tb.tagText}>DEMO</Text>
        </View>
        <Text style={tb.status}>{statusLabel}</Text>
      </View>

      {/* Row 2: scrub bar */}
      <View
        style={tb.scrubArea}
        onLayout={(e) => {
          barWidth.current = e.nativeEvent.layout.width;
        }}
        {...scrubResponder}
      >
        <View style={tb.track}>
          <View style={[tb.fill, { width: `${pct}%` as any }]} />
        </View>
        {barWidth.current > 0 && (
          <View style={[tb.thumb, { left: thumbLeft }]} />
        )}
      </View>

      {/* Row 3: speed + reset */}
      <View style={tb.row}>
        <View style={tb.speedGroup}>
          {SPEEDS.map((s) => (
            <TouchableOpacity
              key={s}
              style={[tb.speedBtn, activeSpeed === s && tb.speedBtnActive]}
              onPress={() => handleSpeedPress(s)}
              disabled={busy}
            >
              <Text
                style={[tb.speedText, activeSpeed === s && tb.speedTextActive]}
              >
                {s}x
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        <TouchableOpacity
          style={[tb.resetBtn, busy && tb.disabled]}
          onPress={handleReset}
          disabled={busy}
        >
          <Text style={tb.resetText}>⏮  Reset</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

// ── Main screen ───────────────────────────────────────────────────────────────

export default function OddsScreen({ onSelectMatchup }: Props) {
  const [data, setData] = useState<OddsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"week" | "day">("week");
  const weekLabel = useMemo(() => getCurrentWeekLabel(), []);
  const isMountedRef = useRef(true);

  const fetchOdds = useCallback(async (showLoader = true) => {
    try {
      if (showLoader) setLoading(true);
      const response = viewMode === "day" ? await getTodayDayOdds() : await getTodayOdds();
      if (!isMountedRef.current) return;
      setData(response);
      setError(null);
    } catch (err) {
      if (!isMountedRef.current) return;
      setError(err instanceof Error ? err.message : "Failed to fetch odds");
    } finally {
      if (isMountedRef.current) setLoading(false);
    }
  }, [viewMode]);

  const pollInterval = Math.max(1000, Math.round(15_000 / (data?.demo_speed ?? 1)));

  useEffect(() => {
    isMountedRef.current = true;
    fetchOdds();
    const id = setInterval(() => fetchOdds(false), pollInterval);
    return () => {
      isMountedRef.current = false;
      clearInterval(id);
    };
  }, [fetchOdds, viewMode, pollInterval]);

  const handleDemoAction = useCallback(() => {
    fetchOdds(false);
  }, [fetchOdds]);

  const heading =
    data?.demo_mode && viewMode === "day"
      ? `Daily Matchup of ${data.date}`
      : weekLabel;

  return (
    <View style={styles.container}>
      <Text style={styles.heading}>{heading}</Text>

      {data?.demo_mode && (
        <DemoToolbar
          serverFraction={data.game_fraction ?? 0}
          serverSpeed={data.demo_speed ?? 1}
          onRefresh={handleDemoAction}
        />
      )}

      {data?.demo_mode && (
        <View style={vt.row}>
          {(["week", "day"] as const).map((mode) => (
            <TouchableOpacity
              key={mode}
              style={[vt.btn, viewMode === mode && vt.btnActive]}
              onPress={() => setViewMode(mode)}
            >
              <Text style={[vt.text, viewMode === mode && vt.textActive]}>
                {mode === "week" ? "Week" : "Day"}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      )}

      {loading && <Text style={styles.status}>Loading…</Text>}

      {!loading && error && (
        <Text style={[styles.status, styles.error]}>
          Error loading odds: {error}
        </Text>
      )}

      {!loading && data && (
        <>
          <Text style={styles.dateLabel}>{data.date}</Text>
          <FlatList
            data={data.matchups}
            keyExtractor={(item, index) =>
              `${item.home_team}-${item.away_team}-${index}`
            }
            renderItem={({ item }) => (
              <TouchableOpacity
                style={styles.cardWrapper}
                activeOpacity={0.8}
                onPress={() => onSelectMatchup?.(item, data.date)}
              >
                <MatchupCard
                  matchup={item}
                  isLive={data.is_live}
                  currentScores={data.current_scores}
                  projScores={data.proj_scores}
                  winProbs={data.win_probs}
                />
              </TouchableOpacity>
            )}
            contentContainerStyle={styles.listContent}
            showsVerticalScrollIndicator={false}
          />
        </>
      )}
    </View>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#020617",
    paddingHorizontal: 16,
    paddingTop: 12,
  },
  heading: {
    color: "#f8fafc",
    fontSize: 24,
    fontWeight: "800",
    marginBottom: 8,
    textAlign: "center",
  },
  status: { color: "#cbd5e1", fontSize: 16, marginTop: 12 },
  error: { color: "#fca5a5" },
  dateLabel: { color: "#94a3b8", fontSize: 14, marginBottom: 12 },
  listContent: { paddingBottom: 24 },
  cardWrapper: { flex: 1, paddingHorizontal: 6, paddingBottom: 12 },
});

const tb = StyleSheet.create({
  bar: {
    backgroundColor: "#0a1628",
    borderWidth: 1,
    borderColor: "#1e3a5f",
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    marginBottom: 10,
    gap: 10,
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  tag: {
    backgroundColor: "#1d4ed8",
    borderRadius: 4,
    paddingHorizontal: 7,
    paddingVertical: 2,
  },
  tagText: {
    color: "#bfdbfe",
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 0.8,
  },
  status: {
    color: "#93c5fd",
    fontSize: 13,
    fontWeight: "600",
  },
  // Scrub bar
  scrubArea: {
    height: 28,
    justifyContent: "center",
  },
  track: {
    height: 6,
    backgroundColor: "#1e3a5f",
    borderRadius: 3,
    overflow: "hidden",
  },
  fill: {
    height: "100%",
    backgroundColor: "#3b82f6",
    borderRadius: 3,
  },
  thumb: {
    position: "absolute",
    width: THUMB_R * 2,
    height: THUMB_R * 2,
    borderRadius: THUMB_R,
    backgroundColor: "#93c5fd",
    top: (28 - THUMB_R * 2) / 2,
    // left is set dynamically
  },
  // Speed buttons
  speedGroup: {
    flexDirection: "row",
    gap: 5,
    flex: 1,
  },
  speedBtn: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 6,
    backgroundColor: "#1e3a5f",
  },
  speedBtnActive: {
    backgroundColor: "#1d4ed8",
  },
  speedText: {
    color: "#64748b",
    fontSize: 12,
    fontWeight: "600",
  },
  speedTextActive: {
    color: "#bfdbfe",
  },
  resetBtn: {
    paddingHorizontal: 12,
    paddingVertical: 5,
    borderRadius: 6,
    backgroundColor: "#1e3a5f",
  },
  resetText: {
    color: "#93c5fd",
    fontSize: 12,
    fontWeight: "600",
  },
  disabled: {
    opacity: 0.4,
  },
});

const vt = StyleSheet.create({
  row: {
    flexDirection: "row",
    gap: 5,
    marginBottom: 10,
  },
  btn: {
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 6,
    backgroundColor: "#1e3a5f",
  },
  btnActive: {
    backgroundColor: "#1d4ed8",
  },
  text: {
    color: "#64748b",
    fontSize: 13,
    fontWeight: "600",
  },
  textActive: {
    color: "#bfdbfe",
  },
});
