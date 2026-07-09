export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === "/api/admob-revenue") {
      return handleAdmobRevenue(env);
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

    const reportRes = await fetch(
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
              endDate: dateParts(today)
            },
            metrics: ["ESTIMATED_EARNINGS", "IMPRESSIONS", "CLICKS", "IMPRESSION_CTR"],
            dimensions: ["APP"],
            sortConditions: [{ metric: "ESTIMATED_EARNINGS", order: "DESCENDING" }],
            localizationSettings: { currencyCode: "USD" }
          }
        })
      }
    );

    if (!reportRes.ok) {
      const text = await reportRes.text();
      return new Response(JSON.stringify({ error: "admob_api_error", detail: text }), {
        status: 502,
        headers: { "Content-Type": "application/json" }
      });
    }

    const rows = await reportRes.json();
    const apps = rows
      .filter((chunk) => chunk.row)
      .map((chunk) => {
        const dims = chunk.row.dimensionValues || {};
        const mets = chunk.row.metricValues || {};
        return {
          app: dims.APP?.displayLabel || dims.APP?.value || "알 수 없음",
          earnings: Number(mets.ESTIMATED_EARNINGS?.microsValue || 0) / 1_000_000,
          impressions: Number(mets.IMPRESSIONS?.integerValue || 0),
          clicks: Number(mets.CLICKS?.integerValue || 0),
          ctr: Number(mets.IMPRESSION_CTR?.doubleValue || 0)
        };
      });

    const totalEarnings = apps.reduce((sum, a) => sum + a.earnings, 0);

    return new Response(
      JSON.stringify({
        currency: "USD",
        totalEarnings,
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
