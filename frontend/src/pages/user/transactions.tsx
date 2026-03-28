import { useState } from "react"
import { useListTransactions, useSimulateTransaction, useCreateTransaction, type SimulateTransactionRequestType } from "@/lib/api-client"
import { formatINR, cn } from "@/lib/utils"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from "@/components/ui/dialog"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { ArrowDownRight, ArrowUpRight, Search, SlidersHorizontal, Activity, AlertTriangle, CheckCircle2 } from "lucide-react"

export default function Transactions() {
  const { data, isLoading, refetch } = useListTransactions({ limit: 50 })
  const [searchTerm, setSearchTerm] = useState("")

  const filteredTxs = data?.transactions.filter(tx => 
    tx.merchantName?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    tx.category.toLowerCase().includes(searchTerm.toLowerCase()) ||
    tx.description?.toLowerCase().includes(searchTerm.toLowerCase())
  ) || []

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-display font-bold tracking-tight">Transactions</h1>
          <p className="text-muted-foreground">View your history and simulate new transactions.</p>
        </div>
        <SimulatorModal onSimulateComplete={() => refetch()} />
      </div>

      <Card className="glass-panel overflow-hidden flex flex-col">
        <div className="p-4 border-b border-border/50 flex flex-col sm:flex-row gap-4 items-center bg-secondary/20">
          <div className="relative w-full sm:max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input 
              placeholder="Search merchants, categories..." 
              className="pl-9 bg-background/50 border-border/50"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <Button variant="outline" className="w-full sm:w-auto border-border/50 bg-background/50">
            <SlidersHorizontal className="w-4 h-4 mr-2" />
            Filters
          </Button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-xs text-muted-foreground uppercase bg-secondary/10 border-b border-border/50">
              <tr>
                <th className="px-6 py-4 font-semibold">Date</th>
                <th className="px-6 py-4 font-semibold">Details</th>
                <th className="px-6 py-4 font-semibold">Category</th>
                <th className="px-6 py-4 font-semibold">Method</th>
                <th className="px-6 py-4 font-semibold text-right">Amount</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr><td colSpan={5} className="p-8 text-center text-muted-foreground">Loading transactions...</td></tr>
              ) : filteredTxs.length === 0 ? (
                <tr><td colSpan={5} className="p-8 text-center text-muted-foreground">No transactions found.</td></tr>
              ) : (
                filteredTxs.map((tx) => (
                  <tr key={tx.id} className="border-b border-border/10 hover:bg-white/[0.02] transition-colors group">
                    <td className="px-6 py-4 whitespace-nowrap text-muted-foreground">
                      {new Date(tx.transactionDate).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-foreground">{tx.merchantName || tx.description || 'Transfer'}</span>
                        {tx.isStressIndicator && (
                          <Badge variant="outline" className="bg-destructive/10 text-destructive border-destructive/20 text-[10px] px-1.5 py-0">
                            Stress Flag
                          </Badge>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 capitalize text-muted-foreground">
                      {tx.category.replace('_', ' ')}
                    </td>
                    <td className="px-6 py-4">
                      <Badge variant="secondary" className="bg-secondary/40 font-mono font-normal">
                        {tx.paymentMethod?.toUpperCase() || 'SYS'}
                      </Badge>
                    </td>
                    <td className={`px-6 py-4 text-right font-mono font-semibold whitespace-nowrap ${
                      tx.type === 'credit' ? 'text-success' : 'text-foreground'
                    }`}>
                      {tx.type === 'credit' ? '+' : '-'}{formatINR(tx.amount)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}

function SimulatorModal({ onSimulateComplete }: { onSimulateComplete: () => void }) {
  const [open, setOpen] = useState(false)
  const [amount, setAmount] = useState("")
  const [type, setType] = useState<SimulateTransactionRequestType>("debit")
  const [category, setCategory] = useState("upi")
  
  const simulateMutation = useSimulateTransaction()
  const createMutation = useCreateTransaction()

  const handleSimulate = () => {
    if (!amount || isNaN(Number(amount))) return
    simulateMutation.mutate({
      data: {
        amount: Number(amount),
        type,
        category,
        description: "Simulated Test"
      }
    })
  }

  const handleCommit = () => {
    if (!amount || isNaN(Number(amount))) return
    createMutation.mutate({
      data: {
        amount: Number(amount),
        type,
        category,
        description: "Simulated Test",
        paymentMethod: "upi",
        merchantName: "Simulator"
      }
    }, {
      onSuccess: () => {
        onSimulateComplete()
        setOpen(false)
        simulateMutation.reset()
        setAmount("")
      }
    })
  }

  const result = simulateMutation.data

  return (
    <Dialog open={open} onOpenChange={(val) => { setOpen(val); if(!val) simulateMutation.reset() }}>
      <DialogTrigger asChild>
        <Button className="bg-primary text-primary-foreground hover:bg-primary/90 shadow-glow rounded-xl">
          <Activity className="w-4 h-4 mr-2" />
          Simulate Transaction
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[500px] bg-card border-border/50 shadow-2xl">
        <DialogHeader>
          <DialogTitle className="font-display text-2xl tracking-tight">Risk Simulator</DialogTitle>
          <DialogDescription>
            See how a transaction will impact your financial health score before making it.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-6 py-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Type</Label>
              <Select value={type} onValueChange={(v: any) => setType(v)}>
                <SelectTrigger className="bg-secondary/50 border-border/50">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="debit">Debit (Spend)</SelectItem>
                  <SelectItem value="credit">Credit (Receive)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Amount (₹)</Label>
              <Input 
                type="number" 
                value={amount} 
                onChange={(e) => setAmount(e.target.value)}
                placeholder="10000"
                className="bg-secondary/50 border-border/50 font-mono"
              />
            </div>
          </div>
          
          <div className="space-y-2">
            <Label>Category</Label>
            <Select value={category} onValueChange={setCategory}>
              <SelectTrigger className="bg-secondary/50 border-border/50">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="upi">UPI Transfer</SelectItem>
                <SelectItem value="atm_withdrawal">ATM Withdrawal</SelectItem>
                <SelectItem value="emi_payment">EMI Payment</SelectItem>
                <SelectItem value="loan_app">Digital Loan App</SelectItem>
                <SelectItem value="festival_shopping">Festival Shopping</SelectItem>
                <SelectItem value="medical">Medical Emergency</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <Button 
            variant="secondary" 
            onClick={handleSimulate}
            disabled={simulateMutation.isPending || !amount}
            className="w-full"
          >
            {simulateMutation.isPending ? "Simulating..." : "Calculate Risk Impact"}
          </Button>

          {result && (
            <div className="mt-4 p-4 rounded-xl border bg-background/50 border-border/50 space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-muted-foreground">Impact on Score</span>
                <div className="flex items-center gap-2">
                  <span className="text-2xl font-bold font-display">{result.projectedRiskScore}</span>
                  <Badge variant="outline" className={cn(
                    "font-mono",
                    result.riskDelta < 0 ? "text-success border-success/30 bg-success/10" : 
                    result.riskDelta > 0 ? "text-destructive border-destructive/30 bg-destructive/10" : 
                    "text-muted-foreground"
                  )}>
                    {result.riskDelta > 0 ? '+' : ''}{result.riskDelta}
                  </Badge>
                </div>
              </div>
              
              {result.warning && (
                <div className="flex gap-2 p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-sm">
                  <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                  <p>{result.warning}</p>
                </div>
              )}

              {result.recommendation && (
                <div className="flex gap-2 p-3 rounded-lg bg-info/10 border border-info/20 text-info text-sm">
                  <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
                  <p>{result.recommendation}</p>
                </div>
              )}

              <Button 
                onClick={handleCommit} 
                disabled={createMutation.isPending}
                className="w-full bg-primary text-primary-foreground mt-2"
              >
                {createMutation.isPending ? "Committing..." : "Commit Transaction"}
              </Button>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
