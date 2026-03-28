import { useState } from "react"
import { useGetDashboardOverview, usePredictFutureRisk, useListAlerts, useGetRiskScore } from "@/lib/api-client"
import { formatINR, getRiskColor, getRiskColorHex } from "@/lib/utils"
import { Gauge } from "@/components/ui/gauge"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { 
  ArrowUpRight, ArrowDownRight, Wallet, TrendingUp, BellRing, CreditCard,
  ShoppingBag, Home, Coffee, Zap, Activity, RefreshCw, AlertTriangle,
  CheckCircle2, Info, TrendingDown, Target, IndianRupee, Clock
} from "lucide-react"
import { 
  ResponsiveContainer, AreaChart, Area, Tooltip, XAxis, PieChart, Pie, Cell,
  LineChart, Line, YAxis, CartesianGrid, ReferenceLine
} from "recharts"
import { motion, AnimatePresence } from "framer-motion"
import { useLocation } from "wouter"

const getCategoryIcon = (category: string) => {
  switch(category) {
    case 'salary': return <IndianRupee className="w-4 h-4 text-success" />
    case 'grocery': return <ShoppingBag className="w-4 h-4 text-info" />
    case 'food_delivery': return <Coffee className="w-4 h-4 text-warning" />
    case 'rent': return <Home className="w-4 h-4 text-purple-500" />
    case 'utility_bill': return <Zap className="w-4 h-4 text-orange-500" />
    case 'loan_app': return <AlertTriangle className="w-4 h-4 text-destructive" />
    case 'atm_withdrawal': return <Wallet className="w-4 h-4 text-orange-400" />
    case 'emi_payment': return <TrendingDown className="w-4 h-4 text-warning" />
    case 'festival_shopping': return <ShoppingBag className="w-4 h-4 text-pink-500" />
    default: return <CreditCard className="w-4 h-4 text-muted-foreground" />
  }
}

const RISK_COLORS = {
  low: 'hsl(142 71% 45%)',
  medium: 'hsl(38 92% 50%)',
  high: 'hsl(24 98% 50%)',
  critical: 'hsl(346 84% 61%)',
}

export default function UserDashboard() {
  const [, setLocation] = useLocation()
  const { data, isLoading, refetch } = useGetDashboardOverview()
  const { data: prediction } = usePredictFutureRisk()
  const { data: alerts } = useListAlerts({ unreadOnly: true })
  const { data: liveScore, refetch: refetchScore, isFetching: scoreRefreshing } = useGetRiskScore()

  const CHART_COLORS = ['hsl(var(--chart-1))', 'hsl(var(--chart-2))', 'hsl(var(--chart-3))', 'hsl(var(--chart-4))', 'hsl(var(--chart-5))']

  if (isLoading) return <DashboardSkeleton />
  if (!data) return <div className="text-destructive p-8 text-center bg-destructive/10 rounded-2xl border border-destructive/20">Failed to load dashboard. Please refresh.</div>

  const riskScore = liveScore?.score ?? data.currentRiskScore.score
  const riskLevel = liveScore?.level ?? data.currentRiskScore.level
  const healthScore = liveScore?.financialHealthScore ?? data.currentRiskScore.financialHealthScore

  const predictionChartData = [
    { label: 'Today', score: riskScore, projected: false },
    ...(prediction?.predictions?.map(p => ({
      label: `Wk ${p.week}`,
      score: p.predictedScore,
      projected: true,
      confidence: p.confidence,
    })) || [])
  ]

  const unreadAlerts = Array.isArray(alerts) ? alerts.filter((a: any) => !a.isRead) : []
  const savingsTarget = 30
  const savingsGap = Math.max(0, savingsTarget - (data.savingsRate || 0))

  return (
    <div className="space-y-6 pb-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-display font-bold tracking-tight">
            Welcome back, {data.user.name.split(' ')[0]} 👋
          </h1>
          <p className="text-muted-foreground mt-1">
            {data.user.city}, {data.user.state} · {data.user.employmentType?.replace('_', ' ')}
          </p>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          {unreadAlerts.length > 0 && (
            <Badge className="bg-destructive/20 text-destructive border-destructive/30 px-3 py-1.5 animate-pulse">
              <BellRing className="w-3 h-3 mr-1.5" />
              {unreadAlerts.length} Alert{unreadAlerts.length > 1 ? 's' : ''}
            </Badge>
          )}
          <Button
            variant="outline"
            size="sm"
            className="border-border/50 bg-secondary/20 hover:bg-secondary/40 rounded-xl"
            onClick={() => { refetchScore(); refetch() }}
            disabled={scoreRefreshing}
          >
            <RefreshCw className={`w-3.5 h-3.5 mr-2 ${scoreRefreshing ? 'animate-spin' : ''}`} />
            Refresh Score
          </Button>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-success/10 border border-success/20">
            <div className="w-2 h-2 rounded-full bg-success animate-pulse"></div>
            <span className="text-xs font-medium text-success uppercase tracking-wider">Live</span>
          </div>
        </div>
      </div>

      {/* Active Alerts Banner */}
      <AnimatePresence>
        {unreadAlerts.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: -12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            className="space-y-2"
          >
            {unreadAlerts.slice(0, 2).map((alert: any) => (
              <div
                key={alert.id}
                className={`flex items-start gap-3 p-4 rounded-xl border ${
                  alert.severity === 'critical' ? 'bg-destructive/10 border-destructive/30 text-destructive' :
                  alert.severity === 'warning' ? 'bg-warning/10 border-warning/30 text-warning' :
                  'bg-info/10 border-info/30 text-info'
                }`}
              >
                <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-sm">{alert.title}</p>
                  <p className="text-xs opacity-80 mt-0.5 leading-relaxed">{alert.message}</p>
                </div>
                <Badge variant="outline" className="text-[10px] uppercase shrink-0">{alert.severity}</Badge>
              </div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Metrics Row */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Health Score Gauge */}
        <Card className="glass-panel p-6 lg:col-span-4 flex flex-col items-center justify-center relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-64 h-64 bg-primary/5 rounded-full blur-3xl -mr-20 -mt-20 pointer-events-none"></div>
          <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground w-full text-left mb-4">Financial Health Score</h3>
          <Gauge 
            value={healthScore} 
            level={riskLevel}
            label="Health"
            size={200}
          />
          <div className="mt-4 flex flex-col items-center w-full">
            <Badge className={`px-4 py-1.5 text-sm uppercase tracking-widest font-bold ${getRiskColor(riskLevel)}`}>
              {riskLevel} RISK
            </Badge>
            <p className="text-xs text-center text-muted-foreground mt-3 px-2 leading-relaxed">
              Risk Score: <span className="font-bold text-foreground">{riskScore}/100</span> · Confidence: <span className="font-bold text-foreground">{Math.round((liveScore?.confidence ?? data.currentRiskScore.confidence) * 100)}%</span>
            </p>
            <div className="w-full mt-4 space-y-2">
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>Savings Rate</span>
                <span className={data.savingsRate < 10 ? 'text-destructive font-semibold' : 'text-success font-semibold'}>{data.savingsRate}%</span>
              </div>
              <Progress value={data.savingsRate} className="h-1.5" />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>Target: {savingsTarget}%</span>
                {savingsGap > 0 && <span className="text-warning">{savingsGap}% gap</span>}
              </div>
            </div>
          </div>
        </Card>

        {/* Metric Cards */}
        <div className="lg:col-span-8 grid grid-cols-1 sm:grid-cols-2 gap-5">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
            <Card className="glass-panel p-5 h-full flex flex-col justify-between hover:shadow-glow transition-shadow">
              <div className="flex items-center gap-3 text-muted-foreground mb-3">
                <div className="p-2 rounded-xl bg-info/10"><Wallet className="w-5 h-5 text-info" /></div>
                <h3 className="font-medium text-sm">Total Balance</h3>
              </div>
              <div>
                <div className="text-3xl font-display font-bold tracking-tight">{formatINR(data.totalBalance)}</div>
                <div className="flex items-center gap-2 mt-2 text-sm">
                  <span className={`flex items-center px-2 py-0.5 rounded text-xs font-semibold ${data.totalBalance > 0 ? 'text-success bg-success/10' : 'text-destructive bg-destructive/10'}`}>
                    {data.totalBalance > 0 ? <ArrowUpRight className="w-3 h-3 mr-1" /> : <ArrowDownRight className="w-3 h-3 mr-1" />}
                    {data.user.city}
                  </span>
                  <span className="text-muted-foreground">across accounts</span>
                </div>
              </div>
            </Card>
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
            <Card className="glass-panel p-5 h-full flex flex-col justify-between hover:shadow-glow transition-shadow">
              <div className="flex items-center gap-3 text-muted-foreground mb-3">
                <div className="p-2 rounded-xl bg-success/10"><TrendingUp className="w-5 h-5 text-success" /></div>
                <h3 className="font-medium text-sm">Monthly Savings</h3>
              </div>
              <div>
                <div className={`text-3xl font-display font-bold tracking-tight ${data.savingsRate <= 0 ? 'text-destructive' : 'text-success'}`}>
                  {data.savingsRate}%
                </div>
                <div className="mt-2 text-sm text-muted-foreground">
                  {data.savingsRate > 0 
                    ? <>{formatINR((data.monthlyIncome || 0) - data.monthlyExpenses)} <span className="text-success">saved this month</span></>
                    : <span className="text-destructive">Spending exceeds income ⚠️</span>
                  }
                </div>
              </div>
            </Card>
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
            <Card className="glass-panel p-5 h-full flex flex-col justify-between hover:shadow-glow transition-shadow">
              <div className="flex items-center gap-3 text-muted-foreground mb-3">
                <div className="p-2 rounded-xl bg-warning/10"><ArrowUpRight className="w-5 h-5 text-warning" /></div>
                <h3 className="font-medium text-sm">Monthly Expenses</h3>
              </div>
              <div>
                <div className="text-3xl font-display font-bold tracking-tight">{formatINR(data.monthlyExpenses)}</div>
                <div className="mt-2 text-sm text-muted-foreground">
                  Income: <span className="font-semibold text-foreground">{formatINR(data.monthlyIncome || 0)}</span>
                </div>
              </div>
            </Card>
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}>
            <Card className="glass-panel p-5 h-full flex flex-col justify-between hover:shadow-glow transition-shadow">
              <div className="flex items-center gap-3 text-muted-foreground mb-3">
                <div className="p-2 rounded-xl bg-primary/10"><BellRing className="w-5 h-5 text-primary" /></div>
                <h3 className="font-medium text-sm">Active Alerts</h3>
              </div>
              <div>
                <div className={`text-3xl font-display font-bold tracking-tight ${unreadAlerts.length > 0 ? 'text-destructive' : 'text-success'}`}>
                  {unreadAlerts.length}
                </div>
                <div className="mt-2 text-sm text-muted-foreground">
                  {unreadAlerts.length > 0 
                    ? <span className="text-destructive">Require your attention</span>
                    : <span className="text-success">All clear!</span>
                  }
                </div>
              </div>
            </Card>
          </motion.div>
        </div>
      </div>

      {/* Risk Trend + 4-Week Prediction */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <Card className="glass-panel p-6 lg:col-span-3">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h3 className="font-semibold flex items-center gap-2">
                <Activity className="w-5 h-5 text-primary" />
                Risk Trend & 4-Week Forecast
              </h3>
              <p className="text-xs text-muted-foreground mt-0.5">Historical + AI-predicted trajectory</p>
            </div>
            <div className="flex items-center gap-4 text-xs text-muted-foreground">
              <div className="flex items-center gap-1.5"><div className="w-3 h-0.5 bg-primary rounded-full"></div>Historical</div>
              <div className="flex items-center gap-1.5"><div className="w-3 h-0.5 bg-warning rounded-full border-dashed"></div>Predicted</div>
            </div>
          </div>
          <div className="h-[180px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={[...data.riskTrend.slice(-6), ...predictionChartData.slice(1)]} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.15} />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} tickFormatter={(v) => v ? new Date(v).toLocaleDateString('en-IN', {day:'numeric', month:'short'}) : ''} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} />
                <Tooltip
                  contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '8px', fontSize: '12px' }}
                  formatter={(val: number) => [val, 'Risk Score']}
                />
                <ReferenceLine y={50} stroke="hsl(var(--warning))" strokeDasharray="3 3" strokeOpacity={0.5} />
                <Line type="monotone" dataKey="score" stroke="hsl(var(--primary))" strokeWidth={2.5} dot={false} activeDot={{ r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          {prediction && (
            <div className="mt-4 flex items-center gap-4 text-sm">
              <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg ${
                prediction.overallTrend === 'deteriorating' ? 'bg-destructive/10 text-destructive' :
                prediction.overallTrend === 'improving' ? 'bg-success/10 text-success' :
                'bg-secondary/50 text-muted-foreground'
              }`}>
                {prediction.overallTrend === 'deteriorating' ? <TrendingDown className="w-4 h-4" /> :
                 prediction.overallTrend === 'improving' ? <TrendingUp className="w-4 h-4" /> :
                 <Activity className="w-4 h-4" />}
                <span className="font-medium capitalize">Trend: {prediction.overallTrend}</span>
              </div>
              {prediction.keyRisks?.[0] && (
                <p className="text-xs text-muted-foreground line-clamp-1 flex-1">
                  ⚠️ {prediction.keyRisks[0]}
                </p>
              )}
            </div>
          )}
        </Card>

        {/* Spending Breakdown */}
        <Card className="glass-panel p-6 lg:col-span-2 flex flex-col">
          <h3 className="font-semibold mb-4">Spending Breakdown</h3>
          <div className="h-[160px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data.spendingBreakdown}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={75}
                  paddingAngle={3}
                  dataKey="amount"
                  stroke="none"
                >
                  {data.spendingBreakdown?.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip 
                  formatter={(value: number) => [formatINR(value), 'Amount']}
                  contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '8px', fontSize: '12px' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-3 space-y-1.5 flex-1">
            {data.spendingBreakdown?.slice(0, 5).map((item, idx) => (
              <div key={item.category} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: CHART_COLORS[idx % CHART_COLORS.length] }}></div>
                  <span className="capitalize text-muted-foreground">{item.category.replace(/_/g, ' ')}</span>
                </div>
                <span className="font-semibold">{item.percentage}%</span>
              </div>
            ))}
          </div>
          <Button 
            variant="ghost" 
            size="sm" 
            className="mt-4 w-full text-xs text-primary hover:bg-primary/10" 
            onClick={() => setLocation('/analytics')}
          >
            Full Analytics →
          </Button>
        </Card>
      </div>

      {/* Transactions + Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Transactions */}
        <Card className="glass-panel p-6 lg:col-span-2 flex flex-col">
          <div className="flex items-center justify-between mb-5">
            <h3 className="font-semibold">Recent Transactions</h3>
            <Button variant="ghost" size="sm" className="text-xs text-primary hover:bg-primary/10 h-auto py-1.5" onClick={() => setLocation('/transactions')}>
              View All →
            </Button>
          </div>
          <div className="space-y-2 flex-1">
            {data.recentTransactions?.slice(0, 6).map((tx) => (
              <motion.div 
                key={tx.id} 
                initial={{ opacity: 0, x: -10 }} 
                animate={{ opacity: 1, x: 0 }}
                className={`flex items-center justify-between p-3 rounded-xl transition-colors border ${
                  tx.isStressIndicator 
                    ? 'border-destructive/20 bg-destructive/5 hover:bg-destructive/10' 
                    : 'border-transparent hover:bg-white/5 hover:border-border/50'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-full bg-secondary flex items-center justify-center border border-border shrink-0">
                    {getCategoryIcon(tx.category)}
                  </div>
                  <div>
                    <p className="font-medium text-sm text-foreground flex items-center gap-2">
                      {tx.merchantName || tx.description || tx.category.replace(/_/g, ' ')}
                      {tx.isStressIndicator && (
                        <span className="text-[10px] bg-destructive/20 text-destructive px-1.5 py-0.5 rounded-full font-semibold">STRESS</span>
                      )}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {new Date(tx.transactionDate).toLocaleDateString('en-IN', {day:'numeric', month:'short'})} · {tx.paymentMethod?.toUpperCase() || 'UPI'}
                    </p>
                  </div>
                </div>
                <div className={`font-semibold font-mono text-sm ${tx.type === 'credit' ? 'text-success' : tx.isStressIndicator ? 'text-destructive' : 'text-foreground'}`}>
                  {tx.type === 'credit' ? '+' : '-'}{formatINR(tx.amount)}
                </div>
              </motion.div>
            ))}
          </div>
        </Card>

        {/* Quick Actions + Prediction Preview */}
        <div className="space-y-5">
          {/* Next 4 Weeks */}
          {prediction && (
            <Card className="glass-panel p-5">
              <h3 className="font-semibold text-sm mb-4 flex items-center gap-2">
                <Clock className="w-4 h-4 text-primary" />
                4-Week Forecast
              </h3>
              <div className="space-y-2.5">
                {prediction.predictions?.map((p: any) => (
                  <div key={p.week} className="flex items-center gap-3">
                    <span className="text-xs text-muted-foreground w-8">Wk {p.week}</span>
                    <div className="flex-1 h-2 bg-secondary/60 rounded-full overflow-hidden">
                      <div 
                        className="h-full rounded-full transition-all duration-700" 
                        style={{ 
                          width: `${p.predictedScore}%`,
                          backgroundColor: getRiskColorHex(p.predictedLevel)
                        }}
                      />
                    </div>
                    <span className="text-xs font-mono font-semibold w-8 text-right" style={{ color: getRiskColorHex(p.predictedLevel) }}>
                      {p.predictedScore}
                    </span>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Quick Navigate */}
          <Card className="glass-panel p-5">
            <h3 className="font-semibold text-sm mb-4 flex items-center gap-2">
              <Target className="w-4 h-4 text-primary" />
              Quick Actions
            </h3>
            <div className="grid grid-cols-2 gap-2">
              {[
                { label: 'Risk X-Ray', icon: <Activity className="w-4 h-4" />, path: '/risk', color: 'text-primary bg-primary/10 hover:bg-primary/20 border-primary/20' },
                { label: 'AI Coach', icon: <CheckCircle2 className="w-4 h-4" />, path: '/coach', color: 'text-success bg-success/10 hover:bg-success/20 border-success/20' },
                { label: 'What-If', icon: <TrendingUp className="w-4 h-4" />, path: '/simulate', color: 'text-warning bg-warning/10 hover:bg-warning/20 border-warning/20' },
                { label: 'Transactions', icon: <CreditCard className="w-4 h-4" />, path: '/transactions', color: 'text-info bg-info/10 hover:bg-info/20 border-info/20' },
              ].map(action => (
                <button
                  key={action.path}
                  onClick={() => setLocation(action.path)}
                  className={`flex flex-col items-center gap-2 p-3 rounded-xl border text-center transition-all cursor-pointer ${action.color}`}
                >
                  {action.icon}
                  <span className="text-xs font-medium">{action.label}</span>
                </button>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}

function DashboardSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="w-80 h-10 bg-secondary rounded-lg"></div>
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <Skeleton className="h-[350px] rounded-2xl bg-secondary lg:col-span-4" />
        <div className="lg:col-span-8 grid grid-cols-2 gap-5">
          {[1,2,3,4].map(i => <Skeleton key={i} className="h-[150px] rounded-2xl bg-secondary" />)}
        </div>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <Skeleton className="h-[280px] rounded-2xl bg-secondary lg:col-span-3" />
        <Skeleton className="h-[280px] rounded-2xl bg-secondary lg:col-span-2" />
      </div>
    </div>
  )
}
