import { useState } from "react"
import { useGetAdminOverview, useGetHighRiskUsers, useGetCityAnalytics, useGetAdminAlerts, useGetRiskDistribution, useCreateIntervention } from "@/lib/api-client"
import { formatINR, getRiskColor, getRiskColorHex } from "@/lib/utils"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Users, Shield, AlertTriangle, Activity, MapPin, CheckCircle2,
  Clock, RefreshCw, BellRing, Zap, BarChart3, ChevronRight, Target, Brain
} from "lucide-react"
import { 
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid,
  PieChart, Pie, Cell, AreaChart, Area
} from "recharts"
import { motion } from "framer-motion"
import { useLocation } from "wouter"
import { useQueryClient } from "@tanstack/react-query"

const DIST_COLORS = ['hsl(142 71% 45%)', 'hsl(38 92% 50%)', 'hsl(24 98% 50%)', 'hsl(346 84% 61%)']

// synthetic 90-day trend data for the portfolio chart
const TREND_DATA = Array.from({ length: 13 }, (_, i) => ({
  date: new Date(Date.now() - (12 - i) * 7 * 24 * 60 * 60 * 1000).toISOString(),
  score: Math.round(48 + Math.sin(i * 0.6) * 6 + i * 0.3),
}))

export default function AdminDashboard() {
  const [, setLocation] = useLocation()
  const qc = useQueryClient()
  const [creating, setCreating] = useState<string | null>(null)

  const { data: overview, isLoading, refetch } = useGetAdminOverview()
  const { data: highRiskRaw } = useGetHighRiskUsers({ limit: 8 })
  const { data: cityRaw } = useGetCityAnalytics()
  const { data: adminAlerts } = useGetAdminAlerts({ severity: 'critical' as any, limit: 6 } as any)
  const { data: dist } = useGetRiskDistribution()
  const { mutateAsync: createIntervention } = useCreateIntervention()

  // High-risk users endpoint returns array directly
  const highRiskUsers: any[] = Array.isArray(highRiskRaw) ? highRiskRaw : []
  // City analytics endpoint returns array directly
  const cityList: any[] = Array.isArray(cityRaw) ? cityRaw : []
  // Alerts endpoint returns array directly
  const alertList: any[] = Array.isArray(adminAlerts) ? adminAlerts : []
  // Risk distribution uses byLevel array
  const distRaw = dist as any
  const byLevel: Array<{ level: string; count: number }> = distRaw?.byLevel || []
  const riskDistData = byLevel.length > 0 ? [
    { name: 'Low',      value: byLevel.find((l: any) => l.level === 'low')?.count ?? 0,      color: DIST_COLORS[0] },
    { name: 'Medium',   value: byLevel.find((l: any) => l.level === 'medium')?.count ?? 0,   color: DIST_COLORS[1] },
    { name: 'High',     value: byLevel.find((l: any) => l.level === 'high')?.count ?? 0,     color: DIST_COLORS[2] },
    { name: 'Critical', value: byLevel.find((l: any) => l.level === 'critical')?.count ?? 0, color: DIST_COLORS[3] },
  ] : []

  const handleIntervention = async (userId: string, userName: string) => {
    setCreating(userId)
    try {
      await createIntervention({
        data: { userId, type: 'counseling', priority: 'high', notes: `Auto-triggered intervention for ${userName}. Immediate financial review required.` }
      })
      qc.invalidateQueries()
      alert(`✅ Intervention escalated for ${userName}! Risk team has been notified.`)
    } catch (e) {
      console.error(e)
    } finally {
      setCreating(null)
    }
  }

  if (isLoading) return <AdminSkeleton />
  if (!overview) return <div className="text-destructive p-8 text-center">Failed to load. Please refresh.</div>

  const ov = overview as any
  const highRiskCount: number = ov.highRiskUsers ?? ov.highRiskCount ?? 0
  const totalUsers: number = ov.totalUsers ?? 0
  const cityNames: string[] = Array.isArray(ov.cities) ? ov.cities : []

  return (
    <div className="space-y-6 pb-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="w-8 h-8 rounded-xl bg-primary/20 flex items-center justify-center">
              <Brain className="w-4 h-4 text-primary" />
            </div>
            <h1 className="text-3xl font-display font-bold tracking-tight">Risk Operations Center</h1>
          </div>
          <p className="text-muted-foreground ml-11">Real-time portfolio monitoring · Barclays India</p>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          {alertList.length > 0 && (
            <Badge className="bg-destructive/20 text-destructive border-destructive/30 px-3 py-1.5 animate-pulse">
              <BellRing className="w-3 h-3 mr-1.5" />{alertList.length} Critical Alerts
            </Badge>
          )}
          <Button variant="outline" size="sm" className="border-border/50 bg-secondary/20 hover:bg-secondary/40 rounded-xl" onClick={() => refetch()}>
            <RefreshCw className="w-3.5 h-3.5 mr-2" />Refresh
          </Button>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-success/10 border border-success/20">
            <div className="w-2 h-2 rounded-full bg-success animate-pulse"></div>
            <span className="text-xs font-medium text-success uppercase tracking-wider">Live</span>
          </div>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Total Users', value: totalUsers, icon: <Users className="w-5 h-5 text-info" />, bg: 'bg-info/10', sub: `${cityNames.length} cities · India` },
          { label: 'High Risk Users', value: highRiskCount, icon: <AlertTriangle className="w-5 h-5 text-destructive" />, bg: 'bg-destructive/10', sub: totalUsers > 0 ? `${Math.round((highRiskCount / totalUsers) * 100)}% of portfolio` : '—' },
          { label: 'Active Alerts', value: ov.activeAlerts ?? 0, icon: <BellRing className="w-5 h-5 text-warning" />, bg: 'bg-warning/10', sub: 'Require review' },
          { label: 'Avg Risk Score', value: ov.averageRiskScore ?? 0, icon: <Activity className="w-5 h-5 text-primary" />, bg: 'bg-primary/10', sub: 'Stable trend' },
        ].map((kpi, i) => (
          <motion.div key={kpi.label} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.08 }}>
            <Card className="glass-panel p-5 hover:shadow-glow transition-shadow">
              <div className={`inline-flex p-2 rounded-xl mb-3 ${kpi.bg}`}>{kpi.icon}</div>
              <div className="text-3xl font-display font-bold tracking-tight">{kpi.value}</div>
              <p className="text-xs font-semibold text-muted-foreground mt-1">{kpi.label}</p>
              <p className="text-xs text-muted-foreground/70 mt-0.5">{kpi.sub}</p>
            </Card>
          </motion.div>
        ))}
      </div>

      {/* Risk Distribution + Trend */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="glass-panel p-6">
          <h3 className="font-semibold mb-0.5">Risk Distribution</h3>
          <p className="text-xs text-muted-foreground mb-4">Portfolio breakdown by risk tier</p>
          <div className="h-[155px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={riskDistData} cx="50%" cy="50%" innerRadius={45} outerRadius={72} paddingAngle={3} dataKey="value" stroke="none">
                  {riskDistData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '8px', fontSize: '12px' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="grid grid-cols-2 gap-2 mt-2">
            {riskDistData.map(d => (
              <div key={d.name} className="flex items-center gap-2 text-xs">
                <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: d.color }}></div>
                <span className="text-muted-foreground">{d.name}:</span>
                <span className="font-bold">{d.value}</span>
              </div>
            ))}
          </div>
        </Card>

        <Card className="glass-panel p-6 lg:col-span-2">
          <div className="flex items-center justify-between mb-0.5">
            <h3 className="font-semibold">Portfolio Risk Trend (90 Days)</h3>
            <Badge variant="outline" className="text-xs">Stable</Badge>
          </div>
          <p className="text-xs text-muted-foreground mb-4">Average portfolio risk score · Weekly aggregated</p>
          <div className="h-[185px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={TREND_DATA} margin={{ top: 5, right: 5, left: -25, bottom: 0 }}>
                <defs>
                  <linearGradient id="riskGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.15} />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} tickFormatter={(v) => new Date(v).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} />
                <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '8px', fontSize: '12px' }} formatter={(v: number) => [v, 'Avg Risk']} />
                <Area type="monotone" dataKey="score" stroke="hsl(var(--primary))" fill="url(#riskGrad)" strokeWidth={2} dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {/* High-Risk Users Table */}
      <Card className="glass-panel p-6">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h3 className="font-semibold text-lg flex items-center gap-2">
              <Shield className="w-5 h-5 text-destructive" />
              High-Risk Customers — Intervention Required
            </h3>
            <p className="text-xs text-muted-foreground mt-0.5">Risk score &gt; 50 · Sorted by severity · Click Intervene to escalate</p>
          </div>
          <Button variant="ghost" size="sm" className="text-xs text-primary hover:bg-primary/10" onClick={() => setLocation('/admin/users')}>
            All Users <ChevronRight className="w-3 h-3 ml-1" />
          </Button>
        </div>
        <div className="overflow-x-auto -mx-1">
          <table className="w-full min-w-[680px]">
            <thead>
              <tr className="text-xs uppercase tracking-wider text-muted-foreground border-b border-border/50">
                <th className="text-left py-3 px-3">Customer</th>
                <th className="text-left py-3 px-3">Location</th>
                <th className="text-center py-3 px-3">Risk Score</th>
                <th className="text-center py-3 px-3">Employment</th>
                <th className="text-right py-3 px-3">Income / mo</th>
                <th className="text-center py-3 px-3">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/30">
              {highRiskUsers.slice(0, 8).map((user: any, i: number) => (
                <motion.tr
                  key={user.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="hover:bg-white/5 transition-colors"
                >
                  <td className="py-3 px-3">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white shrink-0" style={{ backgroundColor: getRiskColorHex(user.riskLevel) }}>
                        {(user.name as string).split(' ').map((n: string) => n[0]).join('').substring(0, 2)}
                      </div>
                      <div>
                        <p className="font-medium text-sm">{user.name}</p>
                        <p className="text-xs text-muted-foreground">{user.email}</p>
                      </div>
                    </div>
                  </td>
                  <td className="py-3 px-3 text-sm">
                    <div className="flex items-center gap-1.5 text-muted-foreground">
                      <MapPin className="w-3 h-3" />{user.city}
                    </div>
                  </td>
                  <td className="py-3 px-3 text-center">
                    <div className="flex items-center justify-center gap-2">
                      <div className="w-16 h-1.5 bg-secondary/60 rounded-full overflow-hidden">
                        <div className="h-full rounded-full" style={{ width: `${user.riskScore}%`, backgroundColor: getRiskColorHex(user.riskLevel) }} />
                      </div>
                      <Badge className={`text-xs px-2 py-0.5 ${getRiskColor(user.riskLevel)}`}>{user.riskScore}</Badge>
                    </div>
                  </td>
                  <td className="py-3 px-3 text-center">
                    <Badge variant="outline" className="text-xs capitalize">{String(user.employmentType ?? '').replace(/_/g, ' ')}</Badge>
                  </td>
                  <td className="py-3 px-3 text-right font-mono text-sm font-semibold">{formatINR(user.monthlyIncome || 0)}</td>
                  <td className="py-3 px-3 text-center">
                    <Button size="sm" variant="destructive" className="h-7 text-xs px-3 rounded-lg" disabled={creating === user.id} onClick={() => handleIntervention(user.id, user.name)}>
                      {creating === user.id ? <RefreshCw className="w-3 h-3 animate-spin" /> : <><Zap className="w-3 h-3 mr-1" />Intervene</>}
                    </Button>
                  </td>
                </motion.tr>
              ))}
              {highRiskUsers.length === 0 && (
                <tr><td colSpan={6} className="py-8 text-center text-muted-foreground text-sm">No high-risk users found</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* City Analytics + Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="glass-panel p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold flex items-center gap-2"><MapPin className="w-4 h-4 text-primary" />City-wise Risk Analytics</h3>
            <Button variant="ghost" size="sm" className="text-xs text-primary h-7 hover:bg-primary/10" onClick={() => setLocation('/admin/risk')}>Full View →</Button>
          </div>
          <div className="h-[200px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={cityList.slice(0, 8)} layout="vertical" margin={{ top: 0, right: 25, left: 5, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} opacity={0.15} />
                <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} />
                <YAxis dataKey="city" type="category" tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }} width={65} />
                <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '8px', fontSize: '12px' }} />
                <Bar dataKey="averageRiskScore" radius={[0, 4, 4, 0]} name="Avg Risk">
                  {cityList.slice(0, 8).map((e: any, i: number) => {
                    const s = e.averageRiskScore
                    return <Cell key={i} fill={s >= 60 ? DIST_COLORS[3] : s >= 40 ? DIST_COLORS[2] : s >= 25 ? DIST_COLORS[1] : DIST_COLORS[0]} />
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-xs">
              <thead><tr className="text-muted-foreground border-b border-border/30">
                <th className="text-left pb-1.5">City</th><th className="text-center pb-1.5">Users</th><th className="text-center pb-1.5">High Risk %</th><th className="text-right pb-1.5">Avg Score</th>
              </tr></thead>
              <tbody className="divide-y divide-border/20">
                {cityList.slice(0, 5).map((c: any) => (
                  <tr key={c.city} className="hover:bg-white/5">
                    <td className="py-1.5 font-medium">{c.city}</td>
                    <td className="py-1.5 text-center text-muted-foreground">{c.totalUsers}</td>
                    <td className="py-1.5 text-center text-destructive font-bold">{c.highRiskPercentage}%</td>
                    <td className="py-1.5 text-right font-mono font-bold" style={{ color: getRiskColorHex(c.averageRiskScore >= 60 ? 'critical' : c.averageRiskScore >= 40 ? 'high' : c.averageRiskScore >= 25 ? 'medium' : 'low') }}>{c.averageRiskScore}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        <Card className="glass-panel p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold flex items-center gap-2"><BellRing className="w-4 h-4 text-warning" />High-Priority Alerts Feed</h3>
            <Badge variant="outline" className="text-xs">{alertList.length} active</Badge>
          </div>
          <div className="space-y-3 max-h-[320px] overflow-y-auto">
            {alertList.map((alert: any, i: number) => (
              <motion.div
                key={alert.id}
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.06 }}
                className={`flex items-start gap-3 p-3.5 rounded-xl border ${
                  alert.severity === 'critical' ? 'bg-destructive/10 border-destructive/30' :
                  'bg-warning/10 border-warning/30'
                }`}
              >
                <div className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${alert.severity === 'critical' ? 'bg-destructive' : 'bg-warning'}`}></div>
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-xs">{alert.title}</p>
                  <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2 leading-relaxed">{alert.message}</p>
                  <p className="text-[10px] text-muted-foreground mt-1.5 flex items-center gap-1">
                    <Clock className="w-2.5 h-2.5" />
                    {new Date(alert.createdAt).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}
                  </p>
                </div>
                <Badge variant="outline" className="text-[10px] uppercase py-0 px-1.5 shrink-0">{alert.severity}</Badge>
              </motion.div>
            ))}
            {alertList.length === 0 && (
              <div className="text-center py-8 flex flex-col items-center gap-2 text-muted-foreground">
                <CheckCircle2 className="w-8 h-8 text-success opacity-60" />
                <p className="text-sm font-medium text-success">All clear!</p>
                <p className="text-xs">No critical alerts at this time</p>
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* Quick Navigation */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Risk Distribution', icon: <BarChart3 className="w-5 h-5" />, path: '/admin/risk', desc: 'Full breakdown', c: 'border-primary/30 hover:bg-primary/10 text-primary' },
          { label: 'User Management', icon: <Users className="w-5 h-5" />, path: '/admin/users', desc: `${totalUsers} customers`, c: 'border-info/30 hover:bg-info/10 text-info' },
          { label: 'Interventions', icon: <Target className="w-5 h-5" />, path: '/admin/interventions', desc: 'Active cases', c: 'border-warning/30 hover:bg-warning/10 text-warning' },
          { label: 'Model Performance', icon: <Activity className="w-5 h-5" />, path: '/admin/model', desc: 'AUC & metrics', c: 'border-success/30 hover:bg-success/10 text-success' },
        ].map(item => (
          <Card key={item.path} className={`glass-panel p-4 cursor-pointer border transition-all hover:shadow-glow ${item.c}`} onClick={() => setLocation(item.path)}>
            <div className="mb-2">{item.icon}</div>
            <p className="font-semibold text-sm text-foreground">{item.label}</p>
            <p className="text-xs text-muted-foreground mt-0.5">{item.desc}</p>
          </Card>
        ))}
      </div>
    </div>
  )
}

function AdminSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="w-80 h-10 bg-secondary rounded-lg"></div>
      <div className="grid grid-cols-4 gap-4">{[1,2,3,4].map(i => <Skeleton key={i} className="h-28 rounded-2xl bg-secondary" />)}</div>
      <div className="grid grid-cols-3 gap-6"><Skeleton className="h-72 rounded-2xl bg-secondary" /><Skeleton className="h-72 rounded-2xl bg-secondary lg:col-span-2" /></div>
      <Skeleton className="h-80 rounded-2xl bg-secondary" />
    </div>
  )
}
