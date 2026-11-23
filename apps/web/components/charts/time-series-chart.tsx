"use client";

import { useEffect, useRef } from "react";
import * as echarts from "echarts/core";
import { LineChart } from "echarts/charts";
import {
  AriaComponent,
  DataZoomComponent,
  GridComponent,
  ToolboxComponent,
  TooltipComponent,
} from "echarts/components";
import { SVGRenderer } from "echarts/renderers";
import type { EChartsOption } from "echarts";
import type { Observation } from "@/lib/schemas";

echarts.use([
  LineChart,
  AriaComponent,
  DataZoomComponent,
  GridComponent,
  ToolboxComponent,
  TooltipComponent,
  SVGRenderer,
]);

const monthFormatter = new Intl.DateTimeFormat("es-AR", {
  month: "short",
  year: "2-digit",
  timeZone: "UTC",
});
const numberFormatter = new Intl.NumberFormat("es-AR", { maximumFractionDigits: 2 });

export function TimeSeriesChart({
  observations,
  title,
  unit,
}: {
  observations: Observation[];
  title: string;
  unit: string;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const available = observations.filter((item) => item.value !== null);
  const description = `${title}. Serie mensual con ${observations.length} períodos; ${
    observations.length - available.length
  } valores ausentes. La tabla completa se encuentra a continuación.`;

  useEffect(() => {
    if (!containerRef.current) return;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const chart = echarts.init(containerRef.current, undefined, {
      renderer: "svg",
      useCoarsePointer: true,
      pointerSize: 44,
    });
    const option: EChartsOption = {
      animation: !reducedMotion,
      aria: { enabled: true, description },
      color: ["#006b78"],
      grid: { left: 54, right: 18, top: 20, bottom: 62, containLabel: true },
      tooltip: {
        trigger: "axis",
        renderMode: "richText",
        valueFormatter: (value) =>
          value === null || value === undefined || value === "-"
            ? "Sin dato"
            : `${numberFormatter.format(Number(value))} ${unit}`,
      },
      toolbox: {
        right: 0,
        feature: {
          saveAsImage: { name: "emae-original-2004", title: "Descargar gráfico" },
        },
      },
      xAxis: {
        type: "category",
        boundaryGap: false,
        data: observations.map((item) => item.period_start),
        axisLabel: {
          hideOverlap: true,
          formatter: (value: string) => monthFormatter.format(new Date(`${value}T00:00:00Z`)),
        },
      },
      yAxis: {
        type: "value",
        name: unit,
        nameLocation: "middle",
        nameGap: 46,
        scale: true,
      },
      dataZoom: [
        { type: "inside", start: observations.length > 120 ? 55 : 0, end: 100 },
        { type: "slider", height: 22, bottom: 8, start: observations.length > 120 ? 55 : 0, end: 100 },
      ],
      series: [
        {
          type: "line",
          name: title,
          data: observations.map((item) =>
            item.value === null ? null : Number.parseFloat(item.value),
          ),
          showSymbol: observations.length < 48,
          symbolSize: 6,
          connectNulls: false,
          lineStyle: { width: 2.5 },
          emphasis: { focus: "series" },
        },
      ],
    };
    chart.setOption(option);
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(containerRef.current);
    return () => {
      observer.disconnect();
      chart.dispose();
    };
  }, [description, observations, title, unit]);

  return (
    <div
      ref={containerRef}
      className="h-[22rem] w-full sm:h-[26rem]"
      role="img"
      aria-label={description}
    />
  );
}
