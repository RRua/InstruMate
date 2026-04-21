/**
 * API client for InstruMate backend.
 * All endpoints are relative so the frontend works both in dev and behind
 * the FastAPI static-file mount.
 */

const BASE = "/api";

function getApiKey() {
  return localStorage.getItem("instrumate_api_key") || "";
}

export function setApiKey(key) {
  localStorage.setItem("instrumate_api_key", key);
}

async function request(path, options = {}) {
  const apiKey = getApiKey();
  if (apiKey) {
    options.headers = { ...options.headers, "X-API-Key": apiKey };
  }
  const res = await fetch(`${BASE}${path}`, options);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// Health
export const getHealth = () => request("/health");

// Analysis
export const uploadAndAnalyze = (file, analyzers = "basic,callgraph,andex,content++,possible_modifications") => {
  const form = new FormData();
  form.append("file", file);
  return request(`/analyze?analyzers=${encodeURIComponent(analyzers)}`, {
    method: "POST",
    body: form,
  });
};

export const getAnalysisJob = (jobId) => request(`/analyze/${jobId}`);

// Apps
export const listApps = (params = {}) => {
  const qs = new URLSearchParams();
  if (params.q) qs.set("q", params.q);
  if (params.page) qs.set("page", params.page);
  if (params.per_page) qs.set("per_page", params.per_page);
  if (params.has_classification !== undefined) qs.set("has_classification", params.has_classification);
  if (params.has_virustotal_report !== undefined) qs.set("has_virustotal_report", params.has_virustotal_report);
  if (params.is_variant !== undefined) qs.set("is_variant", params.is_variant);
  const qsStr = qs.toString();
  return request(`/apps${qsStr ? `?${qsStr}` : ""}`);
};
export const getAppDetail = (appId) => request(`/apps/${appId}`);
export const getAppAnalysis = (appId) => request(`/apps/${appId}/analysis`);

// Call Graph
export const getCallGraph = (appId, limit = 500, filter = "") => {
  const qs = new URLSearchParams({ limit });
  if (filter) qs.set("filter", filter);
  return request(`/apps/${appId}/callgraph?${qs.toString()}`);
};

// Download & Export
export const getDownloadUrl = (appId) => {
  const apiKey = getApiKey();
  const headers = apiKey ? `?_apikey=${encodeURIComponent(apiKey)}` : "";
  return `${BASE}/apps/${appId}/download${headers}`;
};
export const getExportUrl = (appId) => {
  const apiKey = getApiKey();
  const headers = apiKey ? `?_apikey=${encodeURIComponent(apiKey)}` : "";
  return `${BASE}/apps/${appId}/export${headers}`;
};

// Variants
export const createVariants = (appId, makers, specs) =>
  request(`/apps/${appId}/variants`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ variant_makers: makers, variant_specs: specs }),
  });
export const listVariants = (appId) => request(`/apps/${appId}/variants`);

// Classification
export const triggerClassification = (appId, model) => {
  const qs = model ? `?model=${encodeURIComponent(model)}` : "";
  return request(`/apps/${appId}/classify${qs}`, { method: "POST" });
};
export const getClassifyJob = (jobId) => request(`/classify/${jobId}`);
export const getClassification = (appId) => request(`/apps/${appId}/classification`);
export const getSecurityMetrics = (appId) => request(`/apps/${appId}/metrics`);

// VirusTotal
export const submitToVirusTotal = (appId) =>
  request(`/apps/${appId}/virustotal`, { method: "POST" });
export const getVTJob = (jobId) => request(`/virustotal/${jobId}`);
export const getVTReport = (appId) => request(`/apps/${appId}/virustotal`);
