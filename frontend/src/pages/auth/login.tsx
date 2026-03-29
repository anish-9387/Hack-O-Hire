import { useState } from "react"
import { useLocation } from "wouter"
import { useAuthStore } from "@/hooks/use-store"
import { useLogin, useRegister, type LoginRequestRole } from "@/lib/api-client"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Sparkles, ArrowRight, ShieldCheck, Activity, Zap, UserPlus, LogIn } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"

export default function Login() {
  const [, setLocation] = useLocation()
  const { setAuth } = useAuthStore()
  const loginMutation = useLogin()
  const registerMutation = useRegister()

  const [isRegister, setIsRegister] = useState(false)
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [name, setName] = useState("")
  const [role, setRole] = useState<LoginRequestRole>("user")
  const [error, setError] = useState("")

  const handleSuccess = (data: any) => {
    setAuth(data.token, data.user, data.role, data.refreshToken, data.expiresIn)
    setLocation(data.role === 'admin' ? '/admin' : '/dashboard')
  }

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault()
    setError("")
    loginMutation.mutate({ data: { email, password, role } }, {
      onSuccess: handleSuccess,
      onError: (err) => setError(err.message || "Invalid credentials"),
    })
  }

  const handleRegister = (e: React.FormEvent) => {
    e.preventDefault()
    setError("")
    if (password !== confirmPassword) {
      setError("Passwords do not match")
      return
    }
    if (password.length < 6) {
      setError("Password must be at least 6 characters")
      return
    }
    registerMutation.mutate({ data: { email, password, name, role } }, {
      onSuccess: handleSuccess,
      onError: (err) => setError(err.message || "Registration failed"),
    })
  }

  const demoLogin = (isUser: boolean) => {
    const demoEmail = isUser ? "user@demo.com" : "admin@demo.com"
    const demoPassword = isUser ? "demo123" : "admin123"
    const demoRole: LoginRequestRole = isUser ? "user" : "admin"
    setEmail(demoEmail)
    setPassword(demoPassword)
    setRole(demoRole)
    setError("")
    loginMutation.mutate({ data: { email: demoEmail, password: demoPassword, role: demoRole } }, {
      onSuccess: handleSuccess,
      onError: (err) => setError(err.message || "Invalid credentials"),
    })
  }

  const isPending = loginMutation.isPending || registerMutation.isPending

  return (
    <div className="min-h-screen w-full flex bg-background selection:bg-primary/30">
      {/* Left side - Visuals */}
      <div className="hidden lg:flex flex-1 relative items-center justify-center overflow-hidden border-r border-border/50">
        <div className="absolute inset-0 z-0">
          <img
            src={`${import.meta.env.BASE_URL}images/auth-bg.png`}
            alt="Abstract fintech background"
            className="w-full h-full object-cover opacity-60"
          />
          <div className="absolute inset-0 bg-gradient-to-r from-background via-background/80 to-transparent"></div>
        </div>

        <div className="relative z-10 p-12 max-w-2xl">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            <div className="flex items-center gap-3 mb-8">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary to-info flex items-center justify-center shadow-glow">
                <Sparkles className="w-6 h-6 text-primary-foreground" />
              </div>
              <h1 className="text-3xl font-display font-bold text-foreground tracking-tight">RiskSense</h1>
            </div>

            <h2 className="text-5xl font-display font-bold text-foreground leading-[1.1] tracking-tight mb-6">
              Predictive intelligence for <span className="text-gradient">modern banking.</span>
            </h2>
            <p className="text-lg text-muted-foreground leading-relaxed mb-12 max-w-xl">
              Monitor financial health scores in real-time, predict credit risk before it happens, and deliver hyper-personalized coaching to your customers.
            </p>

            <div className="space-y-6">
              {[
                { icon: ShieldCheck, title: "Real-time Risk Scoring", desc: "Continuous monitoring of transaction streams." },
                { icon: Activity, title: "Behavioral Analytics", desc: "Identify stress indicators early." },
                { icon: Zap, title: "AI-Powered Coaching", desc: "Automated personalized financial interventions." }
              ].map((feature, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.5, delay: 0.3 + (i * 0.1) }}
                  className="flex items-center gap-4 p-4 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm"
                >
                  <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center">
                    <feature.icon className="w-5 h-5 text-primary" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-foreground">{feature.title}</h3>
                    <p className="text-sm text-muted-foreground">{feature.desc}</p>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </div>
      </div>

      {/* Right side - Form */}
      <div className="flex-1 flex flex-col justify-center px-8 sm:px-12 lg:px-24 xl:px-32">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5 }}
          className="w-full max-w-md mx-auto"
        >
          <div className="mb-10 lg:hidden flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-primary to-info flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-primary-foreground" />
            </div>
            <h1 className="text-2xl font-display font-bold">RiskSense</h1>
          </div>

          <AnimatePresence mode="wait">
            <motion.div
              key={isRegister ? "register" : "login"}
              initial={{ opacity: 0, x: isRegister ? 20 : -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: isRegister ? -20 : 20 }}
              transition={{ duration: 0.3 }}
            >
              <h2 className="text-3xl font-display font-bold mb-2">
                {isRegister ? "Create account" : "Welcome back"}
              </h2>
              <p className="text-muted-foreground mb-8">
                {isRegister
                  ? "Sign up to access the credit risk platform."
                  : "Enter your credentials to access the platform."}
              </p>

              <form onSubmit={isRegister ? handleRegister : handleLogin} className="space-y-5">
                {isRegister && (
                  <div className="space-y-2">
                    <Label htmlFor="name">Full Name</Label>
                    <Input
                      id="name"
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="John Doe"
                      className="h-12 bg-secondary/50 border-border/50 focus:border-primary focus:ring-primary/20 rounded-xl"
                      required
                    />
                  </div>
                )}

                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="name@example.com"
                    className="h-12 bg-secondary/50 border-border/50 focus:border-primary focus:ring-primary/20 rounded-xl"
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="password">Password</Label>
                  <Input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder={isRegister ? "Min. 6 characters" : ""}
                    className="h-12 bg-secondary/50 border-border/50 focus:border-primary focus:ring-primary/20 rounded-xl"
                    required
                  />
                </div>

                {isRegister && (
                  <div className="space-y-2">
                    <Label htmlFor="confirmPassword">Confirm Password</Label>
                    <Input
                      id="confirmPassword"
                      type="password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      className="h-12 bg-secondary/50 border-border/50 focus:border-primary focus:ring-primary/20 rounded-xl"
                      required
                    />
                  </div>
                )}

                <div className="space-y-3">
                  <Label>{isRegister ? "Account type" : "Sign in as"}</Label>
                  <div className="grid grid-cols-2 gap-3">
                    <div
                      className={`border rounded-xl p-3 cursor-pointer transition-all ${role === 'user' ? 'border-primary bg-primary/10' : 'border-border/50 hover:border-primary/50 bg-secondary/20'}`}
                      onClick={() => setRole('user')}
                    >
                      <div className="font-semibold text-sm">Customer</div>
                      <div className="text-xs text-muted-foreground mt-0.5">View personal dashboard</div>
                    </div>
                    <div
                      className={`border rounded-xl p-3 cursor-pointer transition-all ${role === 'admin' ? 'border-primary bg-primary/10' : 'border-border/50 hover:border-primary/50 bg-secondary/20'}`}
                      onClick={() => setRole('admin')}
                    >
                      <div className="font-semibold text-sm">Bank Admin</div>
                      <div className="text-xs text-muted-foreground mt-0.5">Access risk intelligence</div>
                    </div>
                  </div>
                </div>

                <Button
                  type="submit"
                  className="w-full h-12 rounded-xl text-md font-semibold bg-primary hover:bg-primary/90 text-primary-foreground shadow-glow"
                  disabled={isPending}
                >
                  {isPending ? (isRegister ? "Creating account..." : "Authenticating...") : (
                    <>
                      {isRegister ? "Create Account" : "Sign In"}
                      {isRegister ? <UserPlus className="w-4 h-4 ml-2" /> : <ArrowRight className="w-4 h-4 ml-2" />}
                    </>
                  )}
                </Button>

                {error && (
                  <p className="text-destructive text-sm text-center">{error}</p>
                )}
              </form>

              <div className="mt-6 text-center">
                <button
                  type="button"
                  className="text-sm text-primary hover:text-primary/80 transition-colors font-medium"
                  onClick={() => { setIsRegister(!isRegister); setError("") }}
                >
                  {isRegister ? (
                    <span className="flex items-center justify-center gap-1.5">
                      <LogIn className="w-3.5 h-3.5" /> Already have an account? Sign in
                    </span>
                  ) : (
                    <span className="flex items-center justify-center gap-1.5">
                      <UserPlus className="w-3.5 h-3.5" /> Don't have an account? Register
                    </span>
                  )}
                </button>
              </div>
            </motion.div>
          </AnimatePresence>

          {!isRegister && (
            <>
              <div className="mt-10 relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-border/50"></div>
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-4 bg-background text-muted-foreground">Or use demo accounts</span>
                </div>
              </div>

              <div className="mt-8 grid grid-cols-2 gap-4">
                <Button variant="outline" className="h-10 rounded-xl border-border/50 bg-secondary/20 hover:bg-secondary/40" onClick={() => demoLogin(true)}>
                  Demo User
                </Button>
                <Button variant="outline" className="h-10 rounded-xl border-border/50 bg-secondary/20 hover:bg-secondary/40" onClick={() => demoLogin(false)}>
                  Demo Admin
                </Button>
              </div>
            </>
          )}
        </motion.div>
      </div>
    </div>
  )
}
