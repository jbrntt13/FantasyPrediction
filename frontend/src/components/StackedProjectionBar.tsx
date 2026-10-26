import React, { useMemo } from "react";
import { View } from "react-native";
import Svg, { Defs, Pattern, Line, Rect, G, Text as SvgText } from "react-native-svg";

type Props = {
  width?: number;
  height?: number;

  currentTotal: number;        // blue fill
  projectedTodayTotal: number; // current + expected remaining today (absolute)
  projectedWeekTotal: number;  // weekly projected line
  maxScale: number;            // dynamic max passed in

  showTodayLine?: boolean;
  showLabels?: boolean;

  // optional: make the top not feel cramped
  headroomPct?: number; // e.g. 0.08 for +8%
};

function clamp(n: number, min: number, max: number) {
  return Math.max(min, Math.min(max, n));
}

// optional “nice max” so your weekly line isn’t glued to the top
function niceCeil(n: number) {
  if (n <= 0) return 1;
  const pow = Math.pow(10, Math.floor(Math.log10(n)));
  const frac = n / pow;
  let niceFrac = 1;
  if (frac <= 1) niceFrac = 1;
  else if (frac <= 2) niceFrac = 2;
  else if (frac <= 2.5) niceFrac = 2.5;
  else if (frac <= 5) niceFrac = 5;
  else niceFrac = 10;
  return Math.ceil(niceFrac * pow);
}

export const StackedProjectionBar: React.FC<Props> = ({
  width = 120,
  height = 320,

  currentTotal,
  projectedTodayTotal,
  projectedWeekTotal,
  maxScale,

  showTodayLine = true,
  showLabels = true,
  headroomPct = 0.06,
}) => {
  const padding = 10; // inner padding
  const barX = padding;
  const barY = padding;
  const barW = width - padding * 2;
  const barH = height - padding * 2;

  const safeMax = useMemo(() => {
    const base = Math.max(1, maxScale);
    return niceCeil(base * (1 + headroomPct));
  }, [maxScale, headroomPct]);

  // sanitize + clamp
  const cur = clamp(currentTotal, 0, safeMax);
  const today = clamp(Math.max(projectedTodayTotal, cur), 0, safeMax);
  const week = clamp(projectedWeekTotal, 0, safeMax);

  const yFor = (value: number) => barY + barH - (value / safeMax) * barH;
  const hFor = (value: number) => (value / safeMax) * barH;

  const curTopY = yFor(cur);
  const curH = hFor(cur);

  const todayTopY = yFor(today);
  const todayH = hFor(today);

  const deltaH = Math.max(0, todayH - curH); // green portion height

  const weekY = yFor(week);

  return (
    <View style={{ width, height }}>
      <Svg width={width} height={height}>
        <Defs>
          {/* Hatch pattern for green projected area */}
          <Pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
            <Line x1="0" y1="8" x2="8" y2="0" stroke="rgba(0,160,90,0.9)" strokeWidth="2" />
          </Pattern>
        </Defs>

        {/* Container */}
        <Rect
          x={barX}
          y={barY}
          width={barW}
          height={barH}
          rx={10}
          ry={10}
          fill="transparent"
          stroke="rgba(20,70,140,0.9)"
          strokeWidth={3}
        />

        <G clipPath={undefined}>
          {/* Current (blue) */}
          <Rect
            x={barX}
            y={curTopY}
            width={barW}
            height={curH}
            fill="rgba(20,70,140,0.95)"
          />

          {/* Projected today delta (green hatch overlay between current and today) */}
          {deltaH > 0 && (
            <>
              <Rect
                x={barX}
                y={todayTopY}
                width={barW}
                height={deltaH}
                fill="rgba(0,160,90,0.18)"
              />
              <Rect
                x={barX}
                y={todayTopY}
                width={barW}
                height={deltaH}
                fill="url(#hatch)"
                opacity={0.6}
              />
            </>
          )}

          {/* Today projected line */}
          {showTodayLine && (
            <Line
              x1={barX}
              y1={todayTopY}
              x2={barX + barW}
              y2={todayTopY}
              stroke="rgba(0,160,90,0.9)"
              strokeWidth={3}
            />
          )}

          {/* Weekly projected line */}
          <Line
            x1={barX}
            y1={weekY}
            x2={barX + barW}
            y2={weekY}
            stroke="rgba(110,70,160,0.95)"
            strokeWidth={4}
          />
        </G>

        {/* Labels (optional) */}
        {showLabels && (
          <>
            <SvgText
              x={barX + barW + 8}
              y={weekY + 5}
              fontSize="12"
              fill="rgba(110,70,160,0.95)"
            >
              {`${Math.round(projectedWeekTotal)} wk proj`}
            </SvgText>

            <SvgText
              x={barX + barW + 8}
              y={todayTopY + 5}
              fontSize="12"
              fill="rgba(0,160,90,0.9)"
            >
              {`${Math.round(projectedTodayTotal)} today proj`}
            </SvgText>

            <SvgText
              x={barX - 2}
              y={curTopY - 6}
              fontSize="12"
              fill="rgba(20,70,140,0.95)"
            >
              {`${Math.round(currentTotal)} current`}
            </SvgText>
          </>
        )}
      </Svg>
    </View>
  );
};
