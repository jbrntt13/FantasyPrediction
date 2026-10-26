import { useState } from "react";
import { StatusBar } from "expo-status-bar";
import { SafeAreaView, StyleSheet } from "react-native";
import OddsScreen from "./src/screens/OddsScreen";
import MatchupDetailScreen from "./src/screens/MatchupDetailScreen";
import { Matchup } from "./src/api/odds";

export default function App() {
  const [selected, setSelected] = useState<{ matchup: Matchup; date: string } | null>(null);

  const handleSelect = (matchup: Matchup, date: string) => {
    setSelected({ matchup, date });
  };

  const handleBack = () => setSelected(null);

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar style="light" />
      {selected ? (
        <MatchupDetailScreen
          matchup={selected.matchup}
          dateLabel={selected.date}
          onBack={handleBack}
        />
      ) : (
        <OddsScreen onSelectMatchup={handleSelect} />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: "#020617",
  },
});
