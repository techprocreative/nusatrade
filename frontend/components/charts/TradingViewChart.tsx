"use client";

import { useEffect, useRef, useState } from "react";

interface CandleData {
    time: any; // Time from lightweight-charts
    open: number;
    high: number;
    low: number;
    close: number;
}

interface TradingViewChartProps {
    symbol?: string;
    data?: CandleData[];
    onCrosshairMove?: (price: number | null) => void;
}

export default function TradingViewChart({
    symbol = "EURUSD",
    data,
    onCrosshairMove,
}: TradingViewChartProps) {
    const containerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<any>(null);
    const seriesRef = useRef<any>(null);
    const [currentPrice, setCurrentPrice] = useState<number | null>(null);

    useEffect(() => {
        // Dynamically import lightweight-charts
        const initChart = async () => {
            if (!containerRef.current) return;

            const { createChart, CrosshairMode } = await import("lightweight-charts");

            // Create chart
            const chart = createChart(containerRef.current, {
                width: containerRef.current.clientWidth,
                height: 400,
                layout: {
                    background: { color: "#0f172a" },
                    textColor: "#94a3b8",
                },
                grid: {
                    vertLines: { color: "#1e293b" },
                    horzLines: { color: "#1e293b" },
                },
                crosshair: {
                    mode: CrosshairMode.Normal,
                },
                rightPriceScale: {
                    borderColor: "#334155",
                },
                timeScale: {
                    borderColor: "#334155",
                    timeVisible: true,
                    secondsVisible: false,
                },
            });

            chartRef.current = chart;

            // Add candlestick series
            const candlestickSeries = chart.addCandlestickSeries({
                upColor: "#22c55e",
                downColor: "#ef4444",
                borderDownColor: "#ef4444",
                borderUpColor: "#22c55e",
                wickDownColor: "#ef4444",
                wickUpColor: "#22c55e",
            });

            seriesRef.current = candlestickSeries;

            // Load initial data or generate sample
            if (data && data.length > 0) {
                candlestickSeries.setData(data);
            } else {
                candlestickSeries.setData(generateSampleData());
            }

            // Handle crosshair move
            chart.subscribeCrosshairMove((param: any) => {
                if (param.time) {
                    const price = param.seriesData.get(candlestickSeries);
                    if (price) {
                        setCurrentPrice(price.close);
                        onCrosshairMove?.(price.close);
                    }
                } else {
                    setCurrentPrice(null);
                    onCrosshairMove?.(null);
                }
            });

            // Handle resize
            const handleResize = () => {
                if (containerRef.current) {
                    chart.applyOptions({ width: containerRef.current.clientWidth });
                }
            };

            window.addEventListener("resize", handleResize);

            return () => {
                window.removeEventListener("resize", handleResize);
                chart.remove();
            };
        };

        initChart();
    }, []);

    // Update data when prop changes
    useEffect(() => {
        if (seriesRef.current && data && data.length > 0) {
            seriesRef.current.setData(data);
        }
    }, [data]);

    return (
        <div className="relative">
            <div className="absolute top-2 left-2 z-10 flex items-center gap-4">
                <span className="text-lg font-bold text-white">{symbol}</span>
                {currentPrice && (
                    <span className="text-sm text-slate-400">
                        Price: {currentPrice.toFixed(5)}
                    </span>
                )}
            </div>
            <div
                ref={containerRef}
                className="w-full rounded-lg overflow-hidden border border-slate-700"
            />
        </div>
    );
}

function generateSampleData(): CandleData[] {
    const data: CandleData[] = [];
    let basePrice = 1.089;
    const now = Math.floor(Date.now() / 1000);
    const oneHour = 3600;

    for (let i = 200; i >= 0; i--) {
        const time = now - i * oneHour;
        const volatility = 0.0005 + Math.random() * 0.001;
        const direction = Math.random() > 0.5 ? 1 : -1;

        const open = basePrice;
        const close = open + direction * volatility * (0.5 + Math.random());
        const high = Math.max(open, close) + Math.random() * volatility * 0.5;
        const low = Math.min(open, close) - Math.random() * volatility * 0.5;

        data.push({
            time: time as any,
            open: parseFloat(open.toFixed(5)),
            high: parseFloat(high.toFixed(5)),
            low: parseFloat(low.toFixed(5)),
            close: parseFloat(close.toFixed(5)),
        });

        basePrice = close;
    }

    return data;
}
