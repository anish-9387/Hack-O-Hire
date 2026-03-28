import { useState } from "react"
import { useGetSpendingAnalytics, type GetSpendingAnalyticsPeriod } from "@/lib/api-client"
import { formatINR } from "@/lib/utils"
import { Card } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, Legend } from "recharts"
import { ArrowDown, ArrowUp, Minus } from "lucide-react"

export default function Analytics() {
  const [period, setPeriod] = useState<GetSpendingAnalyticsPeriod>("30d")
  const { data, isLoading } = useGetSpendingAnalytics({ period })

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-display font-bold tracking-tight">Spending Analytics</h1>
          <p className="text-muted-foreground">Deep dive into your cash flow patterns.</p>
        </div>
        
        <ToggleGroup type="single" value={period} onValueChange={(v) => v && setPeriod(v as any)} className="bg-secondary/20 p-1 rounded-xl border border-border/50">
          <ToggleGroupItem value="7d" className="rounded-lg data-[state=on]:bg-primary data-[state=on]:text-primary-foreground">7D</ToggleGroupItem>
          <ToggleGroupItem value="30d" className="rounded-lg data-[state=on]:bg-primary data-[state=on]:text-primary-foreground">30D</ToggleGroupItem>
          <ToggleGroupItem value="90d" className="rounded-lg data-[state=on]:bg-primary data-[state=on]:text-primary-foreground">90D</ToggleGroupItem>
          <ToggleGroupItem value="1y" className="rounded-lg data-[state=on]:bg-primary data-[state=on]:text-primary-foreground">1Y</ToggleGroupItem>
        </ToggleGroup>
      </div>

      {isLoading || !data ? (
        <AnalyticsSkeleton />
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card className="glass-panel p-6">
              <h3 className="text-sm font-medium text-muted-foreground mb-2">Total Outflow</h3>
              <div className="text-4xl font-display font-bold text-foreground">{formatINR(data.totalSpent)}</div>
            </Card>
            <Card className="glass-panel p-6">
              <h3 className="text-sm font-medium text-muted-foreground mb-2">Total Inflow</h3>
              <div className="text-4xl font-display font-bold text-success">{formatINR(data.totalIncome)}</div>
            </Card>
          </div>

          <Card className="glass-panel p-6">
            <h3 className="font-semibold mb-6">Cashflow Timeline</h3>
            <div className="h-[300px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.timeline} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis 
                    dataKey="date" 
                    tickFormatter={(val) => new Date(val).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}
                  />
                  <YAxis tickFormatter={(val) => `₹${val/1000}k`} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '8px' }}
                    formatter={(val: number) => formatINR(val)}
                    labelFormatter={(val) => new Date(val).toLocaleDateString('en-IN')}
                  />
                  <Legend />
                  <Bar dataKey="income" name="Inflow" fill="hsl(var(--success))" radius={[4, 4, 0, 0]} maxBarSize={40} />
                  <Bar dataKey="spent" name="Outflow" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} maxBarSize={40} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>

          <Card className="glass-panel overflow-hidden">
            <div className="p-6 border-b border-border/50">
              <h3 className="font-semibold">Category Breakdown</h3>
            </div>
            <div className="divide-y divide-border/10">
              {data.categories.map((cat) => (
                <div key={cat.category} className="p-4 sm:px-6 flex items-center justify-between hover:bg-white/[0.02] transition-colors">
                  <div className="flex items-center gap-4 flex-1">
                    <div className="w-10 h-10 rounded-full bg-secondary flex items-center justify-center font-bold text-muted-foreground uppercase text-xs border border-border">
                      {cat.category.substring(0,2)}
                    </div>
                    <div>
                      <p className="font-medium capitalize">{cat.category.replace('_', ' ')}</p>
                      <p className="text-xs text-muted-foreground">{cat.transactionCount} transactions</p>
                    </div>
                  </div>
                  
                  <div className="flex flex-col items-end">
                    <div className="font-mono font-semibold">{formatINR(cat.amount)}</div>
                    <div className="flex items-center gap-1 text-xs mt-1">
                      {cat.trend === 'up' && <span className="text-destructive flex items-center"><ArrowUp className="w-3 h-3 mr-0.5" /> Rising</span>}
                      {cat.trend === 'down' && <span className="text-success flex items-center"><ArrowDown className="w-3 h-3 mr-0.5" /> Falling</span>}
                      {cat.trend === 'stable' && <span className="text-muted-foreground flex items-center"><Minus className="w-3 h-3 mr-0.5" /> Stable</span>}
                      <span className="text-muted-foreground ml-2">({cat.percentage}%)</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </>
      )}
    </div>
  )
}

function AnalyticsSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Skeleton className="h-32 rounded-2xl bg-secondary" />
        <Skeleton className="h-32 rounded-2xl bg-secondary" />
      </div>
      <Skeleton className="h-[400px] rounded-2xl bg-secondary" />
      <Skeleton className="h-[300px] rounded-2xl bg-secondary" />
    </div>
  )
}
