"use client";

import dynamic from "next/dynamic";
import type { Observation } from "@/lib/schemas";

const TimeSeriesChart = dynamic(
  () => import("./time-series-chart").then((module) => module.TimeSeriesChart),
  {
    ssr: false,
    loading: () => <div className="h-[22rem] animate-pulse rounded-md bg-paper" aria-label="Cargando gráfico" />,
  },
);

export function ActivityChart(props: {
  observations: Observation[];
  title: string;
  unit: string;
}) {
  return <TimeSeriesChart {...props} />;
}
