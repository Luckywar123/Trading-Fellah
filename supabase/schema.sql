-- ============================================================================
-- TRADING FELLAH — Supabase schema
-- Jalankan ini di Supabase SQL Editor (project baru, free tier OK).
-- Auth pakai wallet login (SIWE) custom, JADI kita TIDAK pakai supabase.auth.users
-- bawaan Supabase (itu email/OAuth based). Kita bikin tabel users sendiri,
-- keyed by wallet_address, dan backend yang keluarin JWT session sendiri.
-- ============================================================================

create extension if not exists "pgcrypto";

-- ----------------------------------------------------------------------------
-- USERS  (identitas = wallet address, bukan email/password)
-- ----------------------------------------------------------------------------
create table if not exists public.users (
    id                uuid primary key default gen_random_uuid(),
    wallet_address    text unique not null,          -- lowercase 0x...
    display_name      text,
    created_at        timestamptz not null default now(),
    last_login_at     timestamptz,
    is_admin          boolean not null default false
);

-- nonce sekali-pakai buat SIWE (Sign-In With Ethereum) challenge
create table if not exists public.auth_nonces (
    wallet_address    text primary key,
    nonce             text not null,
    expires_at        timestamptz not null
);

-- ----------------------------------------------------------------------------
-- SUBSCRIPTIONS  (membership bulanan, dibayar crypto via NOWPayments)
-- ----------------------------------------------------------------------------
create type subscription_status as enum ('inactive', 'pending', 'active', 'expired', 'cancelled');
create type plan_tier as enum ('basic', 'pro', 'elite');

create table if not exists public.subscriptions (
    id                uuid primary key default gen_random_uuid(),
    user_id           uuid not null references public.users(id) on delete cascade,
    plan              plan_tier not null default 'basic',
    status            subscription_status not null default 'inactive',
    current_period_end timestamptz,
    created_at        timestamptz not null default now(),
    updated_at        timestamptz not null default now()
);
create index if not exists idx_subscriptions_user on public.subscriptions(user_id);

create table if not exists public.payments (
    id                uuid primary key default gen_random_uuid(),
    user_id           uuid not null references public.users(id) on delete cascade,
    provider          text not null default 'nowpayments',
    provider_payment_id text unique,
    plan              plan_tier not null,
    amount_usd        numeric(12,2) not null,
    pay_currency      text,                            -- e.g. USDTTRC20, BTC, ETH
    status             text not null default 'waiting', -- waiting/confirming/finished/failed/expired
    raw_payload        jsonb,
    created_at         timestamptz not null default now()
);
create index if not exists idx_payments_user on public.payments(user_id);

-- ----------------------------------------------------------------------------
-- MT5 ACCOUNTS  (kredensial terenkripsi, 1 user bisa punya >1 akun broker)
-- ----------------------------------------------------------------------------
create table if not exists public.mt5_accounts (
    id                uuid primary key default gen_random_uuid(),
    user_id           uuid not null references public.users(id) on delete cascade,
    label             text not null default 'Main Account',
    broker_server     text not null,        -- contoh: "VantageInternational-Live 3"
    mt5_login         text not null,        -- nomor akun MT5 (bukan rahasia, tapi disimpan apa adanya)
    encrypted_password text not null,       -- password MT5, dienkripsi Fernet di backend
    metaapi_account_id text,                -- id account setelah diprovision ke MetaApi
    connection_status  text not null default 'disconnected', -- disconnected/connecting/connected/error
    is_live            boolean not null default false, -- live vs demo
    created_at         timestamptz not null default now(),
    updated_at         timestamptz not null default now()
);
create index if not exists idx_mt5_accounts_user on public.mt5_accounts(user_id);

-- ----------------------------------------------------------------------------
-- RISK SETTINGS  (toggle agresivitas per akun — ini yang user pilih sendiri)
-- ----------------------------------------------------------------------------
create type risk_preset as enum ('conservative', 'balanced', 'aggressive', 'full_send', 'custom');

create table if not exists public.risk_settings (
    id                    uuid primary key default gen_random_uuid(),
    mt5_account_id        uuid not null references public.mt5_accounts(id) on delete cascade unique,
    preset                risk_preset not null default 'balanced',
    max_margin_pct_per_trade numeric(5,2) not null default 20.00, -- % dari free margin dipakai per order
    max_risk_pct_per_trade   numeric(5,2) not null default 2.00,  -- % equity di-risk-kan (jarak ke SL)
    max_open_positions       int not null default 5,
    max_daily_trades         int not null default 25,
    sl_atr_multiplier         numeric(5,2) not null default 1.2,
    trailing_enabled          boolean not null default true,
    trailing_trigger_pips     int not null default 50,
    trail_distance_pips       int not null default 10,
    breakeven_trigger_pips    int not null default 15,
    news_blackout_enabled     boolean not null default true,   -- "net" auto-pause saat news high impact
    news_blackout_minutes     int not null default 15,
    full_margin_mode          boolean not null default false,  -- kalau true & swing tervalidasi -> pakai max_margin_pct_per_trade penuh
    ai_confidence_threshold   numeric(4,2) not null default 0.70,
    live_autotrade_enabled    boolean not null default false,  -- MASTER SWITCH — harus eksplisit dinyalain user, default OFF
    last_emergency_stop_at    timestamptz,
    updated_at                timestamptz not null default now()
);

-- ----------------------------------------------------------------------------
-- TRADES  (histori posisi, sinkron dari MT5 + order manual + order dari AI)
-- ----------------------------------------------------------------------------
create table if not exists public.trades (
    id                 uuid primary key default gen_random_uuid(),
    mt5_account_id     uuid not null references public.mt5_accounts(id) on delete cascade,
    mt5_ticket         bigint,               -- ticket id asli dari MT5, null kalau masih paper/forward test
    symbol             text not null,
    direction          text not null,        -- LONG/SHORT
    volume_lots        numeric(10,4) not null,
    entry_price        numeric(18,6) not null,
    stop_loss          numeric(18,6),
    take_profit        numeric(18,6),
    exit_price         numeric(18,6),
    pnl_usd            numeric(14,2),
    source             text not null default 'manual', -- manual / ai_swing / ai_orderblock / backtest / forward_test
    confidence_score   numeric(4,2),
    reason_open        text,
    reason_close       text,
    is_forward_test    boolean not null default false,
    opened_at          timestamptz not null default now(),
    closed_at          timestamptz
);
create index if not exists idx_trades_account on public.trades(mt5_account_id);
create index if not exists idx_trades_opened on public.trades(opened_at desc);

-- ----------------------------------------------------------------------------
-- LIVE AUTOTRADE CONFIGS  (opt-in per akun+simbol untuk eksekusi ASLI.
-- Dua lapis gate: risk_settings.live_autotrade_enabled (master switch per akun)
-- HARUS true, DAN row di sini enabled=true, baru scheduler bakal eksekusi
-- order asli buat kombinasi akun+simbol itu.)
-- ----------------------------------------------------------------------------
create table if not exists public.live_autotrade_configs (
    id              uuid primary key default gen_random_uuid(),
    mt5_account_id  uuid not null references public.mt5_accounts(id) on delete cascade,
    symbol          text not null,
    timeframe       text not null default '15m',
    enabled         boolean not null default true,
    created_at      timestamptz not null default now(),
    unique (mt5_account_id, symbol, timeframe)
);

-- ----------------------------------------------------------------------------
-- FORWARD TEST CONFIGS  (on/off per akun+simbol, dipoll APScheduler di backend)
-- ----------------------------------------------------------------------------
create table if not exists public.forward_test_configs (
    id              uuid primary key default gen_random_uuid(),
    mt5_account_id  uuid not null references public.mt5_accounts(id) on delete cascade,
    symbol          text not null,
    timeframe       text not null default '15m',
    enabled         boolean not null default true,
    created_at      timestamptz not null default now(),
    unique (mt5_account_id, symbol, timeframe)
);

-- ----------------------------------------------------------------------------
-- BACKTEST RUNS
-- ----------------------------------------------------------------------------
create table if not exists public.backtest_runs (
    id              uuid primary key default gen_random_uuid(),
    user_id         uuid not null references public.users(id) on delete cascade,
    symbol          text not null,
    timeframe       text not null,
    date_from       date not null,
    date_to         date not null,
    risk_preset     risk_preset not null default 'balanced',
    params          jsonb,
    result_summary  jsonb,        -- {win_rate, total_trades, net_pnl, max_dd, sharpe, ...}
    equity_curve    jsonb,        -- array of {t, equity}
    status          text not null default 'queued', -- queued/running/done/failed
    created_at      timestamptz not null default now()
);
create index if not exists idx_backtest_user on public.backtest_runs(user_id);

-- ----------------------------------------------------------------------------
-- AI NEWS EVENTS  (hasil analisa sentiment berita dari AI agent)
-- ----------------------------------------------------------------------------
create table if not exists public.ai_news_events (
    id              uuid primary key default gen_random_uuid(),
    headline        text not null,
    source          text,
    currency_impact text[],          -- ["USD","EUR"]
    impact_level    text,            -- low/medium/high
    sentiment       text,            -- buy/sell/neutral
    sentiment_score numeric(4,2),    -- -1..1
    ai_summary      text,
    event_time      timestamptz,
    created_at      timestamptz not null default now()
);
create index if not exists idx_news_time on public.ai_news_events(event_time desc);

-- ----------------------------------------------------------------------------
-- AI KNOWLEDGE BASE  (materi financial yang "disuapin" ke AI agent — dipakai
-- sebagai konteks tambahan pas AI bikin analisa/expectation. Simple keyword
-- retrieval dulu; kalau volume materi udah banyak, upgrade ke pgvector
-- (Supabase support native) buat semantic search.)
-- ----------------------------------------------------------------------------
create table if not exists public.ai_knowledge_base (
    id              uuid primary key default gen_random_uuid(),
    title           text not null,
    content         text not null,
    tags            text[] default '{}',
    added_by        uuid references public.users(id),
    created_at      timestamptz not null default now()
);

-- ----------------------------------------------------------------------------
-- AI BEHAVIOR PROFILE  (analisa kebiasaan trading tiap user dari histori trade)
-- ----------------------------------------------------------------------------
create table if not exists public.ai_behavior_profiles (
    id                  uuid primary key default gen_random_uuid(),
    user_id             uuid not null references public.users(id) on delete cascade,
    generated_at        timestamptz not null default now(),
    trades_analyzed     int not null default 0,
    summary             text,             -- narasi AI ttg pola trading user
    tendencies          jsonb,            -- {overtrading_score, revenge_trading_flag, best_session, best_symbol, avg_hold_time_min, discipline_score, ...}
    recommendations     text
);
create index if not exists idx_behavior_user on public.ai_behavior_profiles(user_id);

-- ----------------------------------------------------------------------------
-- SWING / ORDER BLOCK SIGNALS  (log sinyal yang dideteksi AI, buat audit + backtest)
-- ----------------------------------------------------------------------------
create table if not exists public.ai_signals (
    id              uuid primary key default gen_random_uuid(),
    symbol          text not null,
    timeframe       text not null,
    signal_type     text not null,   -- swing_breakout / order_block / support_resistance
    direction       text not null,   -- LONG/SHORT
    trigger_price   numeric(18,6) not null,
    zone_low        numeric(18,6),
    zone_high       numeric(18,6),
    confidence      numeric(4,2) not null,
    validated       boolean not null default false,
    acted_on        boolean not null default false,
    created_at      timestamptz not null default now()
);
create index if not exists idx_signals_symbol on public.ai_signals(symbol, created_at desc);

-- ============================================================================
-- Row Level Security — backend pakai service_role key (bypass RLS), tapi
-- kita nyalain RLS + policy ketat buat jaga-jaga kalau ada akses langsung
-- pakai anon/public key dari frontend.
-- ============================================================================
alter table public.users enable row level security;
alter table public.mt5_accounts enable row level security;
alter table public.risk_settings enable row level security;
alter table public.trades enable row level security;
alter table public.backtest_runs enable row level security;
alter table public.subscriptions enable row level security;
alter table public.payments enable row level security;
alter table public.ai_behavior_profiles enable row level security;
alter table public.live_autotrade_configs enable row level security;
alter table public.forward_test_configs enable row level security;
alter table public.ai_knowledge_base enable row level security;

-- Default: tolak semua akses langsung dari anon key. Semua request HARUS lewat
-- backend (yang pakai service_role key dan validasi JWT sendiri).
-- Kalau nanti mau akses langsung dari frontend pakai supabase-js + JWT custom,
-- tinggal tambah policy pakai auth.jwt() claims di sini.
