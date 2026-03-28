import { useGetRiskDistribution } from "@/lib/api-client"
import { Card } from "@/components/ui/card"
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, LineChart, Line, Legend } from "recharts"

export default function RiskDistributionPage() {
  const { data, isLoading } = useGetRiskDistribution()

  if (isLoading || !data) return <div className="p-8 text-center text-muted-foreground animate-pulse">Loading analytics...</div>

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-display font-bold tracking-tight">Risk Distribution Analytics</h1>
        <p className="text-muted-foreground mt-1">Deep dive into portfolio segmentation.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="glass-panel p-6">
          <h3 className="font-semibold mb-6">Risk by Employment Type</h3>
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.byEmploymentType} layout="vertical" margin={{ top: 0, right: 30, left: 40, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} opacity={0.2} />
                <XAxis type="number" />
                <YAxis dataKey="type" type="category" width={80} tick={{ fontSize: 12, fill: 'hsl(var(--muted-foreground))' }} />
                <Tooltip 
                  cursor={{ fill: 'hsl(var(--secondary))', opacity: 0.4 }}
                  contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))' }}
                />
                <Bar dataKey="averageScore" name="Avg Risk Score" fill="hsl(var(--primary))" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card className="glass-panel p-6">
          <h3 className="font-semibold mb-6">City Risk Profiles</h3>
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.byCity} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.2} />
                <XAxis dataKey="city" tick={{ fontSize: 12, fill: 'hsl(var(--muted-foreground))' }} />
                <YAxis />
                <Tooltip 
                  cursor={{ fill: 'hsl(var(--secondary))', opacity: 0.4 }}
                  contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))' }}
                />
                <Legend />
                <Bar dataKey="highRiskCount" name="High Risk Users" fill="hsl(var(--destructive))" radius={[4, 4, 0, 0]} stackId="a" />
                <Bar dataKey="userCount" name="Safe Users" fill="hsl(var(--success))" radius={[4, 4, 0, 0]} stackId="a" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card className="glass-panel p-6 lg:col-span-2">
          <h3 className="font-semibold mb-6">Macro Risk Trend (90 Days)</h3>
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data.trendOverTime} margin={{ top: 5, right: 20, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.2} />
                <XAxis dataKey="date" tickFormatter={(v) => new Date(v).toLocaleDateString('en-IN', {month:'short'})} />
                <YAxis yAxisId="left" domain={['auto', 'auto']} />
                <YAxis yAxisId="right" orientation="right" />
                <Tooltip 
                  contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))' }}
                  labelFormatter={(v) => new Date(v).toLocaleDateString()}
                />
                <Legend />
                <Line yAxisId="left" type="monotone" dataKey="averageScore" name="Avg Score" stroke="hsl(var(--primary))" strokeWidth={3} dot={false} />
                <Line yAxisId="right" type="monotone" dataKey="highRiskCount" name="High Risk Count" stroke="hsl(var(--destructive))" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>
    </div>
  )
}
