-- =====================================================
-- 004: MAJBURIY OBUNA KANALLARI
-- Supabase -> SQL Editor -> New query -> Run
-- =====================================================

create table if not exists public.channels (
    id        bigint generated always as identity primary key,

    -- '@KanalNomi' yoki '-1004423253818' — ikkalasi ham bo'ladi
    chat_id   text        not null,

    title     text,                  -- ko'rsatish uchun nom
    url       text,                  -- t.me havolasi (tugmaga qo'yiladi)
    added_at  timestamptz not null default now(),

    constraint channels_chat_id_key unique (chat_id)
);

alter table public.channels enable row level security;

-- Jadval bo'sh bo'lsa majburiy obuna O'CHIQ bo'ladi — hamma erkin foydalanadi.
--
-- Qo'lda qo'shish:
--   insert into public.channels (chat_id, title, url) values
--     ('@ACIYNPUBG_UC',   '1-kanal', 'https://t.me/ACIYNPUBG_UC'),
--     ('@KinochiOka2025', '2-kanal', 'https://t.me/KinochiOka2025')
--   on conflict (chat_id) do nothing;
--
-- ⚠️ Bot har bir kanalda ADMIN bo'lishi shart, aks holda obunani
-- tekshira olmaydi (bunday holatda foydalanuvchi bloklanmaydi).
