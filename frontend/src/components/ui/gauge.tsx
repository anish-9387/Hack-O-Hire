import React from "react"
import { cn, getRiskColorHex } from "@/lib/utils"

interface GaugeProps {
  value: number
  max?: number
  size?: number
  strokeWidth?: number
  level?: string
  className?: string
  label?: string
}

export function Gauge({ 
  value, 
  max = 100, 
  size = 200, 
  strokeWidth = 16,
  level,
  className,
  label
}: GaugeProps) {
  const radius = (size - strokeWidth) / 2
  const circumference = radius * 2 * Math.PI
  const percent = Math.min(Math.max(value, 0), max) / max
  // Display as an arc (270 degrees)
  const arcOffset = circumference * 0.25
  const strokeDasharray = `${circumference * 0.75} ${circumference * 0.25}`
  const strokeDashoffset = circumference * 0.75 * (1 - percent)

  const color = getRiskColorHex(level)

  return (
    <div className={cn("relative flex flex-col items-center justify-center", className)} style={{ width: size, height: size }}>
      <svg
        className="transform -rotate-135"
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
      >
        {/* Background track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          strokeDasharray={strokeDasharray}
          strokeDashoffset="0"
          strokeLinecap="round"
          className="text-muted/30"
        />
        {/* Progress track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={strokeDasharray}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          className="transition-all duration-1000 ease-out"
        />
      </svg>
      <div className="absolute flex flex-col items-center justify-center text-center mt-4">
        <span className="text-5xl font-display font-bold tracking-tighter" style={{ color }}>
          {value}
        </span>
        {label && <span className="text-sm font-medium text-muted-foreground uppercase tracking-wider mt-1">{label}</span>}
      </div>
    </div>
  )
}
