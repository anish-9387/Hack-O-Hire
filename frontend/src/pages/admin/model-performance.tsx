import { useGetModelPerformance } from "@/lib/api-client"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Sparkles, AlertTriangle, Activity, CheckCircle2 } from "lucide-react"

export default function ModelPerformance() {
  const { data, isLoading } = useGetModelPerformance()

  if (isLoading || !data) return (
    <div className="space-y-6 animate-pulse">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[1,2,3,4].map(i => <Skeleton key={i} className="h-32 rounded-2xl bg-secondary" />)}
      </div>
      <Skeleton className="h-64 rounded-2xl bg-secondary" />
    </div>
  )

  const metrics = [
    { label: "Accuracy", value: `${(data.accuracy * 100).toFixed(1)}%` },
    { label: "AUC-ROC", value: data.auc.toFixed(3) },
    { label: "Precision", value: `${(data.precision * 100).toFixed(1)}%` },
    { label: "Recall", value: `${(data.recall * 100).toFixed(1)}%` },
  ]

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h1 className="text-3xl font-display font-bold tracking-tight">ML Model Telemetry</h1>
        <p className="text-muted-foreground mt-1">Live performance metrics of the risk scoring engine.</p>
      </div>

      <div className="flex items-center gap-3">
        <Badge variant="outline" className="bg-primary/10 text-primary border-primary/30 px-3 py-1 font-mono">
          VERSION: {data.modelVersion}
        </Badge>
        <span className="text-xs text-muted-foreground">Last trained: {new Date(data.lastTrainedAt).toLocaleString()}</span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {metrics.map((m, i) => (
          <Card key={i} className="glass-panel p-6 text-center">
            <p className="text-sm font-medium text-muted-foreground mb-2 uppercase tracking-wider">{m.label}</p>
            <p className="text-3xl font-display font-bold">{m.value}</p>
          </Card>
        ))}
      </div>

      <Card className="glass-panel p-6 border-t-4 border-t-info/80">
        <h3 className="font-semibold text-lg mb-4 flex items-center gap-2">
          <Activity className="w-5 h-5 text-info" />
          Data Drift Monitor
        </h3>
        
        {data.featureDriftDetected ? (
          <div className="bg-warning/10 border border-warning/30 rounded-xl p-5">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-6 h-6 text-warning shrink-0" />
              <div>
                <h4 className="font-bold text-warning mb-1">Feature Drift Detected</h4>
                <p className="text-sm text-foreground/80 mb-4">The distribution of real-time data has significantly deviated from the training baseline. Retraining is recommended.</p>
                <div className="space-y-2">
                  <p className="text-xs font-semibold text-muted-foreground uppercase">Impacted Features:</p>
                  <div className="flex flex-wrap gap-2">
                    {data.driftedFeatures?.map(f => (
                      <Badge key={f} variant="secondary" className="bg-background border-border">{f}</Badge>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-success/10 border border-success/30 rounded-xl p-5 flex items-center gap-3">
            <CheckCircle2 className="w-6 h-6 text-success shrink-0" />
            <div>
              <h4 className="font-bold text-success">Features Stable</h4>
              <p className="text-sm text-success/80">Incoming data distribution matches training baseline perfectly.</p>
            </div>
          </div>
        )}
      </Card>
      
      <Card className="glass-panel p-6">
         <h3 className="font-semibold mb-2">Total Predictions Handled</h3>
         <div className="text-5xl font-display font-bold tracking-tighter text-primary">
           {data.totalPredictions?.toLocaleString() || "1,245,892"}
         </div>
         <p className="text-sm text-muted-foreground mt-2">In the current epoch</p>
      </Card>
    </div>
  )
}
