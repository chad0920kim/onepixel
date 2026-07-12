// Static-asset ignore files (.assetsignore / .gitignore) aren't reliably
// honored by every deploy target (Pages in particular ignores both), so
// sensitive/internal paths are denied here in code instead — this is the
// one place both the Workers and Pages (_worker.js) deployments share.
const DENIED_PATH_PATTERN = /^\/(\.|admob\/|wrangler(\.pages)?\.toml$|_?worker\.js$)/;

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (DENIED_PATH_PATTERN.test(url.pathname)) {
      return new Response("Not found", { status: 404 });
    }

    if (url.pathname === "/api/admob-revenue") {
      return handleAdmobRevenue(env);
    }

    if (url.pathname === "/api/suggestions") {
      if (request.method === "POST") return handlePostSuggestion(request, env);
      if (request.method === "GET") return handleGetSuggestions(env);
      return new Response("Method Not Allowed", { status: 405 });
    }

    return env.ASSETS.fetch(request);
  }
};

async function handleAdmobRevenue(env) {
  try {
    const accessToken = await getAccessToken(env);
    const today = new Date();
    const start = new Date(today);
    start.setDate(start.getDate() - 30);

    const [usdRows, krwRows] = await Promise.all([
      fetchNetworkReport(env, accessToken, start, today, "USD"),
      fetchNetworkReport(env, accessToken, start, today, "KRW")
    ]);

    const krwByApp = new Map(
      krwRows
        .filter((chunk) => chunk.row)
        .map((chunk) => [
          chunk.row.dimensionValues?.APP?.value,
          Number(chunk.row.metricValues?.ESTIMATED_EARNINGS?.microsValue || 0) / 1_000_000
        ])
    );

    const apps = usdRows
      .filter((chunk) => chunk.row)
      .map((chunk) => {
        const dims = chunk.row.dimensionValues || {};
        const mets = chunk.row.metricValues || {};
        return {
          app: dims.APP?.displayLabel || dims.APP?.value || "알 수 없음",
          earnings: Number(mets.ESTIMATED_EARNINGS?.microsValue || 0) / 1_000_000,
          earningsKrw: krwByApp.get(dims.APP?.value) || 0,
          impressions: Number(mets.IMPRESSIONS?.integerValue || 0),
          clicks: Number(mets.CLICKS?.integerValue || 0),
          ctr: Number(mets.IMPRESSION_CTR?.doubleValue || 0)
        };
      });

    const totalEarnings = apps.reduce((sum, a) => sum + a.earnings, 0);
    const totalEarningsKrw = apps.reduce((sum, a) => sum + a.earningsKrw, 0);

    return new Response(
      JSON.stringify({
        currency: "USD",
        totalEarnings,
        totalEarningsKrw,
        rangeDays: 30,
        apps
      }),
      { headers: { "Content-Type": "application/json" } }
    );
  } catch (err) {
    return new Response(JSON.stringify({ error: "internal_error", detail: String(err) }), {
      status: 500,
      headers: { "Content-Type": "application/json" }
    });
  }
}

async function fetchNetworkReport(env, accessToken, start, end, currencyCode) {
  const res = await fetch(
    `https://admob.googleapis.com/v1/accounts/${env.ADMOB_PUBLISHER_ID}/networkReport:generate`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        reportSpec: {
          dateRange: {
            startDate: dateParts(start),
            endDate: dateParts(end)
          },
          metrics: ["ESTIMATED_EARNINGS", "IMPRESSIONS", "CLICKS", "IMPRESSION_CTR"],
          dimensions: ["APP"],
          sortConditions: [{ metric: "ESTIMATED_EARNINGS", order: "DESCENDING" }],
          localizationSettings: { currencyCode }
        }
      })
    }
  );

  if (!res.ok) {
    throw new Error(`admob_api_error(${currencyCode}): ${await res.text()}`);
  }

  return res.json();
}

async function getAccessToken(env) {
  const res = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      client_id: env.ADMOB_CLIENT_ID,
      client_secret: env.ADMOB_CLIENT_SECRET,
      refresh_token: env.ADMOB_REFRESH_TOKEN,
      grant_type: "refresh_token"
    })
  });

  if (!res.ok) {
    throw new Error(`token_refresh_failed: ${await res.text()}`);
  }

  const data = await res.json();
  return data.access_token;
}

function dateParts(date) {
  return {
    year: date.getFullYear(),
    month: date.getMonth() + 1,
    day: date.getDate()
  };
}

const MAX_SUGGESTION_LENGTH = 500;
const RATE_LIMIT_MAX = 5;
const RATE_LIMIT_WINDOW_SECONDS = 60 * 60; // 1 hour
const URL_PATTERN = /https?:\/\/|www\.|[a-z0-9-]+\.(com|net|org|io|co|xyz|top|shop|biz|info)\b/i;

async function handlePostSuggestion(request, env) {
  let body;
  try {
    body = await request.json();
  } catch {
    return new Response(JSON.stringify({ error: "invalid_json" }), {
      status: 400,
      headers: { "Content-Type": "application/json" }
    });
  }

  // Honeypot: a real user never fills this hidden field; bots that
  // auto-fill every input on the form do.
  if (String(body.website || "").trim()) {
    return new Response(JSON.stringify({ ok: true }), {
      headers: { "Content-Type": "application/json" }
    });
  }

  const text = String(body.text || "").trim();
  if (!text) {
    return new Response(JSON.stringify({ error: "empty_text" }), {
      status: 400,
      headers: { "Content-Type": "application/json" }
    });
  }
  if (text.length > MAX_SUGGESTION_LENGTH) {
    return new Response(JSON.stringify({ error: "text_too_long", max: MAX_SUGGESTION_LENGTH }), {
      status: 400,
      headers: { "Content-Type": "application/json" }
    });
  }
  if (URL_PATTERN.test(text)) {
    return new Response(JSON.stringify({ error: "links_not_allowed" }), {
      status: 400,
      headers: { "Content-Type": "application/json" }
    });
  }

  const ip = request.headers.get("CF-Connecting-IP") || "unknown";
  const rateLimited = await isRateLimited(env, ip);
  if (rateLimited) {
    return new Response(JSON.stringify({ error: "rate_limited" }), {
      status: 429,
      headers: { "Content-Type": "application/json" }
    });
  }

  const createdAt = new Date().toISOString();
  const key = `sugg:${Date.now()}:${crypto.randomUUID()}`;
  await env.SUGGESTIONS.put(key, JSON.stringify({ text, createdAt }));
  await bumpRateLimit(env, ip);

  return new Response(JSON.stringify({ ok: true }), {
    headers: { "Content-Type": "application/json" }
  });
}

async function isRateLimited(env, ip) {
  const count = Number((await env.SUGGESTIONS.get(`rl:${ip}`)) || 0);
  return count >= RATE_LIMIT_MAX;
}

async function bumpRateLimit(env, ip) {
  const rlKey = `rl:${ip}`;
  const count = Number((await env.SUGGESTIONS.get(rlKey)) || 0);
  await env.SUGGESTIONS.put(rlKey, String(count + 1), { expirationTtl: RATE_LIMIT_WINDOW_SECONDS });
}

async function handleGetSuggestions(env) {
  const list = await env.SUGGESTIONS.list({ prefix: "sugg:" });
  const items = await Promise.all(
    list.keys.map(async (k) => {
      const raw = await env.SUGGESTIONS.get(k.name);
      if (!raw) return null;
      try {
        return JSON.parse(raw);
      } catch {
        return null;
      }
    })
  );

  const suggestions = items
    .filter(Boolean)
    .sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));

  return new Response(JSON.stringify({ suggestions }), {
    headers: { "Content-Type": "application/json" }
  });
}
