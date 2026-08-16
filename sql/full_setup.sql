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


-- =====================================================
-- 3. KINOLAR (39 ta, eski database.json dan)
-- =====================================================

insert into public.movies (movie_code, file_id, title)
values
    ('1', 'BAACAgIAAxkBAAIBUmpVUx7zL-VQ_Lio2tB267QUGtM1AAKltwACBDaoSi9Zl0jzJpu_PAQ', '🎬 Labirint — 1-qism'),
    ('2', 'BAACAgQAAxkBAAIBqWpVyDNZ1kvUm9o_Va9O6SHMG9bmAAJFIAACd1UoUbKfuBoL0WCTPQQ', '🎬 Backrooms'),
    ('3', 'BAACAgQAAxkBAAIBuGpVyhEAAUXUzyKj2j9Yx9w82wbPrwACjw0AApVHwVA4AAE_eD-1P5k9BA', '🎬 Bahubali — 1-qism'),
    ('4', 'BAACAgQAAxkBAAIBtmpVygn4CegeAShfN2lstMfC2Qq9AAKQDQAClUfBUKm-1JOXiIY6PQQ', '🎬 Bahubali — 2-qism'),
    ('9', 'BAACAgIAAxkBAAIVWmp7YtYCT3eODBqwbBEAARI4Hz8vDgACTakAAhZn2UuVC7QoOY30kT0E', '🎬  kondorning mushti'),
    ('11', 'BAACAgIAAxkBAAIU-Gp7Lku6ICsSAkfveLlS_g5_iAMWAAJgpgACFmfZSwAB17xnUOWUQT0E', '🎬  Ekzorsist (2023)'),
    ('12', 'BAACAgQAAxkBAAIVAmp7NyppnArC4-9eFHFC2wbG2SSPAAL_HQACW-eRUwVBJeIPdGP-PQQ', '🎬  Lilo & Stitch'),
    ('14', 'BAACAgQAAxkBAAICYGpXXEojTSzxsO31hHk9aIss4_txAAJRDgACq84gUl6paaO75CpVPQQ', '🎬 O''rgimchak Odam: Uyga Yo''l Yo''q'),
    ('20', 'BAACAgIAAxkBAAIVqWp8QLuUFx_eNkGmO0-JmJX8BdSEAALRnAACk9XhS1YNmN2uykjYPQQ', '🎬  Oxiri zamon loyihasi (2026)'),
    ('22', 'BAACAgIAAxkBAAICAmpXKJ0H6pIoS9GXqX68ioUaKLwIAAKtAQACbwqpS8OwyiCunj4WPQQ', '🎬 Kapitan Amerika — 1-qism'),
    ('23', 'BAACAgIAAxkBAAICBWpXKRW4qIrfNKARkkcPGlG3sBfEAAK1AQACfb4AAUjmrYYg8rfTtj0E', '🎬 Kapitan Amerika — 2-qism'),
    ('28', 'BAACAgIAAxkBAAIS8mpy8WtohBLzn09b_Du_IPpHgxf7AAKAlgACBs6YS__Ghew_joqCPQQ', '🎬 Qudratli Renjerlar (2017)'),
    ('30', 'BAACAgQAAxkBAAIU1mp7FJcHfU2JYxbtX-GFkNhB6z4sAAIzDgACsVpBUwv0HE1YODM0PQQ', '🎬  Ekzorsist (2023)'),
    ('34', 'BAACAgQAAxkBAAIBumpVyyoLZ56AYSlLgs9IwhbRUcCjAAJ4IAACAobQUW_fEWmM2ePpPQQ', '🎬 Uch Bahodir: Oxir Zamon'),
    ('35', 'BAACAgQAAxkBAAIBvGpVy6zHXh4YOm5oX7Ond4hypBzxAAIVJQAClGrAUR_QdrlxEL0_PQQ', '🎬 Uch Bahodir'),
    ('36', 'BAACAgQAAxkBAAIC4GpaPz4N1pSPZwwMruwvl4d4c2wJAAIQHwACMDdgUYeb1n85ZvECPQQ', '🎬 Zootopiya 2'),
    ('37', 'BAACAgEAAxkBAAIC4mpaP7m-VzI4xMYPpm_BhQf0BR2PAALdAAMklPhF3C8f5R_sv5U9BA', '🎬 Maxluqlar Universiteti'),
    ('38', 'BAACAgQAAxkBAAIC4WpaP1GZqf93rHd2j0E08eg18Rg-AAKkDQACUAABoFAlAd3lZ7j_xT0E', '🎬 Etik kiygan mushuk 2'),
    ('49', 'BAACAgIAAxkBAAIF-2pgeW_3DyWoLGauVEFKzF5klGSPAAKapAAC_kcAAUsixErXxsjfnj0E', '🎬 Lara Kroft'),
    ('53', 'BAACAgQAAxkBAAIF4mpgdVK8s6OOxWzqLeCDr5_HYOLNAALACQACZNCgU5UvWje2x1QXPQQ', '🎬 ko''rinmas ajal'),
    ('55', 'BAACAgIAAxkBAAIET2pfpKfEVroGqmxvmPsqfk2bX1hVAAJtpwACRJIAAUvRdSFCXML26D0E', '🎬 Z world urushi'),
    ('60', 'BAACAgIAAxkBAAIGxmphCfDwYMXLnoVlgzI8F0l0Z1StAALnsQAC_kcIS70YGTOBnU_APQQ', '🎬 Hayot Lazzati'),
    ('61', 'BAACAgIAAxkBAAIGy2phGNCyRnW369OFGJ2ZomwvazsYAAJ9sgAC_kcIS_yoIBfb-YtNPQQ', '🎬 Afsona'),
    ('62', 'BAACAgUAAxkBAAIHFWpiHgI3idXFAAGBRMqAeWPxAAFzLfMAAtIDAAIe4YBVU9PURa6cZsY9BA', '🎬 Robot 1'),
    ('63', 'BAACAgQAAyEFAAMBBL8vGAADB2pmSMlNfDNSh4mn8tA6aNc63aJTAAJ0IAACAobQUe8LJ_PgqMTGPQQ', '🎬 Qalbing chilparchin bo''ladi (2026)'),
    ('64', 'BAACAgQAAxkBAAIIqWpp45RFn2oKtKM1afVNfNjZBMZxAAJHJAAC4XQ4UclgiKEBRmZCPQQ', '🎬 Vaqt oralig''ida'),
    ('65', 'BAACAgEAAxkBAAIItGpp57MaCBSC_aAYZckKY0M6sBkbAALABAAChWxYRP7F-Ak_iEPBPQQ', '🎬 Qiruvchi'),
    ('70', 'BAACAgEAAxkBAAILpWptd8oXhk2pUCJFpGcJcKhqZETUAAIEBwACyqZoR-bQMDP66w0DPQQ', '🎬 Orgimchak Odam'),
    ('71', 'BAACAgUAAxkBAAIO9WpvV6itK_ofKT7RRyw3uLOJCCc-AAJMFQACJXSwVPhBF7UY1PumPQQ', '🎬 Qora libosdagi odamlar'),
    ('72', 'BAACAgQAAxkBAAIPn2pw7zuNhhAwQGiGNOvHbkyuXbuIAAKUFwAC0JuQUeLidz_mrkDlPQQ', '🎬 Ajoyib yechim'),
    ('73', 'BAACAgIAAxkBAAIQ0WpyMEdHTaktzkEgxk2qOGgKais0AAKSsAACsAKQSyN-j-gZuJkSPQQ', '🎬 Eltuvchi2'),
    ('74', 'BAACAgUAAxkBAAIQ3mpyPgPSR380n3LVLChKLRwY4xGAAAIKFAAClNnBVEk6ktj7yCOxPQQ', '🎬 Qora libosli odamlar 3'),
    ('75', 'BAACAgUAAxkBAAIQ3GpyPaIlkO91f8xBznT0ZV24s-NLAALhEQACGJbAVONOsH27p05ePQQ', '🎬 Qora libosli odamlar 4'),
    ('76', 'BAACAgIAAxkBAAIROmpyUB1Bc4cKo5h-zdOLpd7Ug6uCAAKjsQACsAKQS8ZYTUwmpnwTPQQ', '🎬 Mehir Hududi'),
    ('80', 'BAACAgUAAxkBAAIWhGp_E0dGJiGdRnT7Nqf4MREsZzVjAAK2IgAC5lDxV_-_NbBBNLXSPQQ', '🎬  Sereniti missiyasi'),
    ('81', 'BAACAgQAAxkBAAIWq2p_LbSykRX87YIm54NP3J3MLz3GAAJ3HQAC-QjZU6pbY4uilDp9PQQ', '🎬  Platforma 1'),
    ('82', 'BAACAgIAAxkBAAIXNGp_620-fDpBQQ6uDSEhl-P_BSp-AAIHMAACVk3ASiG-MyNn68cEPQQ', '🎬  Persi Jekson 2: Dengiz maxluqlari'),
    ('90', 'BAACAgUAAxkBAAIV5Wp8pX_Ymzp3GOEtL7yAc8pwmk_3AAKRDgACZZPIVyBvGlmflc03PQQ', '🎬  Sokin Hudud 1'),
    ('100', 'BAACAgQAAxkBAAID5mpfgX2Ij1TNuY9MT6tdVyT_YlTWAAIWCAAC01AYUxoxaOmOy9dvPQQ', '🎬 Madakaskar pingvinglari 3')
on conflict (movie_code) do nothing;


-- =====================================================
-- 4. ADMINLAR (parolsiz qo'lda qo'shish)
-- =====================================================

insert into public.admins (user_id, username)
values (8363001073, 'Yangi admin')
on conflict (user_id) do nothing;


-- =====================================================
-- 5. TEKSHIRISH
-- =====================================================

select 'kinolar' as jadval, count(*) as soni from public.movies
union all
select 'adminlar', count(*) from public.admins;
