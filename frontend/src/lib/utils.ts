import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatINR(amount: number): string {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(amount)
}

export function formatCompactINR(amount: number): string {
  if (amount >= 10000000) return `₹${(amount / 10000000).toFixed(2)}Cr`
  if (amount >= 100000) return `₹${(amount / 100000).toFixed(2)}L`
  if (amount >= 1000) return `₹${(amount / 1000).toFixed(1)}k`
  return `₹${amount}`
}

export function getRiskColor(level: string | undefined): string {
  switch (level?.toLowerCase()) {
    case 'low': return 'text-success bg-success/10 border-success/20'
    case 'medium': return 'text-warning bg-warning/10 border-warning/20'
    case 'high': return 'text-orange-500 bg-orange-500/10 border-orange-500/20'
    case 'critical': return 'text-destructive bg-destructive/10 border-destructive/20'
    default: return 'text-muted-foreground bg-muted border-border'
  }
}

export function getRiskColorHex(level: string | undefined): string {
  switch (level?.toLowerCase()) {
    case 'low': return 'hsl(142 71% 45%)'
    case 'medium': return 'hsl(38 92% 50%)'
    case 'high': return 'hsl(24 98% 50%)'
    case 'critical': return 'hsl(346 84% 61%)'
    default: return 'hsl(215 20% 65%)'
  }
}
