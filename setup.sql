-- Run once in your Supabase SQL Editor on a new project.
create table public.corpora (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  name text not null check (length(trim(name)) between 1 and 120),
  created_at timestamptz not null default now(),
  unique(owner_id, name),
  unique(id, owner_id)
);
create table public.metadata_records (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  corpus_id uuid not null,
  file_id text not null check(length(trim(file_id)) > 0),
  data jsonb not null check(jsonb_typeof(data) = 'object' and data ? 'File_ID' and data->>'File_ID' = file_id),
  created_at timestamptz not null default now(),
  foreign key(corpus_id, owner_id) references public.corpora(id, owner_id) on delete cascade,
  unique(corpus_id, file_id)
);
create index on public.metadata_records(owner_id, corpus_id);
alter table public.corpora enable row level security;
alter table public.metadata_records enable row level security;
revoke all on public.corpora, public.metadata_records from anon;
grant select, insert, update, delete on public.corpora, public.metadata_records to authenticated;
create policy own_corpora on public.corpora for all to authenticated
  using ((select auth.uid()) = owner_id)
  with check ((select auth.uid()) = owner_id);
create policy own_records on public.metadata_records for all to authenticated
  using ((select auth.uid()) = owner_id)
  with check ((select auth.uid()) = owner_id);
