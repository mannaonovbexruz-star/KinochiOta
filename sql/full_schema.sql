-- =====================================================
-- KINO BOT — TO'LIQ SXEMA (movies + admins)
-- Supabase Dashboard -> SQL Editor -> New query -> paste -> Run
--
-- Qayta ishga tushirish XAVFSIZ: hamma narsa `if not exists` bilan,
-- mavjud ma'lumotlar o'chmaydi va o'zgarmaydi.
-- =====================================================


-- =====================================================
-- 1. KINOLAR
-- =====================================================

create table if not exists public.movies (
    id          bigint generated always as identity primary key,
    movie_code  text        not null,
    file_id     text        not null,
    title       text        not null,
    created_at  timestamptz not null default now(),

    -- Bitta kod = bitta kino (bot 23505 xatosini ushlab oladi)
    constraint movies_movie_code_key unique (movie_code),

    -- Bo'sh yoki faqat probeldan iborat qiymat saqlanmasin
    constraint movies_movie_code_not_blank check (length(btrim(movie_code)) > 0),
    constraint movies_title_not_blank      check (length(btrim(title)) > 0)
);

-- "Oxirgi qo'shilganlar" ro'yxati uchun
create index if not exists movies_created_at_idx
    on public.movies (created_at desc);

alter table public.movies enable row level security;


-- =====================================================
-- 2. ADMINLAR
-- =====================================================
-- ⚠️ EGASI bu jadvalda saqlanmaydi — u ADMIN_ID env o'zgaruvchisida.
-- Shuning uchun bazaga kirgan odam ham egani o'chira olmaydi.

create table if not exists public.admins (
    id        bigint generated always as identity primary key,
    user_id   bigint      not null,
    username  text,
    added_at  timestamptz not null default now(),

    -- Bitta odam ikki marta qo'shilmasin
    constraint admins_user_id_key unique (user_id)
);

alter table public.admins enable row level security;


-- =====================================================
-- 3. TEKSHIRISH (natijani jadval ko'rinishida chiqaradi)
-- =====================================================

select
    c.table_name,
    c.column_name,
    c.data_type
from information_schema.columns c
where c.table_schema = 'public'
  and c.table_name in ('movies', 'admins')
order by c.table_name, c.ordinal_position;
