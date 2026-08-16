-- =====================================================
-- KINO BOT — SUPABASE SXEMASI
-- Supabase Dashboard -> SQL Editor -> New query -> Run
-- =====================================================

create table if not exists public.movies (
    id          bigint generated always as identity primary key,
    movie_code  text        not null,
    file_id     text        not null,
    title       text        not null,
    created_at  timestamptz not null default now(),

    -- Kod takrorlanmas bo'lishi kerak: bitta kod = bitta kino.
    -- Bot INSERT paytida 23505 (unique_violation) xatosini ushlab oladi.
    constraint movies_movie_code_key unique (movie_code),

    -- Bo'sh yoki probel kod/nom saqlanib qolmasin
    constraint movies_movie_code_not_blank check (length(btrim(movie_code)) > 0),
    constraint movies_title_not_blank      check (length(btrim(title)) > 0)
);

-- Foydalanuvchi kod yuborganda qidiruv shu indeks orqali ketadi.
-- (unique constraint allaqachon indeks yaratadi, shuning uchun alohida
--  movie_code indeksi kerak emas — bu esa "oxirgi qo'shilganlar" ro'yxati uchun.)
create index if not exists movies_created_at_idx
    on public.movies (created_at desc);


-- =====================================================
-- ROW LEVEL SECURITY
-- =====================================================
-- Bot serverda `service_role` kaliti bilan ishlaydi — u RLS ni chetlab o'tadi,
-- shuning uchun policy yozmasak ham bot ishlayveradi. RLS ni yoqib qo'yish
-- esa kalit sizib chiqqan (anon) holatda bazani himoyalaydi.

alter table public.movies enable row level security;

-- ⚠️ Faqat anon kalitidan foydalanmoqchi bo'lsangiz, quyidagi policy'ni oching:
-- (anon uchun faqat O'QISH ruxsati; yozish baribir service_role orqali bo'ladi)
--
-- create policy "movies_public_read"
--     on public.movies
--     for select
--     to anon
--     using (true);


-- =====================================================
-- TEKSHIRISH
-- =====================================================
-- insert into public.movies (movie_code, file_id, title)
-- values ('125', 'BAACAgIAAxkBAAI-test-file-id', '🎬 Test kino');
--
-- select * from public.movies where movie_code = '125';
