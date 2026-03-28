import { useState } from "react"
import { useListUsers, type ListUsersRiskLevel } from "@/lib/api-client"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import { getRiskColor, formatINR } from "@/lib/utils"
import { Search, SlidersHorizontal, AlertTriangle, Eye } from "lucide-react"
import { useLocation } from "wouter"

export default function AdminUsers() {
  const [, setLocation] = useLocation()
  const [search, setSearch] = useState("")
  const [riskLevel, setRiskLevel] = useState<ListUsersRiskLevel | "all">("all")
  
  const { data, isLoading } = useListUsers({ 
    search: search.length > 2 ? search : undefined,
    riskLevel: riskLevel !== "all" ? riskLevel : undefined,
    limit: 50
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-display font-bold tracking-tight">Customer Base</h1>
        <p className="text-muted-foreground mt-1">Manage and monitor individual user risk profiles.</p>
      </div>

      <Card className="glass-panel overflow-hidden">
        <div className="p-4 border-b border-border/50 flex flex-col sm:flex-row gap-4 items-center bg-secondary/20">
          <div className="relative w-full sm:max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input 
              placeholder="Search by name, email, city..." 
              className="pl-9 bg-background/50 border-border/50"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <Select value={riskLevel} onValueChange={(v: any) => setRiskLevel(v)}>
            <SelectTrigger className="w-[180px] bg-background/50 border-border/50">
              <SelectValue placeholder="Risk Level" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Levels</SelectItem>
              <SelectItem value="critical">Critical Only</SelectItem>
              <SelectItem value="high">High & Above</SelectItem>
              <SelectItem value="medium">Medium</SelectItem>
              <SelectItem value="low">Low Risk</SelectItem>
            </SelectContent>
          </Select>
          <div className="flex-1"></div>
          <Button variant="outline" className="border-border/50 bg-background/50">
            <SlidersHorizontal className="w-4 h-4 mr-2" />
            More Filters
          </Button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-xs text-muted-foreground uppercase bg-secondary/10 border-b border-border/50">
              <tr>
                <th className="px-6 py-4 font-semibold">User</th>
                <th className="px-6 py-4 font-semibold">Location</th>
                <th className="px-6 py-4 font-semibold">Profile</th>
                <th className="px-6 py-4 font-semibold">Risk Level</th>
                <th className="px-6 py-4 font-semibold">Score</th>
                <th className="px-6 py-4 font-semibold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/10">
              {isLoading ? (
                <tr><td colSpan={6} className="p-8 text-center text-muted-foreground">Loading users...</td></tr>
              ) : !data?.users.length ? (
                <tr><td colSpan={6} className="p-8 text-center text-muted-foreground">No users found matching criteria.</td></tr>
              ) : (
                data.users.map((user) => (
                  <tr key={user.id} className="hover:bg-white/[0.02] transition-colors group">
                    <td className="px-6 py-4">
                      <div className="font-medium text-foreground">{user.name}</div>
                      <div className="text-xs text-muted-foreground">{user.email}</div>
                    </td>
                    <td className="px-6 py-4 text-muted-foreground">
                      {user.city}
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm capitalize">{user.employmentType?.replace('_', ' ')}</div>
                      <div className="text-xs text-muted-foreground font-mono mt-0.5">{user.monthlyIncome ? formatINR(user.monthlyIncome) : 'N/A'}/mo</div>
                    </td>
                    <td className="px-6 py-4">
                      <Badge className={`uppercase text-[10px] tracking-wider font-bold ${getRiskColor(user.riskLevel)}`}>
                        {user.riskLevel}
                      </Badge>
                    </td>
                    <td className="px-6 py-4">
                      <div className="font-mono font-semibold text-lg">{user.riskScore}</div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="hover-elevate hover:text-primary hover:bg-primary/10 text-xs gap-1.5 rounded-lg px-3"
                        onClick={() => setLocation(`/admin/users/${user.id}`)}
                      >
                        <Eye className="w-3.5 h-3.5" />View Profile
                      </Button>
                      {['high', 'critical'].includes(user.riskLevel) && (
                        <Button variant="ghost" size="icon" className="hover-elevate text-destructive hover:bg-destructive/10 hover:text-destructive ml-1">
                          <AlertTriangle className="w-4 h-4" />
                        </Button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        
        {data && data.totalPages > 1 && (
          <div className="p-4 border-t border-border/50 flex items-center justify-between text-sm text-muted-foreground bg-secondary/10">
            <span>Showing page {data.page} of {data.totalPages}</span>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" disabled={data.page === 1}>Previous</Button>
              <Button variant="outline" size="sm" disabled={data.page === data.totalPages}>Next</Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  )
}
