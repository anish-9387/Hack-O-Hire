import { useGetAuditLogs } from "@/lib/api-client"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ShieldCheck, Server } from "lucide-react"

export default function AuditLogs() {
  const { data, isLoading } = useGetAuditLogs({ limit: 50 })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-display font-bold tracking-tight">Compliance & Audit</h1>
        <p className="text-muted-foreground mt-1">Immutable ledger of system actions and data access.</p>
      </div>

      <Card className="glass-panel overflow-hidden border-border/50">
        <div className="p-4 bg-secondary/10 border-b border-border/50 flex items-center gap-2 text-sm text-muted-foreground">
          <ShieldCheck className="w-4 h-4 text-success" />
          <span>System running in compliant mode. All actions are cryptographically logged.</span>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-xs text-muted-foreground uppercase bg-secondary/5 border-b border-border/50">
              <tr>
                <th className="px-6 py-4 font-semibold">Timestamp</th>
                <th className="px-6 py-4 font-semibold">Action</th>
                <th className="px-6 py-4 font-semibold">Actor / User</th>
                <th className="px-6 py-4 font-semibold">Resource</th>
                <th className="px-6 py-4 font-semibold">IP Address</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/10 font-mono text-[13px]">
              {isLoading ? (
                <tr><td colSpan={5} className="p-8 text-center text-muted-foreground">Loading logs...</td></tr>
              ) : !data?.logs.length ? (
                <tr><td colSpan={5} className="p-8 text-center text-muted-foreground">No logs available.</td></tr>
              ) : (
                data.logs.map((log) => (
                  <tr key={log.id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="px-6 py-3 text-muted-foreground whitespace-nowrap">
                      {new Date(log.createdAt).toISOString().replace('T', ' ').substring(0, 19)}
                    </td>
                    <td className="px-6 py-3">
                      <Badge variant="outline" className="bg-secondary/20 font-normal">
                        {log.action}
                      </Badge>
                    </td>
                    <td className="px-6 py-3 text-primary">
                      {log.userId || 'SYSTEM'}
                    </td>
                    <td className="px-6 py-3 text-muted-foreground">
                      {log.resourceType} {log.resourceId && `[${log.resourceId.substring(0,8)}...]`}
                    </td>
                    <td className="px-6 py-3 text-muted-foreground">
                      <div className="flex items-center gap-2">
                        <Server className="w-3 h-3 opacity-50" />
                        {log.ipAddress || 'Internal'}
                      </div>
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
