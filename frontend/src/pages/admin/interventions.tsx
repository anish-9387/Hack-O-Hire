import { useState } from "react"
import { useListInterventions, useCreateIntervention } from "@/lib/api-client"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { AlertTriangle, Clock, CheckCircle2, Plus } from "lucide-react"

const getStatusColor = (status: string) => {
  switch(status) {
    case 'completed': return 'text-success border-success/30 bg-success/10'
    case 'active': return 'text-primary border-primary/30 bg-primary/10'
    case 'pending': return 'text-warning border-warning/30 bg-warning/10'
    default: return 'text-muted-foreground border-border bg-secondary'
  }
}

export default function AdminInterventions() {
  const { data, isLoading, refetch } = useListInterventions()

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-display font-bold tracking-tight">Active Interventions</h1>
          <p className="text-muted-foreground mt-1">Manage proactive steps taken to assist high-risk customers.</p>
        </div>
        <NewInterventionModal onSuccess={() => refetch()} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {isLoading ? (
           <div className="col-span-full text-center p-8 text-muted-foreground animate-pulse">Loading interventions...</div>
        ) : !data?.length ? (
           <div className="col-span-full text-center p-12 bg-secondary/20 rounded-2xl border border-border/50 text-muted-foreground">No active interventions found.</div>
        ) : (
          data.map((item) => (
            <Card key={item.id} className="glass-panel p-5 flex flex-col">
              <div className="flex justify-between items-start mb-4">
                <Badge variant="outline" className={`capitalize font-medium ${getStatusColor(item.status)}`}>
                  {item.status}
                </Badge>
                {item.priority === 'urgent' && <Badge className="bg-destructive text-destructive-foreground animate-pulse">Urgent</Badge>}
              </div>
              
              <h3 className="text-lg font-bold mb-1 truncate">{item.userName || "Unknown User"}</h3>
              <p className="text-sm text-primary font-medium capitalize mb-4">{item.type.replace(/_/g, ' ')}</p>
              
              <p className="text-sm text-muted-foreground line-clamp-2 mb-6 flex-1">
                {item.description || "No description provided."}
              </p>
              
              <div className="pt-4 border-t border-border/50 flex items-center justify-between text-xs text-muted-foreground">
                <div className="flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5" />
                  {new Date(item.createdAt).toLocaleDateString()}
                </div>
                <div>Assignee: <span className="font-medium text-foreground">{item.assignedTo || 'Unassigned'}</span></div>
              </div>
            </Card>
          ))
        )}
      </div>
    </div>
  )
}

function NewInterventionModal({ onSuccess }: { onSuccess: () => void }) {
  const [open, setOpen] = useState(false)
  const [userId, setUserId] = useState("")
  const [type, setType] = useState("")
  const [priority, setPriority] = useState("")
  
  const mutation = useCreateIntervention()

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if(!userId || !type || !priority) return

    mutation.mutate({
      data: { userId, type, priority, description: "Admin initiated intervention." }
    }, {
      onSuccess: () => {
        setOpen(false)
        onSuccess()
        setUserId("")
        setType("")
        setPriority("")
      }
    })
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="bg-primary text-primary-foreground shadow-glow">
          <Plus className="w-4 h-4 mr-2" /> Create Intervention
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px] bg-card border-border/50">
        <DialogHeader>
          <DialogTitle>New Intervention Task</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4 pt-4">
          <div className="space-y-2">
            <Label>Customer ID</Label>
            <Input 
              required
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              placeholder="USR-12345"
              className="bg-secondary/50 border-border/50"
            />
          </div>
          
          <div className="space-y-2">
            <Label>Action Type</Label>
            <Select required value={type} onValueChange={setType}>
              <SelectTrigger className="bg-secondary/50 border-border/50">
                <SelectValue placeholder="Select action..." />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="outreach_call">Customer Outreach Call</SelectItem>
                <SelectItem value="emi_restructure">Propose EMI Restructure</SelectItem>
                <SelectItem value="credit_limit_reduction">Reduce Credit Limit</SelectItem>
                <SelectItem value="digital_coaching">Trigger Digital Coach</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>Priority</Label>
            <Select required value={priority} onValueChange={setPriority}>
              <SelectTrigger className="bg-secondary/50 border-border/50">
                <SelectValue placeholder="Select priority..." />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="low">Low</SelectItem>
                <SelectItem value="medium">Medium</SelectItem>
                <SelectItem value="high">High</SelectItem>
                <SelectItem value="urgent">Urgent</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <Button type="submit" className="w-full mt-4" disabled={mutation.isPending}>
            {mutation.isPending ? "Creating..." : "Dispatch Intervention"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  )
}
