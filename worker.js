// Static-asset ignore files (.assetsignore / .gitignore) aren't reliably
// honored by every deploy target (Pages in particular ignores both), so
// sensitive/internal paths are denied here in code instead — this is the
// one place both the Workers and Pages (_worker.js) deployments share.
const DENIED_PATH_PATTERN = /^\/(\.|admob\/|wrangler(\.pages)?\.toml$|_?worker\.js$)/;

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (DENIED_PATH_PATTERN.test(url.pathname)) {
      return new Response("Not found", { status: 404 });
    }

    // AdMob 을 직접 부르는 응답은 몇 분간 엣지 캐시에 두어, 반복 호출이 AdMob 호출 한도를 소진하지 못하게 한다.
    if (url.pathname === "/api/admob-revenue") {
      return cachedResponse(request, ctx, 120, () => handleAdmobRevenue(env));
    }

    if (url.pathname === "/api/admob-history") {
      return cachedResponse(request, ctx, 120, () => handleAdmobHistory(env));
    }

    if (url.pathname === "/api/play-stats") {
      const raw = await env.SUGGESTIONS.get("play-stats");
      return new Response(raw || JSON.stringify({ updated: null, apps: [] }), {
        headers: { "Content-Type": "application/json", "Cache-Control": "public, max-age=300" }
      });
    }

    if (url.pathname === "/api/autoreply/redeem" && request.method === "POST") {
      return handleAutoreplyRedeem(request, env);
    }
    if (url.pathname === "/api/autoreply/unlock" && request.method === "GET") {
      return handleAutoreplyUnlock(url, request, env, ctx);
    }
    if (url.pathname === "/api/autoreply/log" && request.method === "POST") {
      return handleAutoreplyLog(request, env, ctx);
    }

    if (url.pathname === "/api/suggestions") {
      if (request.method === "POST") return handlePostSuggestion(request, env);
      if (request.method === "GET") return handleGetSuggestions(env);
      return new Response("Method Not Allowed", { status: 405 });
    }

    return env.ASSETS.fetch(request);
  },

  // 매일 아침(cron): AdMob 일별 수익을 KV 에 쌓고 텔레그램으로 어제 요약·이상 징후를 보낸다.
  async scheduled(event, env, ctx) {
    // 매시 정각: 최근 3일치만 갱신해 KV 에 저장. 09:30 KST(00:30 UTC)에만 텔레그램 요약까지 보낸다.
    if (event.cron === "30 0 * * *") ctx.waitUntil(runDailyDigest(env));
    else ctx.waitUntil(collectHistory(env, 7).catch(() => {}));
  }
};


// ───────── 공통 보호 장치: 엣지 캐시 · 속도 제한 · 토큰 비교 ─────────
// 캐시 키는 쿼리스트링을 버려서 ?x=1 같은 우회로 캐시를 피하지 못하게 한다. 실패도 60초 캐시해 AdMob 재호출을 막는다.
async function cachedResponse(request, ctx, ttlSeconds, producer) {
  const cache = caches.default;
  const u = new URL(request.url);
  const key = new Request(`${u.origin}${u.pathname}`, { method: "GET" });
  const hit = await cache.match(key);
  if (hit) return hit;
  const res = await producer();
  const out = new Response(res.body, res);
  out.headers.set("Cache-Control", `public, max-age=${res.ok ? ttlSeconds : 60}`);
  ctx.waitUntil(cache.put(key, out.clone()));
  return out;
}

// 간이 속도 제한(엣지 캐시 카운터, 데이터센터별·근사치). 한도를 넘으면 true.
async function rateLimited(ctx, bucket, limit, windowSeconds) {
  const cache = caches.default;
  const key = new Request(`https://ratelimit.internal/${encodeURIComponent(bucket)}`);
  const now = Date.now();
  const hit = await cache.match(key);
  let st = hit ? await hit.json().catch(() => null) : null;
  if (!st || st.exp <= now) st = { n: 0, exp: now + windowSeconds * 1000 };
  if (st.n >= limit) return true;
  st.n += 1;
  const ttl = Math.max(1, Math.ceil((st.exp - now) / 1000));
  ctx.waitUntil(cache.put(key, new Response(JSON.stringify(st), { headers: { "Cache-Control": `max-age=${ttl}` } })));
  return false;
}

// 자동답장 앱 토큰 확인. 시크릿(AR_TOKEN)이 없으면 모두 거부한다(코드에 값을 두지 않는다).
function arAuthorized(request, env) {
  const given = request.headers.get("x-ar-token") || "";
  const want = env.AR_TOKEN || "";
  if (!want || given.length !== want.length) return false;
  let diff = 0;
  for (let i = 0; i < want.length; i++) diff |= given.charCodeAt(i) ^ want.charCodeAt(i);
  return diff === 0;
}

// ───────── 수익 히스토리(KV "admob-history") · 텔레그램 요약 ─────────
const HISTORY_KEY = "admob-history";
const HISTORY_KEEP_DAYS = 400;

// 워커 로컬 시간은 UTC 이므로, UTC 필드가 한국 날짜가 되도록 9시간을 더한 Date 를 쓴다.
function kstNow() {
  return new Date(Date.now() + 9 * 3600 * 1000);
}
function kstDaysAgo(n) {
  const d = kstNow();
  d.setUTCDate(d.getUTCDate() - n);
  return d;
}
function ymd(d) {
  return `${d.getUTCFullYear()}${String(d.getUTCMonth() + 1).padStart(2, "0")}${String(d.getUTCDate()).padStart(2, "0")}`;
}
function utcParts(d) {
  return { year: d.getUTCFullYear(), month: d.getUTCMonth() + 1, day: d.getUTCDate() };
}

async function fetchDailyRows(env, start, end) {
  const accessToken = await getAccessToken(env);
  const res = await fetch(
    `https://admob.googleapis.com/v1/accounts/${env.ADMOB_PUBLISHER_ID}/networkReport:generate`,
    {
      method: "POST",
      headers: { Authorization: `Bearer ${accessToken}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        reportSpec: {
          dateRange: { startDate: utcParts(start), endDate: utcParts(end) },
          metrics: ["ESTIMATED_EARNINGS", "IMPRESSIONS", "CLICKS"],
          dimensions: ["DATE", "APP"],
          localizationSettings: { currencyCode: "KRW" }
        }
      })
    }
  );
  if (!res.ok) throw new Error(`admob_api_error: ${await res.text()}`);
  return (await res.json())
    .filter((chunk) => chunk.row)
    .map((chunk) => {
      const d = chunk.row.dimensionValues || {};
      const m = chunk.row.metricValues || {};
      return {
        date: d.DATE?.value,
        app: d.APP?.displayLabel || d.APP?.value || "알 수 없음",
        krw: Number(m.ESTIMATED_EARNINGS?.microsValue || 0) / 1_000_000,
        impressions: Number(m.IMPRESSIONS?.integerValue || 0),
        clicks: Number(m.CLICKS?.integerValue || 0)
      };
    });
}

// AdMob 앱 표시 이름이 때때로 길게(스토어 제목) 바뀌어 돌아온다 → 기존 기록의 짧은 이름이 앞부분과 같으면 그 이름으로 통일.
function canonApps(fresh, known) {
  const names = [...new Set(known.map((r) => r.app))].sort((a, b) => b.length - a.length);
  const key = (x) => x.toLowerCase().replace(/[\s\-_:]/g, "");
  const ALIAS = [["오토플레이", "음악자동재생"]]; // 스토어 이름이 바뀐 앱: 새 표시 이름 → 기록에 있는 옛 이름
  return fresh.map((r) => {
    const k = key(r.app);
    const al = ALIAS.find(([n]) => k.startsWith(key(n)));
    if (al && names.includes(al[1])) return { ...r, app: al[1] };
    const hit = names.find((n) => key(n) === k || (key(n).length >= 4 && k.startsWith(key(n))));
    return hit ? { ...r, app: hit } : r;
  });
}

async function loadHistory(env) {
  const raw = await env.SUGGESTIONS.get(HISTORY_KEY);
  if (!raw) return { updated: null, rows: [] };
  try {
    return JSON.parse(raw);
  } catch {
    return { updated: null, rows: [] };
  }
}

// 새로 읽은 구간을 기존 기록에 덮어쓴다(같은 날짜·앱은 최신 값으로 교체 — AdMob 은 며칠간 수치를 보정한다).
async function collectHistory(env, days) {
  const hist = await loadHistory(env);
  const fresh = canonApps(await fetchDailyRows(env, kstDaysAgo(days - 1), kstNow()), hist.rows);
  const map = new Map(hist.rows.map((r) => [`${r.date}|${r.app}`, r]));
  const from = ymd(kstDaysAgo(days - 1));
  for (const key of [...map.keys()]) if (key.split("|")[0] >= from) map.delete(key);
  for (const r of fresh) map.set(`${r.date}|${r.app}`, r);
  const cutoff = ymd(kstDaysAgo(HISTORY_KEEP_DAYS));
  const rows = [...map.values()].filter((r) => r.date >= cutoff).sort((a, b) => (a.date < b.date ? -1 : 1));
  const out = { updated: new Date().toISOString(), rows };
  await env.SUGGESTIONS.put(HISTORY_KEY, JSON.stringify(out));
  return out;
}

async function handleAdmobHistory(env) {
  try {
    let hist = await loadHistory(env);
    // 처음 한 번은 90일치를 채운다(이후엔 매시 cron 이 저장).
    if (!hist.rows.length) hist = await collectHistory(env, 90);
    // 열 때마다 최근 3일을 AdMob 에서 바로 받아 덮어쓴다(저장은 안 함). 실패하면 저장본 그대로.
    let updated = hist.updated, rows = hist.rows;
    try {
      const fresh = canonApps(await fetchDailyRows(env, kstDaysAgo(2), kstNow()), rows);
      const from = ymd(kstDaysAgo(2));
      rows = rows.filter((r) => r.date < from).concat(fresh).sort((a, b) => (a.date < b.date ? -1 : 1));
      updated = new Date().toISOString();
    } catch {}
    return new Response(JSON.stringify({ currency: "KRW", updated, rows }), {
      headers: { "Content-Type": "application/json", "Cache-Control": "public, max-age=120" }
    });
  } catch (err) {
    return new Response(JSON.stringify({ error: "internal_error" }), {
      status: 500,
      headers: { "Content-Type": "application/json" }
    });
  }
}

const wonFmt = (n) => "₩" + Math.round(n).toLocaleString("ko-KR");

// 어제 수익·비교·월 누적과 이상 징후로 텔레그램 문구를 만든다. 순수 함수(테스트하기 쉽게 분리).
// orders·ordersUpdated 는 KV "play-stats" 의 Play Console 주문(수수료 전 결제 금액, 날짜는 KST).
function buildDigest(rows, today, orders = [], ordersUpdated = null) {
  const yKey = ymd(new Date(Date.UTC(today.y, today.m - 1, today.d - 1)));
  const sumBy = (pred) => rows.filter(pred).reduce((s, r) => s + r.krw, 0);
  const dayKey = (n) => ymd(new Date(Date.UTC(today.y, today.m - 1, today.d - n)));
  const yesterday = sumBy((r) => r.date === yKey);
  const prev7keys = new Set([2, 3, 4, 5, 6, 7, 8].map(dayKey));
  const prev7avg = sumBy((r) => prev7keys.has(r.date)) / 7;
  const lastWeekSame = sumBy((r) => r.date === dayKey(8));

  const monthPrefix = `${today.y}${String(today.m).padStart(2, "0")}`;
  const elapsed = today.d - 1;
  const monthSum = sumBy((r) => r.date.startsWith(monthPrefix) && r.date < ymd(new Date(Date.UTC(today.y, today.m - 1, today.d))));
  const dim = new Date(Date.UTC(today.y, today.m, 0)).getUTCDate();
  const projection = elapsed > 0 ? (monthSum / elapsed) * dim : null;

  const paid = orders.filter((o) => o.status === "처리됨" && o.currency === "KRW");
  const iapSum = (pred) => paid.filter(pred).reduce((s, o) => s + o.amount, 0);
  const iapY = iapSum((o) => o.date === yKey);
  const iapMonth = iapSum((o) => o.date.startsWith(monthPrefix) && o.date <= yKey);

  const warnings = [];
  // 주문 수집은 맥에서 돈다. 오늘(KST) 한 번도 못 돌았으면 어제 결제가 빠졌을 수 있다.
  const todayIso = `${today.y}-${String(today.m).padStart(2, "0")}-${String(today.d).padStart(2, "0")}`;
  if (!ordersUpdated || ordersUpdated.slice(0, 10) < todayIso) {
    const last = ordersUpdated ? ordersUpdated.replace("T", " ").slice(0, 16) : "기록 없음";
    warnings.push(`인앱 결제는 마지막 수집(${last}) 기준이라 빠진 주문이 있을 수 있습니다.`);
  }
  const hasY = rows.some((r) => r.date === yKey);
  if (!hasY) warnings.push("어제 AdMob 집계가 아직 없습니다(반영 지연일 수 있음).");
  if (hasY && prev7avg >= 100 && yesterday < prev7avg * 0.5) {
    warnings.push(`어제 광고 수익이 직전 7일 평균(${wonFmt(prev7avg)})의 절반 아래입니다.`);
  }
  const appsRecent = new Map();
  for (const r of rows) if (prev7keys.has(r.date)) appsRecent.set(r.app, (appsRecent.get(r.app) || 0) + r.impressions);
  for (const [app, imps] of appsRecent) {
    const yImps = rows.filter((r) => r.date === yKey && r.app === app).reduce((s, r) => s + r.impressions, 0);
    if (hasY && imps > 0 && yImps === 0) warnings.push(`${app}: 어제 광고 노출이 0건입니다(직전 7일 ${imps.toLocaleString("ko-KR")}회).`);
  }

  const pct = (a, b) => (b > 0 ? `${a >= b ? "▲" : "▼"} ${Math.abs(((a - b) / b) * 100).toFixed(0)}%` : "비교값 없음");
  const head = warnings.length ? "⚠️ 확인할 점이 있습니다" : "✅ 이상 없음";
  const lines = [
    `📊 원픽셀 수익 요약 · ${yKey.slice(4, 6)}/${yKey.slice(6, 8)}`,
    head,
    "",
    "어제",
    `· 총수익 ${wonFmt(yesterday + iapY)}`,
    `· 광고 ${wonFmt(yesterday)} · 인앱 ${wonFmt(iapY)}`,
    `· 광고, 직전 7일 평균 대비 ${pct(yesterday, prev7avg)}`,
    `· 광고, 지난주 같은 요일 대비 ${pct(yesterday, lastWeekSame)}`,
    "",
    "이번 달",
    `· 누적 ${wonFmt(monthSum + iapMonth)}`,
    `· 광고 ${wonFmt(monthSum)} · 인앱 ${wonFmt(iapMonth)}`,
    // 인앱 결제는 드물게 생겨 늘려 잡지 않고, 광고 예상에 이번 달 실제 결제만 더한다.
    projection == null ? "· 월말 예상은 내일부터" : `· 월말 예상 ${wonFmt(projection + iapMonth)}`
  ];
  if (warnings.length) lines.push("", "확인할 점", ...warnings.map((w) => `· ${w}`));
  lines.push("", "인앱 결제는 수수료를 빼기 전 금액입니다.");
  lines.push("", "상세: https://onepixel.yhchad.com/dashboard/");
  return { text: lines.join("\n"), warnings };
}

async function sendTelegram(env, text) {
  if (!env.TELEGRAM_BOT_TOKEN || !env.TELEGRAM_CHAT_ID) return { skipped: true };
  const res = await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: env.TELEGRAM_CHAT_ID, text, disable_web_page_preview: true })
  });
  return { ok: res.ok, status: res.status };
}

// 클리앙 글쓰기 권한(가입 30일·로그인 14회) 채우는 동안(2026-11-22~2026-12-22)만
// 아침 요약 끝에 로그인 리마인더를 덧붙인다. 로그인은 채드님이 직접 해야 하는 일이라
// 여기서는 알림만 보내고 아무 것도 대신 하지 않는다.
function clienReminderLine(kstDate) {
  const { y, m, d } = kstDate;
  const onOrBefore = y < 2026 || (y === 2026 && (m < 12 || (m === 12 && d <= 22)));
  if (!onOrBefore) return "";
  return "\n\n💬 오늘 클리앙(clien.net)에 한 번 로그인해주세요 — 글쓰기 권한(가입 30일·로그인 14회) 채우는 중이에요.";
}

async function runDailyDigest(env) {
  try {
    const hist = await collectHistory(env, 35);
    const n = kstNow();
    const kstDate = { y: n.getUTCFullYear(), m: n.getUTCMonth() + 1, d: n.getUTCDate() };
    // 주문을 못 읽어도 광고 요약은 보낸다(경고 문구가 붙는다).
    const play = (await env.SUGGESTIONS.get("play-stats", "json").catch(() => null)) || {};
    const { text: digestText } = buildDigest(hist.rows, kstDate, play.orders || [], play.ordersUpdated || null);
    const text = digestText + clienReminderLine(kstDate);
    const r = await sendTelegram(env, text);
    console.log("digest", JSON.stringify(r));
  } catch (err) {
    console.log("digest_failed", String(err).slice(0, 200));
    try {
      await sendTelegram(env, "⚠️ 원픽셀 수익 집계에 실패했습니다. AdMob 인증(refresh token) 만료일 수 있습니다.");
    } catch {}
  }
}

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

    const body = JSON.stringify({
      currency: "USD",
      totalEarnings,
      totalEarningsKrw,
      rangeDays: 30,
      apps
    });
    // 마지막 성공값을 KV 에 보관 — AdMob/토큰 일시 오류 때 대신 내준다.
    try { await env.SUGGESTIONS.put("admob-revenue-last", body); } catch {}
    return new Response(body, { headers: { "Content-Type": "application/json" } });
  } catch (err) {
    console.error("admob-revenue failed:", String(err).slice(0, 300));
    try {
      const last = await env.SUGGESTIONS.get("admob-revenue-last");
      if (last) return new Response(last, { headers: { "Content-Type": "application/json", "X-Stale": "1" } });
    } catch {}
    return new Response(JSON.stringify({ error: "internal_error" }), {
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

// ---- 자동답장 앱 사용 이력 수집 ----
// 번호·문구 등 개인정보는 받지 않는다. 설치 ID(무작위)·시각·이벤트 코드만 저장한다.
// KV 쓰기 한도를 아끼려고 설치 ID+날짜 별 하나의 키에 이벤트 목록을 이어 붙인다.
const AR_MAX_BODY = 8192;
const AR_MAX_EVENTS_PER_DAY = 400;
const AR_TTL_SECONDS = 60 * 60 * 24 * 90;

async function handleAutoreplyLog(request, env, ctx) {
  if (!arAuthorized(request, env)) {
    return new Response("Forbidden", { status: 403 });
  }
  const ip = request.headers.get("cf-connecting-ip") || "unknown";
  if (await rateLimited(ctx, `arlog-ip:${ip}`, 300, 3600)) {
    return new Response("Too many requests", { status: 429, headers: { "Retry-After": "3600" } });
  }
  const raw = await request.text();
  if (raw.length > AR_MAX_BODY) return new Response("Too large", { status: 413 });
  let body;
  try { body = JSON.parse(raw); } catch { return new Response("Bad request", { status: 400 }); }

  const installId = String(body.i || "").slice(0, 40);
  if (!/^[A-Za-z0-9-]{8,40}$/.test(installId)) return new Response("Bad request", { status: 400 });
  if (await rateLimited(ctx, `arlog-id:${installId}`, 60, 3600)) {
    return new Response("Too many requests", { status: 429, headers: { "Retry-After": "3600" } });
  }
  const events = (Array.isArray(body.e) ? body.e : []).slice(0, 100).map((ev) => ({
    t: Number(ev.t) || Date.now(),
    k: String(ev.k || "").slice(0, 40),
    c: String(ev.c || "").slice(0, 80)
  })).filter((ev) => ev.k);
  if (!events.length) return new Response(JSON.stringify({ ok: true, n: 0 }), { headers: { "Content-Type": "application/json" } });

  const day = new Date(Date.now() + 9 * 3600 * 1000).toISOString().slice(0, 10); // KST 날짜
  const key = `ar:${day}:${installId}`;
  const prev = await env.SUGGESTIONS.get(key, "json");
  const meta = {
    v: String(body.v || "").slice(0, 20),
    d: String(body.d || "").slice(0, 40),
    s: Number(body.s) || 0
  };
  const merged = { ...meta, events: [...((prev && prev.events) || []), ...events].slice(-AR_MAX_EVENTS_PER_DAY) };
  await env.SUGGESTIONS.put(key, JSON.stringify(merged), { expirationTtl: AR_TTL_SECONDS });
  return new Response(JSON.stringify({ ok: true, n: events.length }), { headers: { "Content-Type": "application/json" } });
}

// 무제한 승인 확인: 설치 ID 가 KV(arunlock:<id>)에 등록돼 있으면 무료 건수 제한을 풀어 준다.
// 등록은 운영자가 wrangler kv key put 으로만 한다(앱에서 스스로 풀 수 없다).
async function handleAutoreplyUnlock(url, request, env, ctx) {
  if (!arAuthorized(request, env)) {
    return new Response("Forbidden", { status: 403 });
  }
  const ip = request.headers.get("cf-connecting-ip") || "unknown";
  if (await rateLimited(ctx, `arunlock-ip:${ip}`, 300, 3600)) {
    return new Response("Too many requests", { status: 429, headers: { "Retry-After": "3600" } });
  }
  const id = String(url.searchParams.get("i") || "");
  if (!/^[A-Za-z0-9-]{8,40}$/.test(id)) return new Response("Bad request", { status: 400 });
  const rec = await env.SUGGESTIONS.get(`arunlock:${id}`, "json");
  const unlimited = !!(rec && rec.unlimited === true);
  return new Response(JSON.stringify({ ok: true, unlimited, checkedAt: Date.now() }), {
    headers: { "Content-Type": "application/json", "Cache-Control": "no-store" }
  });
}

// 해제 코드 입력: 운영자가 만든 코드(arcode:<코드>)를 입력하면 그 설치 ID 가 무제한으로 등록된다.
// 코드는 사용 횟수(maxUses)가 있고, 누가(이메일) 받은 코드인지 기록한다. 코드 오입력은 느리게 막는다.
async function handleAutoreplyRedeem(request, env) {
  if (!arAuthorized(request, env)) return new Response("Forbidden", { status: 403 });
  let body;
  try { body = JSON.parse(await request.text()); } catch { return new Response("Bad request", { status: 400 }); }
  const id = String(body.i || "");
  const code = String(body.code || "").trim().toUpperCase();
  if (!/^[A-Za-z0-9-]{8,40}$/.test(id) || !/^AR-[A-Z0-9]{4}-[A-Z0-9]{4}$/.test(code)) {
    return new Response(JSON.stringify({ ok: false, error: "invalid" }), { status: 400, headers: { "Content-Type": "application/json" } });
  }
  const ip = request.headers.get("cf-connecting-ip") || "unknown";
  const rlKey = `arrl:${ip}`;
  const tries = Number((await env.SUGGESTIONS.get(rlKey)) || 0);
  if (tries >= 10) return new Response(JSON.stringify({ ok: false, error: "too_many" }), { status: 429, headers: { "Content-Type": "application/json" } });
  await env.SUGGESTIONS.put(rlKey, String(tries + 1), { expirationTtl: 3600 });

  const rec = await env.SUGGESTIONS.get(`arcode:${code}`, "json");
  if (!rec) return new Response(JSON.stringify({ ok: false, error: "wrong_code" }), { status: 404, headers: { "Content-Type": "application/json" } });
  const used = Array.isArray(rec.used) ? rec.used : [];
  if (!used.includes(id)) {
    if (used.length >= (rec.maxUses || 1)) return new Response(JSON.stringify({ ok: false, error: "used_up" }), { status: 409, headers: { "Content-Type": "application/json" } });
    used.push(id);
    await env.SUGGESTIONS.put(`arcode:${code}`, JSON.stringify({ ...rec, used }));
    await env.SUGGESTIONS.put(`arunlock:${id}`, JSON.stringify({ unlimited: true, email: rec.email || "", code: code.slice(0, 7) + "…", at: Date.now() }));
  }
  return new Response(JSON.stringify({ ok: true, unlimited: true }), { headers: { "Content-Type": "application/json", "Cache-Control": "no-store" } });
}
