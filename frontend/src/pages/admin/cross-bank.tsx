import { useState } from "react"
import {
  useGetCrossBankStats,
  useGetCrossBankAlerts,
  useCrossBankCheck,
  useSeedCrossBankDemo,
} from "@/lib/api-client"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Shield, AlertTriangle, Building2, Search, Database,
  Users, Zap, ChevronRight, Globe, Lock
} from "lucide-react"
import { motion } from "framer-motion"
import { useQueryClient } from "@tanstack/react-query"

function formatINR(n: number) {
  if (n >= 10000000) return `${(n / 10000000).toFixed(1)}Cr`
  if (n >= 100000) return `${(n / 100000).toFixed(1)}L`
  if (n >= 1000) return `${(n / 1000).toFixed(1)}K`
  return n.toFixed(0)
}

export default function CrossBankDashboard() {
  const qc = useQueryClient()
  const { data: stats, isLoading: statsLoading } = useGetCrossBankStats()
  const { data: alertsData, isLoading: alertsLoading } = useGetCrossBankAlerts()
  const { mutateAsync: checkBorrower, isPending: checking } = useCrossBankCheck()
  const { mutateAsync: seedDemo, isPending: seeding } = useSeedCrossBankDemo()

  const [pan, setPan] = useState("")
  const [phone, setPhone] = useState("")
  const [checkResult, setCheckResult] = useState<any>(null)

  const alerts = alertsData?.alerts || []
  const registryStats = alertsData?.registry_stats || stats || {}

  const handleCheck = async () => {
    if (!pan || !phone) return
    const result = await checkBorrower({ data: { pan, phone } })
    setCheckResult(result)
  }

  const handleSeed = async () => {
    await seedDemo()
    qc.invalidateQueries({ queryKey: ["/api/cross-bank/stats"] })
    qc.invalidateQueries({ queryKey: ["/api/admin/cross-bank-alerts"] })
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Globe className="h-7 w-7 text-blue-500" />
            Cross-Bank Defaulter Detection
          </h1>
          <p className="text-muted-foreground mt-1">
            Inter-bank shared defaulter registry — detect hidden risk from other institutions
          </p>
        </div>
        <Button onClick={handleSeed} disabled={seeding} variant="outline">
          <Database className="h-4 w-4 mr-2" />
          {seeding ? "Seeding..." : "Seed Demo Data"}
        </Button>
      </div>

      {/* Registry Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {statsLoading ? (
          Array(4).fill(0).map((_, i) => <Skeleton key={i} className="h-24" />)
        ) : (
          <>
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0 }}>
              <Card className="p-4">
                <div className="flex items-center gap-2 text-muted-foreground text-sm">
                  <Building2 className="h-4 w-4" /> Participating Banks
                </div>
                <p className="text-3xl font-bold mt-1">{registryStats.participating_banks || 0}</p>
                <p className="text-xs text-muted-foreground">{registryStats.active_banks || 0} active</p>
              </Card>
            </motion.div>
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
              <Card className="p-4">
                <div className="flex items-center gap-2 text-muted-foreground text-sm">
                  <Users className="h-4 w-4" /> Unique Defaulters
                </div>
                <p className="text-3xl font-bold mt-1">{registryStats.unique_defaulters || 0}</p>
                <p className="text-xs text-muted-foreground">{registryStats.total_records || 0} total records</p>
              </Card>
            </motion.div>
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
              <Card className="p-4 border-red-200 dark:border-red-900">
                <div className="flex items-center gap-2 text-red-500 text-sm">
                  <AlertTriangle className="h-4 w-4" /> Serial Defaulters
                </div>
                <p className="text-3xl font-bold mt-1 text-red-600">{registryStats.serial_defaulters || 0}</p>
                <p className="text-xs text-muted-foreground">Defaulted at 2+ banks</p>
              </Card>
            </motion.div>
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
              <Card className="p-4">
                <div className="flex items-center gap-2 text-muted-foreground text-sm">
                  <Zap className="h-4 w-4" /> Total Default Amount
                </div>
                <p className="text-3xl font-bold mt-1">{formatINR(registryStats.total_default_amount || 0)}</p>
                <p className="text-xs text-muted-foreground">{registryStats.unresolved_count || 0} unresolved</p>
              </Card>
            </motion.div>
          </>
        )}
      </div>

      {/* Banks List */}
      {registryStats.banks && registryStats.banks.length > 0 && (
        <Card className="p-4">
          <h3 className="font-semibold mb-3 flex items-center gap-2">
            <Building2 className="h-5 w-5" /> Participating Banks
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-3">
            {registryStats.banks.map((bank: any) => (
              <div key={bank.id} className="flex items-center gap-3 p-3 rounded-lg bg-muted/50">
                <div className="h-10 w-10 rounded-full bg-blue-100 dark:bg-blue-900 flex items-center justify-center text-blue-600 font-bold text-sm">
                  {bank.code}
                </div>
                <div>
                  <p className="font-medium text-sm">{bank.name}</p>
                  <p className="text-xs text-muted-foreground">{bank.defaults_reported} defaults reported</p>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Borrower Lookup */}
      <Card className="p-6">
        <h3 className="font-semibold mb-4 flex items-center gap-2">
          <Search className="h-5 w-5" /> Cross-Bank Borrower Lookup
        </h3>
        <p className="text-sm text-muted-foreground mb-4">
          Check if a loan applicant has defaults at other banks using their PAN and phone number.
          Identity is hashed for privacy — no raw PII is stored in the registry.
        </p>
        <div className="flex gap-3 items-end">
          <div className="flex-1">
            <label className="text-sm font-medium mb-1 block">PAN Number</label>
            <Input
              placeholder="e.g., ABCPD1000A"
              value={pan}
              onChange={e => setPan(e.target.value.toUpperCase())}
            />
          </div>
          <div className="flex-1">
            <label className="text-sm font-medium mb-1 block">Phone Number</label>
            <Input
              placeholder="e.g., 9812345678"
              value={phone}
              onChange={e => setPhone(e.target.value)}
            />
          </div>
          <Button onClick={handleCheck} disabled={checking || !pan || !phone}>
            <Shield className="h-4 w-4 mr-2" />
            {checking ? "Checking..." : "Check Registry"}
          </Button>
        </div>

        {checkResult && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            className="mt-4"
          >
            {checkResult.found ? (
              <div className="bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-3">
                  <AlertTriangle className="h-5 w-5 text-red-500" />
                  <span className="font-bold text-red-700 dark:text-red-400">
                    CROSS-BANK DEFAULTS FOUND
                  </span>
                  {checkResult.is_serial_defaulter && (
                    <Badge variant="destructive">SERIAL DEFAULTER</Badge>
                  )}
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                  <div>
                    <p className="text-muted-foreground">Defaults Found</p>
                    <p className="font-bold text-lg">{checkResult.cross_bank_default_count}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Banks Defaulted At</p>
                    <p className="font-bold text-lg">{checkResult.banks_defaulted_at}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Total Default Amount</p>
                    <p className="font-bold text-lg">{formatINR(checkResult.total_default_amount)}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Risk Boost</p>
                    <p className="font-bold text-lg text-red-600">+{(checkResult.risk_boost * 100).toFixed(0)}%</p>
                  </div>
                </div>
                {checkResult.records && checkResult.records.length > 0 && (
                  <div className="mt-3 space-y-2">
                    <p className="font-medium text-sm">Default Records:</p>
                    {checkResult.records.map((r: any, i: number) => (
                      <div key={i} className="flex items-center gap-3 text-sm bg-white/50 dark:bg-black/20 rounded p-2">
                        <Badge variant="outline">{r.bank}</Badge>
                        <span>{r.loan_type}</span>
                        <span className="text-muted-foreground">{formatINR(r.amount)}</span>
                        <span className="text-muted-foreground">{r.dpd} DPD</span>
                        <Badge variant={r.status === "unresolved" ? "destructive" : "secondary"}>
                          {r.status}
                        </Badge>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-lg p-4">
                <div className="flex items-center gap-2">
                  <Shield className="h-5 w-5 text-green-500" />
                  <span className="font-bold text-green-700 dark:text-green-400">
                    NO CROSS-BANK DEFAULTS FOUND
                  </span>
                </div>
                <p className="text-sm text-muted-foreground mt-1">
                  This borrower has no default records in the shared inter-bank registry.
                </p>
              </div>
            )}
          </motion.div>
        )}
      </Card>

      {/* Cross-Bank Alerts — borrowers in OUR portfolio who defaulted elsewhere */}
      <Card className="p-6">
        <h3 className="font-semibold mb-4 flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-red-500" />
          Portfolio Cross-Bank Alerts
          {alerts.length > 0 && (
            <Badge variant="destructive">{alerts.length}</Badge>
          )}
        </h3>
        <p className="text-sm text-muted-foreground mb-4">
          Borrowers in your portfolio who appear clean locally but have defaults at other banks.
          These are the highest-risk hidden threats.
        </p>

        {alertsLoading ? (
          <div className="space-y-3">
            {Array(3).fill(0).map((_, i) => <Skeleton key={i} className="h-20" />)}
          </div>
        ) : alerts.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <Lock className="h-12 w-12 mx-auto mb-2 opacity-40" />
            <p>No cross-bank alerts. Seed demo data to see alerts.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {alerts.map((alert: any, i: number) => (
              <motion.div
                key={alert.borrower_id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                className={`flex items-center justify-between p-4 rounded-lg border ${
                  alert.alert_severity === "CRITICAL"
                    ? "border-red-300 bg-red-50 dark:border-red-800 dark:bg-red-950"
                    : "border-orange-300 bg-orange-50 dark:border-orange-800 dark:bg-orange-950"
                }`}
              >
                <div className="flex items-center gap-4">
                  <div className={`h-10 w-10 rounded-full flex items-center justify-center ${
                    alert.alert_severity === "CRITICAL" ? "bg-red-200 dark:bg-red-800" : "bg-orange-200 dark:bg-orange-800"
                  }`}>
                    <AlertTriangle className={`h-5 w-5 ${
                      alert.alert_severity === "CRITICAL" ? "text-red-600" : "text-orange-600"
                    }`} />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">{alert.borrower_id}</span>
                      <Badge variant={alert.alert_severity === "CRITICAL" ? "destructive" : "default"}>
                        {alert.alert_severity}
                      </Badge>
                      {alert.is_serial_defaulter && (
                        <Badge variant="destructive" className="text-[10px]">SERIAL DEFAULTER</Badge>
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {alert.cross_bank_defaults} default(s) at {alert.banks_defaulted_at.join(", ")} |
                      Total: {formatINR(alert.total_default_amount)} |
                      Max DPD: {alert.max_dpd_other_banks}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm font-medium">Current: {alert.current_risk_category}</p>
                  <p className="text-xs text-muted-foreground">{alert.recommended_action}</p>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </Card>

      {/* How It Works */}
      <Card className="p-6 bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-950 dark:to-indigo-950 border-blue-200 dark:border-blue-800">
        <h3 className="font-semibold mb-4 flex items-center gap-2">
          <Lock className="h-5 w-5 text-blue-500" /> How Cross-Bank Detection Works
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[
            { step: 1, title: "Bank Reports Default", desc: "When a borrower defaults, the bank reports it to the shared registry with hashed PAN+phone." },
            { step: 2, title: "New Application", desc: "When the same person applies at another bank, the system checks the registry using their PAN+phone hash." },
            { step: 3, title: "Risk Boost", desc: "If matches found, the AI model's risk prediction is boosted based on cross-bank severity (up to +50%)." },
            { step: 4, title: "Admin Alert", desc: "Bank admin sees a CROSS-BANK ALERT with full default history from other institutions." },
          ].map(item => (
            <div key={item.step} className="flex gap-3">
              <div className="h-8 w-8 rounded-full bg-blue-500 text-white flex items-center justify-center font-bold text-sm shrink-0">
                {item.step}
              </div>
              <div>
                <p className="font-medium text-sm">{item.title}</p>
                <p className="text-xs text-muted-foreground mt-1">{item.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}
