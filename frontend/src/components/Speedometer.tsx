import React, { useEffect } from "react";
import { View, Text, StyleSheet, ImageBackground } from "react-native";
import Animated, { useSharedValue, useAnimatedStyle, withTiming } from "react-native-reanimated";

type NeedleGaugeProps = {
  value: number;        // 0–1, probability of RIGHT team
  leftLabel?: string;
  rightLabel?: string;
  minAngle?: number;
  maxAngle?: number;
  duration?: number;
  size?: number;
  leftImageUrl?: string;   // unused: legacy prop kept for compatibility
  rightImageUrl?: string;  // unused: legacy prop kept for compatibility
};

export const NeedleGauge: React.FC<NeedleGaugeProps> = ({
  value,
  leftLabel = "Away",
  rightLabel = "Home",
  minAngle = -90,
  maxAngle = 90,
  duration = 1000,
  size = 220,
  leftImageUrl,
  rightImageUrl,
}) => {
  const dialSize = size;
  const needleLength = dialSize / 2 - 5;

  const angle = useSharedValue(minAngle);

  const clamped = Math.max(0, Math.min(1, value));
  const targetAngle = minAngle + (maxAngle - minAngle) * clamped;

  const favoredTeam = clamped >= 0.5 ? rightLabel : leftLabel;
  const favoredProb = clamped >= 0.5 ? clamped : 1 - clamped;
  const favoredPercent = favoredProb * 100;

  const confidenceLabel =
    favoredPercent >= 91
      ? "Very Likely"
      : favoredPercent >= 75
        ? "Likely"
        : favoredPercent >= 60
          ? "Leaning"
          : "Tossup";

  useEffect(() => {
    angle.value = withTiming(targetAngle, { duration });
  }, [targetAngle, clamped, duration]);

  // needle rotation
  const needleContainerStyle = useAnimatedStyle(() => ({
    transform: [{ rotate: `${angle.value}deg` }],
  }));

  const percent = (clamped * 100).toFixed(1);
  const winningTeam = favoredTeam;
  const displayedPercent =
    clamped >= 0.5 ? percent : (100 - parseFloat(percent)).toFixed(1);

  return (
    <View style={styles.container}>
      <Text style={styles.statusText}>
        {confidenceLabel} {favoredTeam}
      </Text>
      <View
        style={[
          styles.labelsRow,
          { maxWidth: dialSize + 60 },
        ]}
      >
        {/* you can put labels here again if you want */}
      </View>

      <View style={[styles.dialWrapper, { width: dialSize, height: dialSize / 2 }]}>
        <View style={[styles.semiClip, { width: dialSize, height: dialSize / 2 }]}>
          <ImageBackground
            source={require("../../assets/NEEDLEBACKGROUND.png")}
            style={[
              styles.dialBackground,
              { width: dialSize, height: dialSize, borderRadius: dialSize / 2 },
            ]}
            imageStyle={{
              borderRadius: dialSize / 2,
              alignSelf: "center",
              width: dialSize*1.2,
              transform: [{ translateY: -dialSize * 0.30 },{ translateX: -dialSize * 0.099 }], // shrink background image
              
              
            }}
            resizeMode="contain"
          >
           

            {/* Rotating container, centered in the circle */}
            <Animated.View
              style={[
                styles.needleContainer,
                { width: dialSize, height: dialSize },
                needleContainerStyle,
              ]}
            >
              {/* Needle whose base is at the center of the dial */}
              <View
                style={[
                  styles.needle,
                  { bottom: dialSize / 2, height: needleLength },
                ]}
              />
            </Animated.View>
          </ImageBackground>
        </View>
      </View>

      <View style={styles.percentRow}>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    alignItems: "center",
    paddingVertical: 6,
  },
  labelsRow: {
    width: "100%",
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 2,
  },
  statusText: {
    color: "#e5e7eb",
    fontSize: 14,
    fontWeight: "700",
    marginBottom: 4,
    textAlign: "center",
  },
  teamLabel: {
    color: "#e5e7eb",
    fontSize: 12,
  },
  dialWrapper: {
    alignItems: "center",
    justifyContent: "flex-end",
  },
  semiClip: {
    overflow: "hidden",
  },
  dialBackground: {
    backgroundColor: "#020617",
    borderWidth: 2,
    borderColor: "#374151",
    alignItems: "center",
    justifyContent: "center",
    overflow: "hidden", // important for clipping to the circle
  },

  // (sideBg / leftSide / rightSide no longer used but safe to keep or delete)
  sideBg: {
    position: "absolute",
    top: 0,
    bottom: 0,
    overflow: "hidden",
  },
  leftSide: { left: 0 },
  rightSide: { right: 0 },

  // This fills the whole circle; its center is the rotation pivot
  needleContainer: {
    position: "absolute",
  },

  // Base of the needle is at the circle center
  needle: {
    position: "absolute",
    alignSelf: "center",
    width: 3,
    backgroundColor: "#f97316",
    borderRadius: 9999,
  },

  percentRow: {
    marginTop: 2,
  },
  percentText: {
    color: "#f9fafb",
    fontSize: 14,
    fontWeight: "600",
  },
});
