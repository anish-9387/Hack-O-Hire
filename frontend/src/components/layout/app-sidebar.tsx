import { Link, useLocation } from "wouter"
import { useAuthStore } from "@/hooks/use-store"
import {
  LayoutDashboard,
  Activity,
  PieChart,
  ShieldAlert,
  Sparkles,
  GitCompareArrows,
  Users,
  AlertTriangle,
  ActivitySquare,
  ClipboardList,
  LogOut,
  ChevronRight,
  Globe
} from "lucide-react"
import { 
  Sidebar, 
  SidebarContent, 
  SidebarGroup, 
  SidebarGroupContent, 
  SidebarGroupLabel, 
  SidebarMenu, 
  SidebarMenuButton, 
  SidebarMenuItem,
  SidebarFooter,
  SidebarHeader
} from "@/components/ui/sidebar"
import { Button } from "@/components/ui/button"

export function AppSidebar() {
  const [location] = useLocation()
  const { role, logout, user } = useAuthStore()

  const userRoutes = [
    { title: "Overview", url: "/dashboard", icon: LayoutDashboard },
    { title: "Transactions", url: "/transactions", icon: Activity },
    { title: "Analytics", url: "/analytics", icon: PieChart },
    { title: "Risk Profile", url: "/risk", icon: ShieldAlert },
    { title: "AI Coach", url: "/coach", icon: Sparkles },
    { title: "What-If Simulator", url: "/simulate", icon: GitCompareArrows },
  ]

  const adminRoutes = [
    { title: "Command Center", url: "/admin", icon: LayoutDashboard },
    { title: "Risk Distribution", url: "/admin/risk", icon: ActivitySquare },
    { title: "Customer Base", url: "/admin/users", icon: Users },
    { title: "Interventions", url: "/admin/interventions", icon: AlertTriangle },
    { title: "Model Performance", url: "/admin/model", icon: Sparkles },
    { title: "Cross-Bank Detection", url: "/admin/cross-bank", icon: Globe },
    { title: "Audit Logs", url: "/admin/audit", icon: ClipboardList },
  ]

  const routes = role === 'admin' ? adminRoutes : userRoutes

  return (
    <Sidebar variant="inset" className="border-r border-border/50 bg-background/50 backdrop-blur-xl">
      <SidebarHeader className="p-4">
        <div className="flex items-center gap-3 px-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-info flex items-center justify-center shadow-glow">
            <Sparkles className="w-4 h-4 text-primary-foreground" />
          </div>
          <div>
            <h2 className="font-display font-bold text-lg leading-tight tracking-tight text-foreground">RiskSense</h2>
            <p className="text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">Intelligence</p>
          </div>
        </div>
      </SidebarHeader>

      <SidebarContent className="px-2 mt-4">
        <SidebarGroup>
          <SidebarGroupLabel className="text-xs uppercase tracking-wider text-muted-foreground/70 mb-2">
            {role === 'admin' ? 'Admin Portal' : 'My Finance'}
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu className="gap-1">
              {routes.map((item) => {
                const isActive = location === item.url
                return (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton asChild isActive={isActive} tooltip={item.title}>
                      <Link 
                        href={item.url} 
                        className={`flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 ${
                          isActive 
                            ? 'bg-primary/10 text-primary font-medium' 
                            : 'text-muted-foreground hover:bg-white/5 hover:text-foreground'
                        }`}
                      >
                        <item.icon className={`w-5 h-5 ${isActive ? 'text-primary' : 'text-muted-foreground/70'}`} />
                        <span>{item.title}</span>
                        {isActive && <ChevronRight className="w-4 h-4 ml-auto opacity-50" />}
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                )
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="p-4 mt-auto border-t border-border/50">
        <div className="flex items-center gap-3 mb-4 px-2">
          <div className="w-10 h-10 rounded-full bg-secondary border border-border flex items-center justify-center text-secondary-foreground font-display font-bold">
            {user?.name?.charAt(0) || 'U'}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-foreground truncate">{user?.name}</p>
            <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
          </div>
        </div>
        <Button 
          variant="ghost" 
          className="w-full justify-start text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-xl"
          onClick={() => {
            fetch("/api/auth/logout", {
              method: "POST",
              headers: { Authorization: `Bearer ${useAuthStore.getState().token}` },
            }).catch(() => {})
            logout()
            window.location.href = '/'
          }}
        >
          <LogOut className="w-4 h-4 mr-2" />
          Sign Out
        </Button>
      </SidebarFooter>
    </Sidebar>
  )
}
