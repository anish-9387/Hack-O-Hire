import { Switch, Route, Router as WouterRouter } from "wouter"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { Toaster } from "@/components/ui/toaster"
import { TooltipProvider } from "@/components/ui/tooltip"

import { Layout } from "@/components/layout/layout"
import NotFound from "@/pages/not-found"

// Pages
import Login from "@/pages/auth/login"
import UserDashboard from "@/pages/user/dashboard"
import Transactions from "@/pages/user/transactions"
import Analytics from "@/pages/user/analytics"
import RiskExplanation from "@/pages/user/risk-explanation"
import Coach from "@/pages/user/coach"
import WhatIfSimulator from "@/pages/user/what-if"

import AdminDashboard from "@/pages/admin/dashboard"
import AdminRiskDistribution from "@/pages/admin/risk-distribution"
import AdminUsers from "@/pages/admin/users"
import AdminInterventions from "@/pages/admin/interventions"
import AdminModelPerformance from "@/pages/admin/model-performance"
import AdminAuditLogs from "@/pages/admin/audit-logs"
import AdminUserDetail from "@/pages/admin/user-detail"
import AdminCrossBank from "@/pages/admin/cross-bank"

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000,
    },
  },
})

function Router() {
  return (
    <Switch>
      <Route path="/" component={Login} />
      
      {/* User Routes */}
      <Route path="/dashboard"><Layout><UserDashboard /></Layout></Route>
      <Route path="/transactions"><Layout><Transactions /></Layout></Route>
      <Route path="/analytics"><Layout><Analytics /></Layout></Route>
      <Route path="/risk"><Layout><RiskExplanation /></Layout></Route>
      <Route path="/coach"><Layout><Coach /></Layout></Route>
      <Route path="/simulate"><Layout><WhatIfSimulator /></Layout></Route>
      
      {/* Admin Routes */}
      <Route path="/admin"><Layout><AdminDashboard /></Layout></Route>
      <Route path="/admin/risk"><Layout><AdminRiskDistribution /></Layout></Route>
      <Route path="/admin/users/:id"><Layout><AdminUserDetail /></Layout></Route>
      <Route path="/admin/users"><Layout><AdminUsers /></Layout></Route>
      <Route path="/admin/interventions"><Layout><AdminInterventions /></Layout></Route>
      <Route path="/admin/model"><Layout><AdminModelPerformance /></Layout></Route>
      <Route path="/admin/audit"><Layout><AdminAuditLogs /></Layout></Route>
      <Route path="/admin/cross-bank"><Layout><AdminCrossBank /></Layout></Route>

      <Route component={NotFound} />
    </Switch>
  )
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, "")}>
          <Router />
        </WouterRouter>
        <Toaster />
      </TooltipProvider>
    </QueryClientProvider>
  )
}

export default App;
