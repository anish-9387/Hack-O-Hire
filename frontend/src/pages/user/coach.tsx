import { useGetFinancialAdvice, useGetRiskScore, usePredictFutureRisk } from "@/lib/api-client"
import { formatINR, getRiskColor, getRiskColorHex } from "@/lib/utils"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Progress } from "@/components/ui/progress"
import { 
  Sparkles, Target, AlertCircle, ArrowRight, Zap, ShieldCheck, TrendingUp,
  IndianRupee, PiggyBank, CreditCard, Bell, Clock, CheckCircle2, BarChart3
} from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"
import { useLocation } from "wouter"

const CATEGORY_CONFIG: Record<string, { icon: React.ReactNode; color: string }> = {
  spending: { icon: <CreditCard className="w-4 h-4" />, color: 'text-warning bg-warning/10 border-warning/30' },
  savings: { icon: <PiggyBank className="w-4 h-4" />, color: 'text-success bg-success/10 border-success/30' },
  debt: { icon: <IndianRupee className="w-4 h-4" />, color: 'text-destructive bg-destructive/10 border-destructive/30' },
  income: { icon: <TrendingUp className="w-4 h-4" />, color: 'text-info bg-info/10 border-info/30' },
  investment: { icon: <BarChart3 className="w-4 h-4" />, color: 'text-primary bg-primary/10 border-primary/30' },
  emergency: { icon: <Bell className="w-4 h-4" />, color: 'text-orange-500 bg-orange-500/10 border-orange-500/30' },
}

export default function Coach() {
  const { data, isLoading } = useGetFinancialAdvice()
  const { data: score } = useGetRiskScore()
  const { data: prediction } = usePredictFutureRisk()
  const [, setLocation] = useLocation()

  if (isLoading) return (
    <div className="space-y-6 animate-pulse">
      <Skeleton className="h-40 rounded-2xl bg-secondary" />
      <Skeleton className="h-64 rounded-2xl bg-secondary" />
    </div>
  )

  if (!data) return <div className="text-destructive p-8 text-center">Failed to load coach. Please refresh.</div>

  const riskScore = score?.score ?? 30
  const riskLevel = score?.level ?? 'medium'
  const highPriorityTips = data.tips?.filter((t: any) => t.priority === 'high') || []
  const otherTips = data.tips?.filter((t: any) => t.priority !== 'high') || []
  const totalSavingsOpp = data.tips?.reduce((sum: number, t: any) => sum + (t.potentialSaving || 0), 0) || data.savingsOpportunity || 0

  return (
    <div className="space-y-6 pb-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary to-info flex items-center justify-center shadow-glow">
            <Sparkles className="w-6 h-6 text-primary-foreground" />
          </div>
          <div>
            <h1 className="text-3xl font-display font-bold tracking-tight">AI Financial Coach</h1>
            <p className="text-muted-foreground text-sm">Hyper-personalized insights · Updated in real-time</p>
          </div>
        </div>
        <Button variant="outline" size="sm" className="rounded-xl border-border/50" onClick={() => setLocation('/simulate')}>
          <Zap className="w-4 h-4 mr-2 text-warning" />Run Scenario Simulator
        </Button>
      </div>

      {/* Warning Flags — Most Prominent */}
      <AnimatePresence>
        {data.warningFlags && data.warningFlags.length > 0 && (
          <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
            <Card className="p-5 bg-destructive/10 border-destructive/30">
              <div className="flex items-center gap-2 mb-3">
                <AlertCircle className="w-5 h-5 text-destructive" />
                <h3 className="font-bold text-destructive text-lg">⚠️ Immediate Action Required</h3>
              </div>
              <div className="space-y-2">
                {data.warningFlags.map((flag: string, i: number) => (
                  <div key={i} className="flex items-start gap-2.5 p-3 rounded-lg bg-destructive/10 border border-destructive/20">
                    <div className="w-1.5 h-1.5 rounded-full bg-destructive mt-2 shrink-0"></div>
                    <p className="text-sm text-destructive/90 leading-relaxed">{flag}</p>
                  </div>
                ))}
              </div>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Status Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Main Status */}
        <Card className="glass-panel overflow-hidden border-primary/20 lg:col-span-2">
          <div className="bg-gradient-to-br from-primary/10 to-info/5 p-6">
            <div className="flex items-start gap-4">
              <div className="p-3 rounded-xl bg-primary/20 shrink-0">
                <Sparkles className="w-6 h-6 text-primary" />
              </div>
              <div className="flex-1">
                <h2 className="font-bold text-lg mb-2">Your Financial Status</h2>
                <p className="text-muted-foreground leading-relaxed text-base italic">"{data.overallMessage}"</p>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-4 mt-6">
              <div className="text-center p-3 bg-background/50 rounded-xl border border-border/30">
                <div className="text-2xl font-display font-bold" style={{ color: getRiskColorHex(riskLevel) }}>{riskScore}</div>
                <div className="text-xs text-muted-foreground mt-1">Risk Score</div>
              </div>
              <div className="text-center p-3 bg-background/50 rounded-xl border border-border/30">
                <div className="text-2xl font-display font-bold text-success">{formatINR(totalSavingsOpp)}</div>
                <div className="text-xs text-muted-foreground mt-1">Savings Opp.</div>
              </div>
              <div className="text-center p-3 bg-background/50 rounded-xl border border-border/30">
                <div className="text-2xl font-display font-bold text-info">{data.tips?.length || 0}</div>
                <div className="text-xs text-muted-foreground mt-1">Active Tips</div>
              </div>
            </div>
          </div>
        </Card>

        {/* Monthly Goal + Prediction */}
        <div className="space-y-4">
          {data.monthlyGoal && (
            <Card className="glass-panel p-5 border-info/30 h-full flex flex-col justify-between">
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <div className="p-2 rounded-xl bg-info/20 text-info"><Target className="w-4 h-4" /></div>
                  <span className="font-semibold text-sm">Monthly Focus Goal</span>
                </div>
                <p className="text-sm text-muted-foreground leading-relaxed">{data.monthlyGoal}</p>
              </div>
              <div className="mt-4 space-y-2">
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>Savings Target</span>
                  <span className="font-semibold text-info">30%</span>
                </div>
                <Progress value={score?.financialHealthScore ? score.financialHealthScore / 3 : 20} className="h-1.5" />
                <Button variant="ghost" size="sm" className="w-full text-xs text-info hover:bg-info/10 h-7 mt-1" onClick={() => setLocation('/analytics')}>
                  Track Progress →
                </Button>
              </div>
            </Card>
          )}
        </div>
      </div>

      {/* High Priority Tips */}
      {highPriorityTips.length > 0 && (
        <div className="space-y-3">
          <h3 className="font-display font-bold text-lg flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-destructive" />
            High Priority Actions
          </h3>
          <div className="grid gap-3 sm:grid-cols-1">
            {highPriorityTips.map((tip: any, i: number) => {
              const catConfig = CATEGORY_CONFIG[tip.category] || CATEGORY_CONFIG.spending
              return (
                <motion.div key={i} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.08 }}>
                  <Card className="glass-panel p-5 border-destructive/20 hover:border-destructive/40 transition-all cursor-default hover:bg-destructive/5">
                    <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
                      <div className="flex items-start gap-3 flex-1">
                        <div className={`p-2.5 rounded-xl border shrink-0 ${catConfig.color}`}>{catConfig.icon}</div>
                        <div>
                          <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                            <Badge className="bg-destructive text-destructive-foreground text-[10px] px-2">HIGH PRIORITY</Badge>
                            <Badge variant="outline" className={`text-[10px] px-2 capitalize ${catConfig.color}`}>
                              {tip.category.replace('_', ' ')}
                            </Badge>
                          </div>
                          <p className="text-sm font-medium text-foreground leading-relaxed">{tip.tip}</p>
                        </div>
                      </div>
                      {tip.potentialSaving && (
                        <div className="text-right shrink-0 p-3 rounded-xl bg-success/10 border border-success/20">
                          <p className="text-[10px] text-muted-foreground">Save up to</p>
                          <p className="text-lg font-display font-bold text-success">{formatINR(tip.potentialSaving)}</p>
                          <p className="text-[10px] text-muted-foreground">per month</p>
                        </div>
                      )}
                    </div>
                  </Card>
                </motion.div>
              )
            })}
          </div>
        </div>
      )}

      {/* Smart Tips */}
      {otherTips.length > 0 && (
        <div className="space-y-3">
          <h3 className="font-display font-bold text-lg flex items-center gap-2">
            <Zap className="w-5 h-5 text-warning" />
            Smart Financial Tips
          </h3>
          <div className="grid gap-3 sm:grid-cols-2">
            {otherTips.map((tip: any, i: number) => {
              const catConfig = CATEGORY_CONFIG[tip.category] || CATEGORY_CONFIG.spending
              return (
                <motion.div key={i} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.07 }}>
                  <Card className="glass-panel p-4 hover:bg-white/[0.02] transition-colors cursor-default h-full flex flex-col">
                    <div className="flex items-start gap-3 flex-1">
                      <div className={`p-2 rounded-xl border shrink-0 ${catConfig.color}`}>{catConfig.icon}</div>
                      <div className="flex-1 min-w-0">
                        <Badge variant="outline" className={`text-[10px] px-2 mb-2 capitalize ${catConfig.color}`}>
                          {tip.category.replace('_', ' ')}
                        </Badge>
                        <p className="text-sm text-foreground/90 leading-relaxed">{tip.tip}</p>
                      </div>
                    </div>
                    {tip.potentialSaving && (
                      <div className="flex items-center justify-between mt-3 pt-3 border-t border-border/30">
                        <span className="text-xs text-muted-foreground">Potential savings</span>
                        <span className="text-sm font-bold font-mono text-success">+{formatINR(tip.potentialSaving)}/mo</span>
                      </div>
                    )}
                  </Card>
                </motion.div>
              )
            })}
          </div>
        </div>
      )}

      {/* India-specific Products */}
      <Card className="glass-panel p-6">
        <h3 className="font-semibold mb-4 flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-success" />
          Recommended Products for You — Barclays India
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            { name: 'Emergency Fund SIP', desc: 'Start ₹2,000/month in liquid mutual fund', icon: <PiggyBank className="w-5 h-5 text-success" />, tag: 'Start Today', color: 'border-success/30 bg-success/5' },
            { name: 'Health Insurance', desc: 'Cover ₹5L medical emergency — ₹800/month', icon: <Bell className="w-5 h-5 text-info" />, tag: 'Recommended', color: 'border-info/30 bg-info/5' },
            { name: 'Debt Consolidation', desc: 'Merge loan app debts into single low-rate loan', icon: <CreditCard className="w-5 h-5 text-warning" />, tag: 'High Priority', color: 'border-warning/30 bg-warning/5' },
          ].map((product, i) => (
            <motion.div key={i} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }}>
              <div className={`p-4 rounded-xl border transition-all hover:shadow-md cursor-pointer ${product.color}`}>
                <div className="flex items-center gap-3 mb-2">
                  {product.icon}
                  <Badge variant="outline" className="text-[10px] px-2">{product.tag}</Badge>
                </div>
                <h4 className="font-semibold text-sm">{product.name}</h4>
                <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{product.desc}</p>
                <Button variant="ghost" size="sm" className="w-full mt-3 h-7 text-xs rounded-lg">
                  Learn More <ArrowRight className="w-3 h-3 ml-1" />
                </Button>
              </div>
            </motion.div>
          ))}
        </div>
      </Card>
    </div>
  )
}
