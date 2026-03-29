import React from "react"
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar"
import { AppSidebar } from "./app-sidebar"
import { useAuthStore } from "@/hooks/use-store"
import { Redirect, useLocation } from "wouter"
import { useListAlerts } from "@/lib/api-client"
import { BellRing } from "lucide-react"

export function Layout({ children }: { children: React.ReactNode }) {
  const { token, user } = useAuthStore()
  const [location] = useLocation()
  const { data: alerts } = useListAlerts({ unreadOnly: true }, { 
    enabled: !!token && user?.role !== 'admin',
    refetchInterval: 60000
  })

  if (!token) {
    return <Redirect to="/" />
  }

  const unreadCount = Array.isArray(alerts) ? alerts.filter((a: any) => !a.isRead).length : 0

  const style = {
    "--sidebar-width": "16rem",
    "--sidebar-width-icon": "4rem",
  } as React.CSSProperties

  const getPageTitle = () => {
    const pathMap: Record<string, string> = {
      '/dashboard': 'Dashboard',
      '/transactions': 'Transactions',
      '/analytics': 'Analytics',
      '/risk': 'Risk X-Ray',
      '/coach': 'AI Coach',
      '/simulate': 'What-If Simulator',
      '/admin': 'Risk Operations Center',
      '/admin/risk': 'Risk Distribution',
      '/admin/users': 'User Management',
      '/admin/interventions': 'Interventions',
      '/admin/model': 'Model Performance',
      '/admin/audit': 'Audit Logs',
    }
    return pathMap[location] || 'RiskSense'
  }

  return (
    <SidebarProvider style={style}>
      <div className="flex min-h-screen w-full bg-background text-foreground selection:bg-primary/30">
        <AppSidebar />
        <div className="flex flex-col flex-1 min-w-0 relative">
          <header className="sticky top-0 z-50 flex h-16 shrink-0 items-center gap-4 border-b border-border/50 bg-background/80 backdrop-blur-xl px-6">
            <SidebarTrigger className="text-muted-foreground hover:text-foreground transition-colors" />
            <div className="hidden md:flex items-center gap-2 text-sm text-muted-foreground">
              <span className="text-foreground font-semibold">{getPageTitle()}</span>
            </div>
            <div className="flex-1" />
            {unreadCount > 0 && (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-destructive/10 border border-destructive/20 cursor-pointer hover:bg-destructive/20 transition-colors">
                <BellRing className="w-4 h-4 text-destructive animate-pulse" />
                <span className="text-xs font-bold text-destructive">{unreadCount}</span>
              </div>
            )}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-success/10 border border-success/20">
              <div className="w-2 h-2 rounded-full bg-success animate-pulse shadow-[0_0_8px_hsla(var(--success))]"></div>
              <span className="text-xs font-medium text-success uppercase tracking-wider">Live</span>
            </div>
            {user && (
              <div className="hidden sm:flex items-center gap-2 pl-3 border-l border-border/50">
                <div className="w-7 h-7 rounded-full bg-primary/20 flex items-center justify-center text-xs font-bold text-primary">
                  {user.name?.split(' ').map((n: string) => n[0]).join('').substring(0, 2)}
                </div>
                <div className="hidden lg:block">
                  <p className="text-xs font-semibold leading-none">{user.name?.split(' ')[0]}</p>
                  <p className="text-[10px] text-muted-foreground capitalize mt-0.5">{user.role}</p>
                </div>
              </div>
            )}
          </header>
          <main className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8">
            <div className="mx-auto max-w-7xl">
              {children}
            </div>
          </main>
        </div>
      </div>
    </SidebarProvider>
  )
}
