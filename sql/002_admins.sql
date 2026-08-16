-- =====================================================
-- 002: ADMINLAR JADVALI
-- Supabase Dashboard -> SQL Editor -> New query -> Run
-- (movies jadvaliga tegilmaydi)
-- =====================================================

create table if not exists public.admins (
    id        bigint generated always as identity primary key,
    user_id   bigint      not null,
    username  text,
    added_at  timestamptz not null default now(),

    -- Bitta odam ikki marta qo'shilmasin
    constraint admins_user_id_key unique (user_id)
);

alter table public.admins enable row level security;

-- ⚠️ EGASI bu jadvalda saqlanmaydi — u ADMIN_ID environment o'zgaruvchisida.
-- Shuning uchun bazadan hech kim egani o'chira olmaydi.
--
-- Adminni qo'lda qo'shish (kerak bo'lsa):
--   insert into public.admins (user_id, username) values (5551234567, 'nomi');
--
-- Adminlarni ko'rish:
--   select user_id, username, added_at from public.admins order by added_at desc;
