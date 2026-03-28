import { useState } from "react"
import { useRunWhatIfSimulation, type WhatIfRequestScenario } from "@/lib/api-client"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Progress } from "@/components/ui/progress"
import { 
  ResponsiveContainer, BarChart, Bar, XAxis, Cell, Tooltip, CartesianGrid, YAxis
} from "recharts"
import { 
  GitCompareArrows, AlertTriangle, ShieldCheck, Clock, TrendingUp, TrendingDown, 
  Briefcase, Home, Stethoscope, PartyPopper, DollarSign, Wheat, Store,
  Wallet, ArrowRight, Zap, RefreshCw, IndianRupee, Car, GraduationCap
} from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"
import { getRiskColorHex, getRiskColor } from "@/lib/utils"

type Scenario = {
  id: WhatIfRequestScenario
  label: string
  description: string
  icon: React.ReactNode
  category: string
  severity: string
  indianContext: string
}

const SCENARIOS: Scenario[] = [
  {
    id: 'salary_delay',
    label: 'Salary Delay',
    description: 'What if your salary is delayed by 2–4 weeks?',
    icon: <Clock className="w-5 h-5" />,
    category: 'Income',
    severity: 'moderate',
    indianContext: 'Common in Indian SMEs & startups. EMI bounces, late fees pile up.'
  },
  {
    id: 'medical_emergency',
    label: 'Medical Emergency',
    description: 'What if you face a sudden ₹2–5L hospital bill?',
    icon: <Stethoscope className="w-5 h-5" />,
    category: 'Emergency',
    severity: 'severe',
    indianContext: '65% of Indians lack health insurance. OOP expenses are catastrophic.'
  },
  {
    id: 'job_loss',
    label: 'Job Loss',
    description: 'What if you lose your primary income source?',
    icon: <Briefcase className="w-5 h-5" />,
    category: 'Income',
    severity: 'critical',
    indianContext: 'No unemployment benefits in India. Savings typically last 2–3 months.'
  },
  {
    id: 'festival_season',
    label: 'Festival Season Spending',
    description: 'What if you overspend during Diwali/Holi season?',
    icon: <PartyPopper className="w-5 h-5" />,
    category: 'Spending',
    severity: 'moderate',
    indianContext: 'Indians spend ₹80,000 cr during festivals. Impulse purchases & EMI traps.'
  },
  {
    id: 'emi_increase',
    label: 'EMI Burden Increase',
    description: 'What if RBI hikes rates and your EMI rises 20%?',
    icon: <Home className="w-5 h-5" />,
    category: 'Debt',
    severity: 'moderate',
    indianContext: 'RBI rate hikes add ₹3,000–5,000/month on typical home loans.'
  },
  {
    id: 'income_boost',
    label: 'Income Boost',
    description: 'What if you get a 25% salary hike or freelance income?',
    icon: <TrendingUp className="w-5 h-5" />,
    category: 'Income',
    severity: 'positive',
    indianContext: 'Appraisal season in India: April–June. Moonlighting growing in IT sector.'
  },
  {
    id: 'wedding_expenses',
    label: 'Wedding Expenses',
    description: 'What if you plan a wedding (own or family) costing ₹5–10L?',
    icon: <PartyPopper className="w-5 h-5" />,
    category: 'Life Event',
    severity: 'severe',
    indianContext: 'Average Indian wedding costs ₹10–25L. Many take personal loans for this.'
  },
  {
    id: 'second_income',
    label: 'Gig/Side Income',
    description: 'What if you add ₹15,000/month from freelancing or gig work?',
    icon: <DollarSign className="w-5 h-5" />,
    category: 'Income',
    severity: 'positive',
    indianContext: 'India has 7.7M gig workers. Apps: Urban Company, Swiggy, Rapido.'
  },
  {
    id: 'crop_failure',
    label: 'Business Disruption',
    description: 'What if business income drops 50% for 3 months?',
    icon: <Store className="w-5 h-5" />,
    category: 'Business',
    severity: 'critical',
    indianContext: 'Affects self-employed & SME owners. GST, rent, staff salaries still due.'
  },
  {
    id: 'vehicle_loan',
    label: 'New Vehicle Loan',
    description: 'What if you take a ₹6L two-wheeler or car loan?',
    icon: <Car className="w-5 h-5" />,
    category: 'Debt',
    severity: 'moderate',
    indianContext: 'India is the world\'s largest 2-wheeler market. EMI of ₹8,000–12,000/month.'
  },
  {
    id: 'education_loan',
    label: 'Education Loan',
    description: 'What if you take an education loan for higher studies?',
    icon: <GraduationCap className="w-5 h-5" />,
    category: 'Life Event',
    severity: 'moderate',
    indianContext: 'Avg education loan: ₹8–20L. Moratorium period helps but repayment is heavy.'
  },
  {
    id: 'upi_limit_increase',
    label: 'UPI Overspending',
    description: 'What if UPI daily spending increases 3x from impulse buys?',
    icon: <IndianRupee className="w-5 h-5" />,
    category: 'Spending',
    severity: 'moderate',
    indianContext: 'UPI transactions hit ₹20L cr/month. Frictionless payments drive overspending.'
  },
]

const SEVERITY_CONFIG = {
  positive: { label: 'Positive', color: 'text-success bg-success/10 border-success/30', textColor: 'text-success' },
  moderate: { label: 'Moderate Risk', color: 'text-warning bg-warning/10 border-warning/30', textColor: 'text-warning' },
  severe: { label: 'Severe Risk', color: 'text-orange-500 bg-orange-500/10 border-orange-500/30', textColor: 'text-orange-500' },
  critical: { label: 'Critical', color: 'text-destructive bg-destructive/10 border-destructive/30', textColor: 'text-destructive' },
}

const CATEGORY_COLORS: Record<string, string> = {
  Income: 'bg-info/20 text-info border-info/30',
  Emergency: 'bg-destructive/20 text-destructive border-destructive/30',
  Spending: 'bg-warning/20 text-warning border-warning/30',
  Debt: 'bg-orange-500/20 text-orange-500 border-orange-500/30',
  Business: 'bg-purple-500/20 text-purple-500 border-purple-500/30',
  'Life Event': 'bg-pink-500/20 text-pink-500 border-pink-500/30',
}

export default function WhatIfSimulator() {
  const [selected, setSelected] = useState<Scenario | null>(null)
  const [activeCategory, setActiveCategory] = useState<string>('All')
  const { mutate: runSim, data: result, isPending, reset } = useRunWhatIfSimulation()

  const categories = ['All', ...Array.from(new Set(SCENARIOS.map(s => s.category)))]
  const filteredScenarios = activeCategory === 'All' ? SCENARIOS : SCENARIOS.filter(s => s.category === activeCategory)

  const handleRun = () => {
    if (!selected) return
    runSim({ data: { scenario: selected.id as WhatIfRequestScenario, parameters: {} } })
  }

  const handleSelectScenario = (s: Scenario) => {
    setSelected(s)
    reset()
  }

  const impactColor = result?.impact === 'severe' || result?.impact === 'critical' ? 'text-destructive' :
    result?.impact === 'moderate' ? 'text-warning' :
    result?.impact === 'minimal' ? 'text-success' : 'text-info'

  const barData = result ? [
    { label: 'Current', score: result.currentRiskScore, fill: getRiskColorHex('medium') },
    { label: 'Projected', score: result.projectedRiskScore, fill: getRiskColorHex(result.projectedRiskScore >= 70 ? 'critical' : result.projectedRiskScore >= 50 ? 'high' : result.projectedRiskScore >= 30 ? 'medium' : 'low') },
  ] : []

  return (
    <div className="space-y-6 pb-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-display font-bold tracking-tight flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary/20 flex items-center justify-center">
            <GitCompareArrows className="w-5 h-5 text-primary" />
          </div>
          What-If Scenario Simulator
        </h1>
        <p className="text-muted-foreground mt-2 ml-14">
          AI-powered stress testing for 12 real-life financial scenarios · India-specific context
        </p>
      </div>

      {/* Category Filter */}
      <div className="flex flex-wrap gap-2">
        {categories.map(cat => (
          <button
            key={cat}
            onClick={() => setActiveCategory(cat)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-all border ${
              activeCategory === cat 
                ? 'bg-primary text-primary-foreground border-primary' 
                : 'border-border/50 text-muted-foreground hover:border-primary/40 hover:text-foreground bg-secondary/20'
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Scenario Grid */}
        <div className="lg:col-span-3 space-y-3">
          <p className="text-sm font-medium text-muted-foreground">{filteredScenarios.length} scenarios · Select one to simulate</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {filteredScenarios.map((s, i) => {
              const sev = SEVERITY_CONFIG[s.severity as keyof typeof SEVERITY_CONFIG]
              const isSelected = selected?.id === s.id
              return (
                <motion.div
                  key={s.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.04 }}
                  onClick={() => handleSelectScenario(s)}
                  className={`p-4 rounded-xl border cursor-pointer transition-all hover:shadow-md ${
                    isSelected 
                      ? 'border-primary bg-primary/10 shadow-glow' 
                      : 'border-border/50 bg-card/50 hover:border-border hover:bg-white/5'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${sev.color} border`}>
                      {s.icon}
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <Badge className={`text-[10px] px-1.5 py-0.5 border ${CATEGORY_COLORS[s.category] || ''}`}>
                        {s.category}
                      </Badge>
                      <Badge variant="outline" className={`text-[10px] px-1.5 py-0.5 ${sev.textColor}`}>
                        {sev.label}
                      </Badge>
                    </div>
                  </div>
                  <h4 className="font-semibold text-sm mb-1">{s.label}</h4>
                  <p className="text-xs text-muted-foreground leading-relaxed">{s.description}</p>
                  {isSelected && (
                    <div className="mt-2.5 p-2 rounded-lg bg-primary/10 border border-primary/20">
                      <p className="text-[11px] text-primary/90 leading-relaxed">🇮🇳 {s.indianContext}</p>
                    </div>
                  )}
                </motion.div>
              )
            })}
          </div>
        </div>

        {/* Simulation Panel */}
        <div className="lg:col-span-2 space-y-4 sticky top-0">
          <Card className="glass-panel p-6">
            <h3 className="font-semibold mb-1 flex items-center gap-2">
              <Zap className="w-4 h-4 text-warning" />
              Simulation Panel
            </h3>
            {selected ? (
              <div className="space-y-4">
                <div className={`p-3 rounded-xl border ${SEVERITY_CONFIG[selected.severity as keyof typeof SEVERITY_CONFIG].color}`}>
                  <div className="flex items-center gap-2 mb-1">
                    {selected.icon}
                    <span className="font-semibold text-sm">{selected.label}</span>
                  </div>
                  <p className="text-xs opacity-80 leading-relaxed">{selected.description}</p>
                </div>

                <div className="p-3 rounded-xl bg-secondary/30 border border-border/30">
                  <p className="text-xs font-semibold text-muted-foreground mb-1 uppercase tracking-wider">🇮🇳 India Context</p>
                  <p className="text-xs text-foreground/80 leading-relaxed">{selected.indianContext}</p>
                </div>

                <Button className="w-full" onClick={handleRun} disabled={isPending}>
                  {isPending ? (
                    <><RefreshCw className="w-4 h-4 mr-2 animate-spin" />Running AI Simulation...</>
                  ) : (
                    <><GitCompareArrows className="w-4 h-4 mr-2" />Run Simulation</>
                  )}
                </Button>
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <GitCompareArrows className="w-8 h-8 mx-auto mb-3 opacity-30" />
                <p className="text-sm">Select a scenario to simulate</p>
                <p className="text-xs mt-1">Choose from {SCENARIOS.length} India-specific scenarios</p>
              </div>
            )}
          </Card>

          {/* Result */}
          <AnimatePresence>
            {result && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 20 }}
                className="space-y-4"
              >
                <Card className="glass-panel p-5">
                  <h3 className="font-semibold text-sm mb-4 flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-primary" />
                    Simulation Results
                  </h3>

                  {/* Score Comparison */}
                  <div className="flex items-center justify-between gap-3 mb-5">
                    <div className="text-center flex-1 p-3 rounded-xl bg-secondary/30">
                      <p className="text-xs text-muted-foreground mb-1">Current Score</p>
                      <div className="text-3xl font-display font-bold" style={{ color: getRiskColorHex('medium') }}>
                        {result.currentRiskScore}
                      </div>
                    </div>
                    <ArrowRight className="w-5 h-5 text-muted-foreground shrink-0" />
                    <div className={`text-center flex-1 p-3 rounded-xl border ${
                      result.projectedRiskScore > result.currentRiskScore 
                        ? 'bg-destructive/10 border-destructive/30' 
                        : 'bg-success/10 border-success/30'
                    }`}>
                      <p className="text-xs text-muted-foreground mb-1">Projected Score</p>
                      <div className="text-3xl font-display font-bold" style={{ color: getRiskColorHex(result.projectedRiskScore >= 70 ? 'critical' : result.projectedRiskScore >= 50 ? 'high' : result.projectedRiskScore >= 30 ? 'medium' : 'low') }}>
                        {result.projectedRiskScore}
                      </div>
                    </div>
                  </div>

                  {/* Visual Bar */}
                  <div className="h-[90px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={barData} margin={{ top: 0, right: 5, left: -20, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.1} />
                        <XAxis dataKey="label" tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }} />
                        <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} />
                        <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '8px', fontSize: '12px' }} formatter={(v: number) => [v, 'Risk Score']} />
                        <Bar dataKey="score" radius={[4, 4, 0, 0]}>
                          {barData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>

                  <div className="space-y-3 mt-4">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">Risk Delta</span>
                      <span className={`font-bold text-sm ${result.riskDelta > 0 ? 'text-destructive' : 'text-success'}`}>
                        {result.riskDelta > 0 ? '+' : ''}{result.riskDelta} points
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">Impact Level</span>
                      <Badge className={`text-xs capitalize ${impactColor} bg-transparent border`}>
                        {result.impact}
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">Recovery Time</span>
                      <span className="font-semibold text-sm flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5 text-muted-foreground" />
                        {result.recoveryTimeWeeks} weeks
                      </span>
                    </div>
                  </div>

                  {/* Recovery Progress */}
                  <div className="mt-4">
                    <p className="text-xs text-muted-foreground mb-2">Recovery Difficulty</p>
                    <Progress value={Math.min((result.recoveryTimeWeeks / 12) * 100, 100)} className="h-2" />
                    <div className="flex justify-between text-[10px] text-muted-foreground mt-1">
                      <span>Easy</span><span>Hard</span>
                    </div>
                  </div>
                </Card>

                {/* Recommendations */}
                {result.recommendations && result.recommendations.length > 0 && (
                  <Card className="glass-panel p-5">
                    <h4 className="font-semibold text-sm mb-3 flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4 text-success" />
                      Protective Actions
                    </h4>
                    <div className="space-y-2">
                      {result.recommendations.map((rec: string, i: number) => (
                        <div key={i} className="flex items-start gap-2.5 text-xs p-2.5 rounded-lg bg-success/5 border border-success/20">
                          <div className="w-4 h-4 rounded-full bg-success/20 flex items-center justify-center text-success font-bold text-[10px] shrink-0 mt-0.5">
                            {i + 1}
                          </div>
                          <span className="text-foreground/80 leading-relaxed">{rec}</span>
                        </div>
                      ))}
                    </div>
                  </Card>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}
