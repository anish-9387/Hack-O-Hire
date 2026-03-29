import { useExplainRisk, useGetRiskScore, usePredictFutureRisk } from "@/lib/api-client"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Progress } from "@/components/ui/progress"
import { 
  ShieldAlert, ThumbsUp, AlertTriangle, Lightbulb, TrendingUp, TrendingDown,
  Activity, Brain, Clock, CheckCircle2, ArrowRight
} from "lucide-react"
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, Cell
} from "recharts"
import { motion } from "framer-motion"
import { useLocation } from "wouter"
import { getRiskColor, getRiskColorHex } from "@/lib/utils"

const FEATURE_LABELS: Record<string, { label: string; description: string; icon: string }> = {
  debtToIncomeRatio: { label: 'Debt-to-Income Ratio', description: 'Total debt obligations as percentage of monthly income', icon: '📊' },
  paymentToIncomeRatio: { label: 'EMI Burden', description: 'EMI payments as percentage of total income', icon: '🏠' },
  creditUtilisation: { label: 'Credit Utilisation', description: 'Percentage of available credit being used', icon: '💳' },
  daysPastDue: { label: 'Overdue Payments', description: 'Number of days past due on loan payments', icon: '⏰' },
  latePayments: { label: 'Late Payments', description: 'Number of late payments in last 12 months', icon: '❌' },
  previousDefault: { label: 'Previous Default', description: 'History of loan default on record', icon: '⚠️' },
  hardEnquiries: { label: 'Credit Enquiries', description: 'Number of hard credit pulls in last 12 months', icon: '🔍' },
  loanToValueRatio: { label: 'Loan-to-Value', description: 'Loan amount relative to asset value', icon: '🏦' },
  lowCibilScore: { label: 'Low CIBIL Score', description: 'Credit bureau score below healthy threshold', icon: '📉' },
  incomeConsistency: { label: 'Income Stability', description: 'Regularity and consistency of income credits', icon: '📊' },
  utilityPaymentScore: { label: 'Utility Payments', description: 'Track record of on-time utility bill payments', icon: '💡' },
  digitalEngagement: { label: 'Digital Activity', description: 'Usage of digital banking and payment platforms', icon: '📱' },
  highCibilScore: { label: 'Strong Credit Score', description: 'CIBIL score above 700 indicates good creditworthiness', icon: '✅' },
}

export default function RiskExplanation() {
  const { data, isLoading } = useExplainRisk()
  const { data: score } = useGetRiskScore()
  const { data: prediction } = usePredictFutureRisk()
  const [, setLocation] = useLocation()

  if (isLoading) return (
    <div className="space-y-6 animate-pulse">
      <Skeleton className="h-32 rounded-2xl bg-secondary" />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Skeleton className="h-[500px] rounded-2xl bg-secondary" />
        <Skeleton className="h-[500px] rounded-2xl bg-secondary" />
      </div>
    </div>
  )

  if (!data) return <div className="text-destructive p-8 text-center">Failed to load risk explanation. Please refresh.</div>

  const riskScore = score?.score ?? data.overallScore
  const riskLevel = score?.level ?? (riskScore >= 70 ? 'critical' : riskScore >= 50 ? 'high' : riskScore >= 30 ? 'medium' : 'low')

  const allFactors = [...(data.topFactors || []), ...(data.protectiveFactors || [])]
  
  const chartData = allFactors
    .sort((a, b) => Math.abs(b.impact) - Math.abs(a.impact))
    .map(f => {
      const meta = FEATURE_LABELS[f.feature] || { label: f.feature.replace(/([A-Z])/g, ' $1').trim(), description: '', icon: '📌' }
      return {
        label: meta.label,
        impact: Math.abs(f.impact),
        rawImpact: f.impact,
        type: f.direction,
        feature: f.feature,
        meta,
        fill: f.direction === 'increases_risk' ? 'hsl(var(--destructive))' : 'hsl(142 71% 45%)',
      }
    })
    .slice(0, 8)

  const maxImpact = Math.max(...chartData.map(d => d.impact))

  return (
    <div className="space-y-6 pb-8">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-display font-bold tracking-tight flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary/20 flex items-center justify-center">
              <Brain className="w-5 h-5 text-primary" />
            </div>
            AI Risk X-Ray
          </h1>
          <p className="text-muted-foreground mt-2 ml-14">SHAP-based explainability · {chartData.length} key factors identified</p>
        </div>
        <Button variant="outline" size="sm" className="shrink-0 rounded-xl" onClick={() => setLocation('/simulate')}>
          <Activity className="w-4 h-4 mr-2" />Run What-If
        </Button>
      </div>

      {/* Risk Overview Banner */}
      <Card className={`glass-panel p-5 border-l-4 ${
        riskLevel === 'critical' ? 'border-l-destructive' :
        riskLevel === 'high' ? 'border-l-orange-500' :
        riskLevel === 'medium' ? 'border-l-warning' : 'border-l-success'
      }`}>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="text-center">
              <div className="text-5xl font-display font-bold tracking-tighter" style={{ color: getRiskColorHex(riskLevel) }}>
                {riskScore}
              </div>
              <div className="text-xs text-muted-foreground mt-1">Risk Score</div>
            </div>
            <div>
              <Badge className={`text-sm px-4 py-1.5 font-bold uppercase tracking-wider ${getRiskColor(riskLevel)}`}>
                {riskLevel} Risk
              </Badge>
              <p className="text-sm text-muted-foreground mt-2 max-w-md leading-relaxed">{data.summary}</p>
            </div>
          </div>
          <div className="flex flex-col gap-2 text-sm shrink-0">
            <div className="flex items-center gap-2 p-2 rounded-lg bg-destructive/10 border border-destructive/20">
              <AlertTriangle className="w-3.5 h-3.5 text-destructive" />
              <span className="text-xs text-destructive font-medium">{data.topFactors?.length || 0} risk factors detected</span>
            </div>
            <div className="flex items-center gap-2 p-2 rounded-lg bg-success/10 border border-success/20">
              <ThumbsUp className="w-3.5 h-3.5 text-success" />
              <span className="text-xs text-success font-medium">{data.protectiveFactors?.length || 0} protective factors</span>
            </div>
            {prediction && (
              <div className={`flex items-center gap-2 p-2 rounded-lg ${prediction.overallTrend === 'deteriorating' ? 'bg-warning/10 border-warning/20' : 'bg-info/10 border-info/20'}`}>
                {prediction.overallTrend === 'deteriorating' ? <TrendingDown className="w-3.5 h-3.5 text-warning" /> : <TrendingUp className="w-3.5 h-3.5 text-info" />}
                <span className={`text-xs font-medium capitalize ${prediction.overallTrend === 'deteriorating' ? 'text-warning' : 'text-info'}`}>
                  Trend: {prediction.overallTrend}
                </span>
              </div>
            )}
          </div>
        </div>
      </Card>

      {/* SHAP Factors + Radar */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* SHAP Impact Chart */}
        <Card className="glass-panel p-6 lg:col-span-2">
          <h3 className="font-semibold mb-0.5 flex items-center gap-2">
            <Activity className="w-4 h-4 text-primary" />
            Feature Impact Analysis (SHAP Values)
          </h3>
          <p className="text-xs text-muted-foreground mb-5">How each factor contributes to your risk score</p>
          <div className="h-[320px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} layout="vertical" margin={{ top: 0, right: 30, left: 10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} opacity={0.15} />
                <XAxis type="number" tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} domain={[0, maxImpact * 1.15]} />
                <YAxis dataKey="label" type="category" tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }} width={115} />
                <Tooltip
                  contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '8px', fontSize: '12px' }}
                  formatter={(val: number, _: string, props: any) => [
                    `${val.toFixed(2)} pts ${props.payload.type === 'increases_risk' ? '↑ risk' : '↓ risk'}`,
                    'SHAP Impact'
                  ]}
                />
                <Bar dataKey="impact" radius={[0, 4, 4, 0]}>
                  {chartData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="flex items-center gap-6 mt-4 text-xs text-muted-foreground">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-destructive"></div>
              <span>Increases risk</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-success"></div>
              <span>Reduces risk (protective)</span>
            </div>
          </div>
        </Card>

        {/* Factor Summary Cards */}
        <div className="space-y-4">
          <Card className="glass-panel p-5">
            <h3 className="font-semibold text-sm mb-3 flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-destructive" />Risk Factors
            </h3>
            <div className="space-y-3">
              {data.topFactors?.slice(0, 4).map((f: any, i: number) => {
                const meta = FEATURE_LABELS[f.feature] || { label: f.feature.replace(/([A-Z])/g, ' $1').trim(), icon: '⚠️', description: '' }
                return (
                  <motion.div key={f.feature} initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.08 }}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-medium flex items-center gap-1.5">
                        <span>{meta.icon}</span>{meta.label}
                      </span>
                      <span className="text-xs font-mono font-bold text-destructive">+{f.impact.toFixed(1)}</span>
                    </div>
                    <Progress value={(f.impact / maxImpact) * 100} className="h-1.5 [&>div]:bg-destructive" />
                    <p className="text-[10px] text-muted-foreground mt-1 leading-relaxed">{meta.description}</p>
                  </motion.div>
                )
              })}
            </div>
          </Card>

          <Card className="glass-panel p-5">
            <h3 className="font-semibold text-sm mb-3 flex items-center gap-2">
              <ThumbsUp className="w-4 h-4 text-success" />Protective Factors
            </h3>
            <div className="space-y-3">
              {data.protectiveFactors?.slice(0, 3).map((f: any, i: number) => {
                const meta = FEATURE_LABELS[f.feature] || { label: f.feature.replace(/([A-Z])/g, ' $1').trim(), icon: '✅', description: '' }
                return (
                  <motion.div key={f.feature} initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.08 }}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-medium flex items-center gap-1.5">
                        <span>{meta.icon}</span>{meta.label}
                      </span>
                      <span className="text-xs font-mono font-bold text-success">-{f.impact.toFixed(1)}</span>
                    </div>
                    <Progress value={(f.impact / maxImpact) * 100} className="h-1.5 [&>div]:bg-success" />
                    <p className="text-[10px] text-muted-foreground mt-1 leading-relaxed">{meta.description}</p>
                  </motion.div>
                )
              })}
            </div>
          </Card>
        </div>
      </div>

      {/* Detailed Factor Table + Recommendations */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="glass-panel p-6">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <Activity className="w-4 h-4 text-primary" />All Risk Factors — Detailed View
          </h3>
          <div className="space-y-3">
            {chartData.map((f, i) => (
              <motion.div 
                key={f.feature}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: i * 0.05 }}
                className={`flex items-start gap-3 p-3 rounded-xl border transition-colors ${
                  f.type === 'increases_risk' 
                    ? 'bg-destructive/5 border-destructive/20 hover:bg-destructive/10' 
                    : 'bg-success/5 border-success/20 hover:bg-success/10'
                }`}
              >
                <span className="text-lg leading-none">{f.meta.icon}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium text-sm">{f.meta.label}</span>
                    <span className={`font-mono font-bold text-sm ${f.type === 'increases_risk' ? 'text-destructive' : 'text-success'}`}>
                      {f.type === 'increases_risk' ? '+' : '-'}{f.impact.toFixed(2)}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">{f.meta.description}</p>
                  <div className="mt-1.5 flex items-center gap-2">
                    <div className={`flex-1 h-1.5 rounded-full overflow-hidden bg-secondary/60`}>
                      <div 
                        className={`h-full rounded-full transition-all`} 
                        style={{ 
                          width: `${(f.impact / maxImpact) * 100}%`,
                          backgroundColor: f.type === 'increases_risk' ? 'hsl(var(--destructive))' : 'hsl(142 71% 45%)'
                        }} 
                      />
                    </div>
                    <Badge variant="outline" className={`text-[10px] py-0 px-1.5 ${f.type === 'increases_risk' ? 'text-destructive border-destructive/30' : 'text-success border-success/30'}`}>
                      {f.type === 'increases_risk' ? '↑ Risk' : '↓ Risk'}
                    </Badge>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </Card>

        <div className="space-y-4">
          {/* AI Recommendations */}
          <Card className="glass-panel p-6">
            <h3 className="font-semibold mb-4 flex items-center gap-2">
              <Lightbulb className="w-4 h-4 text-warning" />AI-Powered Recommendations
            </h3>
            <div className="space-y-3">
              {data.recommendations?.map((rec: string, i: number) => (
                <motion.div 
                  key={i}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.1 }}
                  className="flex items-start gap-3 p-3.5 rounded-xl bg-primary/5 border border-primary/20 hover:bg-primary/10 transition-colors"
                >
                  <div className="w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center text-primary text-xs font-bold shrink-0 mt-0.5">
                    {i + 1}
                  </div>
                  <p className="text-sm text-foreground/90 leading-relaxed">{rec}</p>
                </motion.div>
              ))}
            </div>
          </Card>

          {/* 4-Week Prediction */}
          {prediction && (
            <Card className="glass-panel p-5">
              <h3 className="font-semibold text-sm mb-3 flex items-center gap-2">
                <Clock className="w-4 h-4 text-primary" />4-Week Risk Forecast
              </h3>
              <div className="space-y-2.5">
                {prediction.predictions?.map((p: any) => (
                  <div key={p.week} className="flex items-center gap-3">
                    <span className="text-xs text-muted-foreground w-10">Week {p.week}</span>
                    <div className="flex-1 h-2 bg-secondary/60 rounded-full overflow-hidden">
                      <div className="h-full rounded-full transition-all" style={{ width: `${p.predictedScore}%`, backgroundColor: getRiskColorHex(p.predictedLevel) }} />
                    </div>
                    <span className="text-xs font-mono font-bold w-8 text-right" style={{ color: getRiskColorHex(p.predictedLevel) }}>{p.predictedScore}</span>
                    <Badge className={`text-[9px] px-1.5 py-0 capitalize ${getRiskColor(p.predictedLevel)}`}>{p.predictedLevel}</Badge>
                  </div>
                ))}
              </div>
              {prediction.keyRisks?.length > 0 && (
                <div className="mt-4 p-3 rounded-xl bg-warning/10 border border-warning/20">
                  <p className="text-xs font-semibold text-warning mb-1.5">⚠️ Key Upcoming Risks</p>
                  {prediction.keyRisks.slice(0, 2).map((r: string, i: number) => (
                    <p key={i} className="text-xs text-muted-foreground leading-relaxed">• {r}</p>
                  ))}
                </div>
              )}
              <Button variant="ghost" className="w-full mt-4 text-xs h-8 text-primary hover:bg-primary/10" onClick={() => setLocation('/simulate')}>
                Test Scenarios <ArrowRight className="w-3 h-3 ml-1" />
              </Button>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
