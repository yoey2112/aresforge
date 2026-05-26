export function toQuery(params) {
  const query = new URLSearchParams();
  Object.keys(params || {}).forEach((key) => {
    const value = params[key];
    if (value !== undefined && value !== null && String(value).trim()) {
      query.set(key, String(value).trim());
    }
  });
  const rendered = query.toString();
  return rendered ? `?${rendered}` : "";
}

export function prunePayload(payload) {
  Object.keys(payload).forEach((key) => {
    const value = payload[key];
    if (value === "" || value === undefined || value === null) {
      delete payload[key];
      return;
    }
    if (Array.isArray(value) && value.length === 0) {
      delete payload[key];
    }
  });
  return payload;
}

export async function fetchJson(url, options) {
  const response = await fetch(url, options || { method: "GET" });
  const payload = await response.json();
  if (!response.ok || payload.ok === false) {
    const error = new Error(payload.message || payload.error || "Request failed.");
    error.payload = payload;
    throw error;
  }
  return payload;
}