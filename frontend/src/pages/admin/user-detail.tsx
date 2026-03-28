import { useState } from "react"
import { useParams, useLocation } from "wouter"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { getRiskColor, getRiskColorHex, formatINR } from "@/lib/utils"
import { useQuery } from "@tanstack/react-query"
import { useAuthStore } from "@/hooks/use-store"
import {
  ArrowLeft, User, MapPin, Briefcase, Phone, Mail, Calendar,
  TrendingUp, TrendingDown, AlertTriangle, CheckCircle2, Clock,
  Zap, ShieldAlert, Activity, CreditCard, Bell, FileText,
  ChevronDown, ChevronUp, IndianRupee, BarChart2
} from "lucide-react"
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip,
  CartesianGrid, PieChart, Pie, Cell, ReferenceLine, Area, AreaChart
} from "recharts"
import { motion } from "framer-motion"

const CAT_COLORS = [
  '#6366f1','#f59e0b','#10b981','#ef4444','#3b82f6',
  '#8b5cf6','#ec4899','#14b8a6','#f97316','#84cc16',
]

const CATEGORY_LABELS: Record<string, string> = {
  salary: 'Salary', upi: 'UPI Transfer', atm_withdrawal: 'ATM', emi_payment: 'EMI',
  utility_bill: 'Utilities', grocery: 'Grocery', food_delivery: 'Food', loan_app: 'Loan App',
  festival_shopping: 'Festival', medical: 'Medical', fuel: 'Fuel', rent: 'Rent',
  online_shopping: 'Online', transfer: 'Transfer', other: 'Other',
}

const SEVERITY_STYLE: Record<string, string> = {
  critical: 'bg-destructive/10 border-destructive/30 text-destructive',
  warning: 'bg-warning/10 border-warning/30 text-warning',
  info: 'bg-info/10 border-info/30 text-info',
}

const STATUS_STYLE: Record<string, string> = {
  pending: 'bg-warning/10 text-warning border-warning/30',
  active: 'bg-info/10 text-info border-info/30',
  completed: 'bg-success/10 text-success border-success/30',
  cancelled: 'bg-muted text-muted-foreground border-border',
}

async function fetchUserDetail(id: string) {
  const token = useAuthStore.getState().token
  const res = await fetch(`/api/admin/users/${id}`, {
    headers: { Authorization: `Bearer ${token}` }
  })
  if (!res.ok) throw new Error("Failed to load user detail")
  return res.json()
}

export default function AdminUserDetail() {
  const { id } = useParams<{ id: string }>()
  const [, setLocation] = useLocation()
  const [txTab, setTxTab] = useState<'all' | 'debit' | 'credit' | 'stress'>('all')
  const [showAllTx, setShowAllTx] = useState(false)

  const { data, isLoading, error } = useQuery({
    queryKey: ['admin-user-detail', id],
    queryFn: () => fetchUserDetail(id!),
    enabled: !!id,
  })

  if (isLoading) return <DetailSkeleton />
  if (error || !data) return (
    <div className="flex flex-col items-center justify-center py-20 gap-4">
      <ShieldAlert className="w-12 h-12 text-destructive opacity-60" />
      <p className="text-destructive font-semibold">Failed to load user details</p>
      <Button variant="outline" onClick={() => setLocation('/admin/users')}>← Back to Users</Button>
    </div>
  )

  const { profile, riskHistory, transactions, alerts, interventions, spendingByCategory, summary } = data

  // Risk history chart — reversed to show oldest→newest
  const chartHistory = [...riskHistory].reverse().map((r: any) => ({
    date: new Date(r.predictedAt).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }),
    score: r.score,
    health: r.financialHealthScore,
    level: r.level,
  }))

  // Filtered transactions
  const filteredTx = transactions.filter((t: any) => {
    if (txTab === 'all') return true
    if (txTab === 'debit') return t.type === 'debit'
    if (txTab === 'credit') return t.type === 'credit'
    if (txTab === 'stress') return t.isStressIndicator
    return true
  })
  const displayedTx = showAllTx ? filteredTx : filteredTx.slice(0, 10)

  const latestRisk = riskHistory[0] as any
  const scoreChange = summary.riskScoreChange
  const joinedDays = Math.floor((Date.now() - new Date(profile.createdAt).getTime()) / (1000 * 60 * 60 * 24))

  return (
    <div className="space-y-6 pb-10">
      {/* Back + Header */}
      <div className="flex items-start gap-4">
        <Button variant="ghost" size="icon" className="mt-1 hover:bg-secondary/40 rounded-xl shrink-0" onClick={() => setLocation('/admin/users')}>
          <ArrowLeft className="w-4 h-4" />
        </Button>
        <div className="flex-1">
          <div className="flex items-center gap-3 flex-wrap">
            <div
              className="w-12 h-12 rounded-2xl flex items-center justify-center text-lg font-bold text-white shrink-0"
              style={{ backgroundColor: getRiskColorHex(profile.riskLevel) }}
            >
              {profile.name.split(' ').map((n: string) => n[0]).join('').substring(0, 2).toUpperCase()}
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h1 className="text-2xl font-display font-bold tracking-tight">{profile.name}</h1>
                <Badge className={`text-xs uppercase font-bold ${getRiskColor(profile.riskLevel)}`}>{profile.riskLevel} risk</Badge>
                {!profile.isActive && <Badge variant="outline" className="text-xs text-muted-foreground">Inactive</Badge>}
              </div>
              <p className="text-sm text-muted-foreground mt-0.5">{profile.email} · Joined {joinedDays} days ago · ID: {profile.id.substring(0, 8)}…</p>
            </div>
          </div>
        </div>
      </div>

      {/* Summary KPI Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {[
          { label: 'Risk Score', value: profile.riskScore, sub: scoreChange !== 0 ? `${scoreChange > 0 ? '+' : ''}${scoreChange.toFixed(1)} vs prev` : 'No change', icon: <Activity className="w-4 h-4" />, accent: getRiskColorHex(profile.riskLevel), highlight: true },
          { label: 'Health Score', value: profile.financialHealthScore, sub: 'Out of 100', icon: <TrendingUp className="w-4 h-4 text-success" />, accent: 'hsl(142 71% 45%)' },
          { label: 'Monthly Income', value: formatINR(profile.monthlyIncome), sub: profile.employmentType?.replace(/_/g, ' '), icon: <IndianRupee className="w-4 h-4 text-info" />, accent: 'hsl(217 91% 60%)' },
          { label: 'Transactions', value: summary.totalTransactions, sub: `${summary.stressTransactions} stress indicators`, icon: <CreditCard className="w-4 h-4 text-warning" />, accent: 'hsl(38 92% 50%)' },
          { label: 'Alerts', value: alerts.length, sub: `${summary.unreadAlerts} unread`, icon: <Bell className="w-4 h-4 text-destructive" />, accent: 'hsl(346 84% 61%)' },
          { label: 'Interventions', value: interventions.length, sub: `${summary.activeInterventions} active`, icon: <Zap className="w-4 h-4 text-primary" />, accent: 'hsl(var(--primary))' },
        ].map((kpi, i) => (
          <motion.div key={kpi.label} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
            <Card className="glass-panel p-4">
              <div className="flex items-center justify-between mb-1.5">
                {kpi.icon}
                {i === 0 && scoreChange !== 0 && (
                  scoreChange > 0
                    ? <TrendingUp className="w-3 h-3 text-destructive" />
                    : <TrendingDown className="w-3 h-3 text-success" />
                )}
              </div>
              <div className="text-xl font-display font-bold" style={kpi.highlight ? { color: kpi.accent } : {}}>{kpi.value}</div>
              <p className="text-[10px] font-semibold text-muted-foreground mt-0.5 uppercase tracking-wide">{kpi.label}</p>
              <p className="text-[10px] text-muted-foreground/70 capitalize">{kpi.sub}</p>
            </Card>
          </motion.div>
        ))}
      </div>

      {/* Profile Details + Spending Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="glass-panel p-6">
          <h3 className="font-semibold mb-4 flex items-center gap-2"><User className="w-4 h-4 text-primary" />Profile Details</h3>
          <dl className="space-y-3 text-sm">
            {[
              { icon: <Mail className="w-3.5 h-3.5" />, label: 'Email', value: profile.email },
              { icon: <Phone className="w-3.5 h-3.5" />, label: 'Phone', value: profile.phone || '—' },
              { icon: <MapPin className="w-3.5 h-3.5" />, label: 'Location', value: [profile.city, profile.state, profile.pincode].filter(Boolean).join(', ') },
              { icon: <Briefcase className="w-3.5 h-3.5" />, label: 'Employment', value: profile.employmentType?.replace(/_/g, ' ') || '—' },
              { icon: <IndianRupee className="w-3.5 h-3.5" />, label: 'Monthly Income', value: formatINR(profile.monthlyIncome) },
              { icon: <Calendar className="w-3.5 h-3.5" />, label: 'Member Since', value: new Date(profile.createdAt).toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' }) },
              { icon: <Clock className="w-3.5 h-3.5" />, label: 'Last Login', value: profile.lastLoginAt ? new Date(profile.lastLoginAt).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }) : 'Never' },
            ].map(row => (
              <div key={row.label} className="flex gap-3">
                <dt className="flex items-center gap-1.5 text-muted-foreground w-28 shrink-0 capitalize">{row.icon}{row.label}</dt>
                <dd className="font-medium flex-1 min-w-0 truncate capitalize">{row.value}</dd>
              </div>
            ))}
          </dl>
          {latestRisk?.behaviorSegment && (
            <div className="mt-4 pt-4 border-t border-border/30">
              <p className="text-xs text-muted-foreground mb-1">Behavior Segment</p>
              <Badge variant="outline" className="text-xs capitalize">{latestRisk.behaviorSegment.replace(/_/g, ' ')}</Badge>
            </div>
          )}
        </Card>

        <Card className="glass-panel p-6 lg:col-span-2">
          <h3 className="font-semibold mb-4 flex items-center gap-2"><BarChart2 className="w-4 h-4 text-primary" />Spending by Category</h3>
          {spendingByCategory.length > 0 ? (
            <div className="flex gap-4 items-center">
              <div className="h-[180px] w-[180px] shrink-0">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={spendingByCategory} cx="50%" cy="50%" innerRadius={52} outerRadius={82} paddingAngle={2} dataKey="amount" stroke="none">
                      {spendingByCategory.map((_: any, i: number) => <Cell key={i} fill={CAT_COLORS[i % CAT_COLORS.length]} />)}
                    </Pie>
                    <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '8px', fontSize: '11px' }} formatter={(v: number) => [formatINR(v), 'Spent']} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="flex-1 space-y-1.5 overflow-y-auto max-h-[200px]">
                {spendingByCategory.slice(0, 10).map((item: any, i: number) => (
                  <div key={item.category} className="flex items-center gap-2 text-xs">
                    <div className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: CAT_COLORS[i % CAT_COLORS.length] }} />
                    <span className="text-muted-foreground flex-1 capitalize">{CATEGORY_LABELS[item.category] || item.category}</span>
                    <span className="font-mono font-semibold">{formatINR(item.amount)}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-32 text-muted-foreground text-sm">No spending data available</div>
          )}
          <div className="mt-4 pt-3 border-t border-border/30 grid grid-cols-3 gap-3 text-xs">
            <div><p className="text-muted-foreground">Total Debits</p><p className="font-mono font-bold text-destructive">{formatINR(summary.totalDebits)}</p></div>
            <div><p className="text-muted-foreground">Total Credits</p><p className="font-mono font-bold text-success">{formatINR(summary.totalCredits)}</p></div>
            <div><p className="text-muted-foreground">Net Flow</p><p className={`font-mono font-bold ${summary.totalCredits - summary.totalDebits >= 0 ? 'text-success' : 'text-destructive'}`}>{formatINR(Math.abs(summary.totalCredits - summary.totalDebits))}</p></div>
          </div>
        </Card>
      </div>

      {/* Risk Score History Chart */}
      <Card className="glass-panel p-6">
        <div className="flex items-center justify-between mb-1">
          <h3 className="font-semibold flex items-center gap-2"><TrendingUp className="w-4 h-4 text-primary" />Risk Score History</h3>
          <Badge variant="outline" className="text-xs">{riskHistory.length} snapshots</Badge>
        </div>
        <p className="text-xs text-muted-foreground mb-4">Historical risk score trajectory · Oldest to newest</p>
        {chartHistory.length > 1 ? (
          <div className="h-[220px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartHistory} margin={{ top: 5, right: 10, left: -25, bottom: 0 }}>
                <defs>
                  <linearGradient id="riskGradUser" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={getRiskColorHex(profile.riskLevel)} stopOpacity={0.3}/>
                    <stop offset="95%" stopColor={getRiskColorHex(profile.riskLevel)} stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="healthGradUser" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="hsl(142 71% 45%)" stopOpacity={0.2}/>
                    <stop offset="95%" stopColor="hsl(142 71% 45%)" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.15} />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} />
                <Tooltip
                  contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '8px', fontSize: '11px' }}
                  formatter={(v: number, name: string) => [v, name === 'score' ? 'Risk Score' : 'Health Score']}
                />
                <ReferenceLine y={60} stroke="hsl(346 84% 61%)" strokeDasharray="4 4" opacity={0.4} label={{ value: 'High Risk', position: 'right', fontSize: 9, fill: 'hsl(346 84% 61%)' }} />
                <ReferenceLine y={40} stroke="hsl(38 92% 50%)" strokeDasharray="4 4" opacity={0.4} label={{ value: 'Medium', position: 'right', fontSize: 9, fill: 'hsl(38 92% 50%)' }} />
                <Area type="monotone" dataKey="score" stroke={getRiskColorHex(profile.riskLevel)} fill="url(#riskGradUser)" strokeWidth={2.5} dot={{ r: 3, fill: getRiskColorHex(profile.riskLevel) }} name="score" />
                <Area type="monotone" dataKey="health" stroke="hsl(142 71% 45%)" fill="url(#healthGradUser)" strokeWidth={1.5} dot={false} name="health" strokeDasharray="4 2" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="h-28 flex items-center justify-center text-muted-foreground text-sm">Only {riskHistory.length} snapshot{riskHistory.length === 1 ? '' : 's'} available</div>
        )}
        {/* Risk history list */}
        {riskHistory.length > 0 && (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-xs">
              <thead><tr className="text-muted-foreground border-b border-border/30">
                <th className="text-left pb-2 font-medium">Date & Time</th>
                <th className="text-center pb-2 font-medium">Risk Score</th>
                <th className="text-center pb-2 font-medium">Level</th>
                <th className="text-center pb-2 font-medium">Health Score</th>
                <th className="text-center pb-2 font-medium">Confidence</th>
                <th className="text-left pb-2 font-medium">Segment</th>
              </tr></thead>
              <tbody className="divide-y divide-border/20">
                {riskHistory.slice(0, 10).map((r: any) => (
                  <tr key={r.id} className="hover:bg-white/5">
                    <td className="py-2 text-muted-foreground">{new Date(r.predictedAt).toLocaleString('en-IN', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })}</td>
                    <td className="py-2 text-center font-mono font-bold" style={{ color: getRiskColorHex(r.level) }}>{r.score}</td>
                    <td className="py-2 text-center"><Badge className={`text-[9px] uppercase py-0 px-1.5 ${getRiskColor(r.level)}`}>{r.level}</Badge></td>
                    <td className="py-2 text-center text-success font-mono">{r.financialHealthScore}</td>
                    <td className="py-2 text-center text-muted-foreground">{r.confidence ? `${(r.confidence * 100).toFixed(0)}%` : '—'}</td>
                    <td className="py-2 text-muted-foreground capitalize">{r.behaviorSegment?.replace(/_/g, ' ') || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Transactions + Alerts side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Transactions (takes 2/3 width) */}
        <Card className="glass-panel p-6 lg:col-span-2">
          <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
            <h3 className="font-semibold flex items-center gap-2"><CreditCard className="w-4 h-4 text-primary" />Transaction History</h3>
            <div className="flex gap-1.5">
              {(['all', 'debit', 'credit', 'stress'] as const).map(tab => (
                <button
                  key={tab}
                  onClick={() => { setTxTab(tab); setShowAllTx(false) }}
                  className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${txTab === tab ? 'bg-primary text-primary-foreground' : 'bg-secondary/40 text-muted-foreground hover:bg-secondary/60'}`}
                >
                  {tab === 'stress' ? '⚠ Stress' : tab.charAt(0).toUpperCase() + tab.slice(1)}
                </button>
              ))}
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead><tr className="text-muted-foreground border-b border-border/30">
                <th className="text-left pb-2 font-medium">Date</th>
                <th className="text-left pb-2 font-medium">Description</th>
                <th className="text-left pb-2 font-medium">Category</th>
                <th className="text-center pb-2 font-medium">Method</th>
                <th className="text-right pb-2 font-medium">Amount</th>
                <th className="text-right pb-2 font-medium">Balance</th>
              </tr></thead>
              <tbody className="divide-y divide-border/20">
                {displayedTx.map((t: any) => (
                  <tr key={t.id} className={`hover:bg-white/5 transition-colors ${t.isStressIndicator ? 'bg-warning/5' : ''}`}>
                    <td className="py-2 text-muted-foreground whitespace-nowrap">
                      {new Date(t.transactionDate).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}
                    </td>
                    <td className="py-2 max-w-[160px]">
                      <p className="truncate font-medium">{t.description || t.merchantName || '—'}</p>
                      {t.merchantCity && <p className="text-muted-foreground truncate">{t.merchantCity}</p>}
                    </td>
                    <td className="py-2">
                      <span className={`inline-flex items-center gap-1 ${t.isStressIndicator ? 'text-warning' : 'text-muted-foreground'}`}>
                        {t.isStressIndicator && '⚠ '}
                        {CATEGORY_LABELS[t.category] || t.category}
                      </span>
                    </td>
                    <td className="py-2 text-center text-muted-foreground uppercase">{t.paymentMethod || '—'}</td>
                    <td className={`py-2 text-right font-mono font-semibold ${t.type === 'credit' ? 'text-success' : 'text-foreground'}`}>
                      {t.type === 'credit' ? '+' : '-'}{formatINR(t.amount)}
                    </td>
                    <td className="py-2 text-right font-mono text-muted-foreground">{t.balanceAfter ? formatINR(t.balanceAfter) : '—'}</td>
                  </tr>
                ))}
                {filteredTx.length === 0 && (
                  <tr><td colSpan={6} className="py-6 text-center text-muted-foreground">No transactions in this category</td></tr>
                )}
              </tbody>
            </table>
          </div>
          {filteredTx.length > 10 && (
            <Button variant="ghost" size="sm" className="w-full mt-3 text-xs text-muted-foreground hover:text-foreground" onClick={() => setShowAllTx(v => !v)}>
              {showAllTx ? <><ChevronUp className="w-3.5 h-3.5 mr-1" />Show less</> : <><ChevronDown className="w-3.5 h-3.5 mr-1" />Show all {filteredTx.length} transactions</>}
            </Button>
          )}
        </Card>

        {/* Alerts */}
        <Card className="glass-panel p-6">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <Bell className="w-4 h-4 text-warning" />Alerts
            {summary.unreadAlerts > 0 && <Badge className="bg-destructive text-white text-[9px] px-1.5 py-0">{summary.unreadAlerts}</Badge>}
          </h3>
          <div className="space-y-2.5 max-h-[420px] overflow-y-auto">
            {alerts.length === 0 && (
              <div className="flex flex-col items-center py-8 text-muted-foreground gap-2">
                <CheckCircle2 className="w-8 h-8 text-success opacity-50" />
                <p className="text-xs">No alerts for this user</p>
              </div>
            )}
            {alerts.map((alert: any) => (
              <div key={alert.id} className={`p-3 rounded-xl border text-xs ${SEVERITY_STYLE[alert.severity] || 'bg-muted border-border'}`}>
                <div className="flex items-center justify-between mb-1">
                  <p className="font-semibold">{alert.title}</p>
                  <div className="flex items-center gap-1.5">
                    {!alert.isRead && <div className="w-1.5 h-1.5 rounded-full bg-current opacity-70"></div>}
                    <Badge variant="outline" className="text-[9px] py-0 px-1">{alert.severity}</Badge>
                  </div>
                </div>
                <p className="opacity-80 leading-relaxed">{alert.message}</p>
                <p className="mt-1 opacity-50 flex items-center gap-1">
                  <Clock className="w-2.5 h-2.5" />
                  {new Date(alert.createdAt).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
                </p>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Interventions */}
      {interventions.length > 0 && (
        <Card className="glass-panel p-6">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <FileText className="w-4 h-4 text-primary" />Intervention History
            <Badge variant="outline" className="text-xs ml-1">{interventions.length}</Badge>
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead><tr className="text-muted-foreground border-b border-border/30">
                <th className="text-left pb-2 font-medium">Type</th>
                <th className="text-center pb-2 font-medium">Status</th>
                <th className="text-center pb-2 font-medium">Priority</th>
                <th className="text-left pb-2 font-medium">Notes</th>
                <th className="text-left pb-2 font-medium">Assigned To</th>
                <th className="text-right pb-2 font-medium">Created</th>
              </tr></thead>
              <tbody className="divide-y divide-border/20">
                {interventions.map((iv: any) => (
                  <tr key={iv.id} className="hover:bg-white/5">
                    <td className="py-2.5 font-medium capitalize">{iv.type?.replace(/_/g, ' ')}</td>
                    <td className="py-2.5 text-center">
                      <Badge variant="outline" className={`text-[9px] py-0 px-1.5 capitalize ${STATUS_STYLE[iv.status] || ''}`}>{iv.status}</Badge>
                    </td>
                    <td className="py-2.5 text-center">
                      <Badge variant="outline" className="text-[9px] py-0 px-1.5 capitalize">{iv.priority}</Badge>
                    </td>
                    <td className="py-2.5 text-muted-foreground max-w-[200px] truncate">{iv.notes || iv.description || '—'}</td>
                    <td className="py-2.5 text-muted-foreground">{iv.assignedTo || '—'}</td>
                    <td className="py-2.5 text-right text-muted-foreground whitespace-nowrap">
                      {new Date(iv.createdAt).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  )
}

function DetailSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="flex items-center gap-4">
        <Skeleton className="w-10 h-10 rounded-xl bg-secondary" />
        <div><Skeleton className="w-48 h-7 rounded-lg bg-secondary mb-2" /><Skeleton className="w-72 h-4 rounded bg-secondary" /></div>
      </div>
      <div className="grid grid-cols-6 gap-3">{[...Array(6)].map((_,i) => <Skeleton key={i} className="h-24 rounded-2xl bg-secondary" />)}</div>
      <div className="grid grid-cols-3 gap-6"><Skeleton className="h-72 rounded-2xl bg-secondary" /><Skeleton className="h-72 rounded-2xl bg-secondary col-span-2" /></div>
      <Skeleton className="h-64 rounded-2xl bg-secondary" />
    </div>
  )
}
