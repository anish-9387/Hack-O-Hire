/**
 * API client that bridges the AI-Pipeline React frontend to the
 * Hack-O-Hire FastAPI backend.
 *
 * All hooks follow the same React Query interface as the original
 * @/lib/api-client generated hooks, so page components
 * work without modification beyond the import path change.
 */
import { useMutation, useQuery } from "@tanstack/react-query";
import { useAuthStore } from "@/hooks/use-store";

// ── Types ──────────────────────────────────────────────────────────────

export type LoginRequestRole = "user" | "admin";

export interface User {
  id: string;
  name: string;
  email: string;
  role: string;
  city?: string;
  state?: string;
  employmentType?: string;
  monthlyIncome?: number;
}

export type GetSpendingAnalyticsPeriod = "7d" | "30d" | "90d" | "1y";
export type GetSpendingAnalyticsParams = { period?: GetSpendingAnalyticsPeriod };

// ── Token refresh logic ───────────────────────────────────────────────

let _refreshPromise: Promise<string> | null = null;

async function _refreshAccessToken(): Promise<string> {
  const state = useAuthStore.getState();
  if (!state.refreshToken) throw new Error("No refresh token");

  const res = await fetch("/api/auth/refresh", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refreshToken: state.refreshToken }),
  });

  if (!res.ok) {
    state.logout();
    window.location.href = "/";
    throw new Error("Session expired — please log in again");
  }

  const data = await res.json();
  state.setToken(data.token, data.expiresIn);
  return data.token;
}

async function _ensureValidToken(): Promise<string | null> {
  const state = useAuthStore.getState();
  if (!state.token) return null;
  if (!state.isTokenExpired()) return state.token;

  // Deduplicate concurrent refresh calls
  if (!_refreshPromise) {
    _refreshPromise = _refreshAccessToken().finally(() => {
      _refreshPromise = null;
    });
  }
  return _refreshPromise;
}

// ── Fetch helper ───────────────────────────────────────────────────────

async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = await _ensureValidToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(`/api${path}`, { ...options, headers });

  // If 401, try one refresh then retry
  if (res.status === 401 && useAuthStore.getState().refreshToken) {
    try {
      const newToken = await _refreshAccessToken();
      headers["Authorization"] = `Bearer ${newToken}`;
      const retry = await fetch(`/api${path}`, { ...options, headers });
      if (!retry.ok) {
        const err = await retry.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${retry.status}`);
      }
      return retry.json();
    } catch {
      useAuthStore.getState().logout();
      window.location.href = "/";
      throw new Error("Session expired");
    }
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// ── Auth ───────────────────────────────────────────────────────────────

interface LoginRequest {
  email: string;
  password: string;
  role: LoginRequestRole;
}
interface LoginResponse {
  token: string;
  refreshToken: string;
  expiresIn: number;
  user: User;
  role: string;
}

interface RegisterRequest {
  email: string;
  password: string;
  name: string;
  role: LoginRequestRole;
}

export function useLogin() {
  return useMutation<LoginResponse, Error, { data: LoginRequest }>({
    mutationFn: ({ data }) =>
      apiFetch<LoginResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  });
}

export function useRegister() {
  return useMutation<LoginResponse, Error, { data: RegisterRequest }>({
    mutationFn: ({ data }) =>
      apiFetch<LoginResponse>("/auth/register", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  });
}

export function useLogout() {
  return useMutation<any, Error, void>({
    mutationFn: () =>
      apiFetch<any>("/auth/logout", { method: "POST" }),
  });
}

// ── Dashboard ──────────────────────────────────────────────────────────

export function useGetDashboardOverview(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ["/api/dashboard/overview"],
    queryFn: () => apiFetch<any>("/dashboard/overview"),
    enabled: options?.enabled !== false,
  });
}

// ── Risk ───────────────────────────────────────────────────────────────

export function useGetRiskScore(params?: any, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ["/api/risk/score"],
    queryFn: () => apiFetch<any>("/risk/score"),
    enabled: options?.enabled !== false,
  });
}

export function useExplainRisk(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ["/api/risk/explain"],
    queryFn: () => apiFetch<any>("/risk/explain"),
    enabled: options?.enabled !== false,
  });
}

export function usePredictFutureRisk(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ["/api/risk/predict"],
    queryFn: () => apiFetch<any>("/risk/predict"),
    enabled: options?.enabled !== false,
  });
}

export function useGetRiskHistory(
  params?: any,
  options?: { enabled?: boolean }
) {
  return useQuery({
    queryKey: ["/api/risk/history"],
    queryFn: () => apiFetch<any>("/risk/history"),
    enabled: options?.enabled !== false,
  });
}

// ── Alerts ─────────────────────────────────────────────────────────────

export function useListAlerts(
  params?: { unreadOnly?: boolean },
  options?: { enabled?: boolean; refetchInterval?: number }
) {
  return useQuery({
    queryKey: ["/api/alerts", params],
    queryFn: () =>
      apiFetch<any>(`/alerts${params?.unreadOnly ? "?unreadOnly=true" : ""}`),
    enabled: options?.enabled !== false,
    refetchInterval: options?.refetchInterval,
  });
}

// ── Spending Analytics ─────────────────────────────────────────────────

export function useGetSpendingAnalytics(params?: { period?: string }) {
  return useQuery({
    queryKey: ["/api/dashboard/spending", params?.period],
    queryFn: () =>
      apiFetch<any>(`/dashboard/spending?period=${params?.period || "30d"}`),
  });
}

// ── Transactions ───────────────────────────────────────────────────────

export function useListTransactions(params?: { limit?: number }) {
  return useQuery({
    queryKey: ["/api/transactions", params],
    queryFn: () =>
      apiFetch<any>(`/transactions?limit=${params?.limit || 50}`),
  });
}

export function useSimulateTransaction() {
  return useMutation<any, Error, { data: any }>({
    mutationFn: ({ data }) =>
      apiFetch<any>("/transactions/simulate", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  });
}

export function useCreateTransaction() {
  return useMutation<any, Error, { data: any }>({
    mutationFn: ({ data }) =>
      apiFetch<any>("/transactions/create", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  });
}

// ── Coach ──────────────────────────────────────────────────────────────

export function useGetCoachAdvice(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ["/api/coach/advice"],
    queryFn: () => apiFetch<any>("/coach/advice"),
    enabled: options?.enabled !== false,
  });
}

// ── What-If Simulator ──────────────────────────────────────────────────

export function useWhatIfSimulation() {
  return useMutation<any, Error, { data: any }>({
    mutationFn: ({ data }) =>
      apiFetch<any>("/simulation/what-if", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  });
}

// ── Admin ──────────────────────────────────────────────────────────────

export function useGetAdminOverview(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ["/api/admin/overview"],
    queryFn: () => apiFetch<any>("/admin/overview"),
    enabled: options?.enabled !== false,
  });
}

export function useGetHighRiskUsers(params?: { limit?: number }) {
  return useQuery({
    queryKey: ["/api/admin/high-risk-users", params],
    queryFn: () =>
      apiFetch<any>(`/admin/high-risk-users?limit=${params?.limit || 8}`),
  });
}

export function useGetCityAnalytics(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ["/api/admin/city-analytics"],
    queryFn: () => apiFetch<any>("/admin/city-analytics"),
    enabled: options?.enabled !== false,
  });
}

export function useGetAdminAlerts(params?: any, options?: any) {
  return useQuery({
    queryKey: ["/api/admin/alerts", params],
    queryFn: () =>
      apiFetch<any>(
        `/admin/alerts?severity=${params?.severity || "critical"}&limit=${params?.limit || 10}`
      ),
    enabled: options?.enabled !== false,
  });
}

export function useGetRiskDistribution(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ["/api/admin/risk-distribution"],
    queryFn: () => apiFetch<any>("/admin/risk-distribution"),
    enabled: options?.enabled !== false,
  });
}

export function useCreateIntervention() {
  return useMutation<any, Error, { data: any }>({
    mutationFn: ({ data }) =>
      apiFetch<any>("/admin/interventions/create", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  });
}

export function useListUsers(params?: any) {
  return useQuery({
    queryKey: ["/api/admin/users", params],
    queryFn: () => {
      const q = new URLSearchParams();
      if (params?.search) q.set("search", params.search);
      if (params?.riskLevel) q.set("riskLevel", params.riskLevel);
      if (params?.limit) q.set("limit", String(params.limit));
      return apiFetch<any>(`/admin/users?${q.toString()}`);
    },
  });
}

export async function exportExcel(riskLevel?: string): Promise<void> {
  const token = await _ensureValidToken();
  const q = new URLSearchParams();
  if (riskLevel && riskLevel !== "all") q.set("riskLevel", riskLevel);
  const url = `/api/admin/export-excel?${q.toString()}`;

  const res = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  if (!res.ok) {
    const errBody = await res.text().catch(() => "");
    const msg = `Export failed (HTTP ${res.status}). ${errBody}`;
    alert(msg);
    throw new Error(msg);
  }

  const blob = await res.blob();
  if (blob.size === 0) {
    alert("Export returned an empty file.");
    throw new Error("Empty export response");
  }
  const blobUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = blobUrl;
  a.download = `credit_risk_report_${new Date().toISOString().slice(0, 10)}.xlsx`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  // Delay revocation so the browser has time to start the download
  setTimeout(() => URL.revokeObjectURL(blobUrl), 1000);
}

export function useGetUserProfile(id: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ["/api/admin/users", id],
    queryFn: () => apiFetch<any>(`/admin/users/${id}`),
    enabled: options?.enabled !== false && !!id,
  });
}

export function useGetModelPerformance(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ["/api/admin/model-performance"],
    queryFn: () => apiFetch<any>("/admin/model-performance"),
    enabled: options?.enabled !== false,
  });
}

export function useGetAuditLogs(params?: any) {
  return useQuery({
    queryKey: ["/api/admin/audit-logs", params],
    queryFn: () => apiFetch<any>("/admin/audit-logs"),
  });
}

// ── Aliases & missing hooks ────────────────────────────────────────────

/** Coach advice (alias for useGetCoachAdvice) */
export const useGetFinancialAdvice = useGetCoachAdvice;

/** What-if simulation (alias) */
export const useRunWhatIfSimulation = useWhatIfSimulation;

/** List interventions */
export function useListInterventions(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ["/api/admin/interventions"],
    queryFn: () => apiFetch<any>("/admin/interventions"),
    enabled: options?.enabled !== false,
  });
}

// ── Cross-Bank Defaulter Detection ────────────────────────────────────

export function useGetCrossBankStats(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ["/api/cross-bank/stats"],
    queryFn: () => apiFetch<any>("/cross-bank/stats"),
    enabled: options?.enabled !== false,
  });
}

export function useGetCrossBankAlerts(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ["/api/admin/cross-bank-alerts"],
    queryFn: () => apiFetch<any>("/admin/cross-bank-alerts"),
    enabled: options?.enabled !== false,
  });
}

export function useCrossBankCheck() {
  return useMutation<any, Error, { data: { pan: string; phone: string; exclude_bank_id?: string } }>({
    mutationFn: ({ data }) =>
      apiFetch<any>("/cross-bank/check", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  });
}

export function useCrossBankReport() {
  return useMutation<any, Error, { data: any }>({
    mutationFn: ({ data }) =>
      apiFetch<any>("/cross-bank/report", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  });
}

export function useSeedCrossBankDemo() {
  return useMutation<any, Error, void>({
    mutationFn: () =>
      apiFetch<any>("/cross-bank/seed-demo", { method: "POST" }),
  });
}

export function useCrossBankPredict() {
  return useMutation<any, Error, { data: any }>({
    mutationFn: ({ data }) =>
      apiFetch<any>("/cross-bank/predict", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  });
}

// ── Type aliases (match original generated types) ──────────────────────

export type SimulateTransactionRequestType = "debit" | "credit";
export type ListUsersRiskLevel = "low" | "medium" | "high" | "critical";
export type WhatIfRequestScenario = string;
