-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- 1. Processes Table (replaces processes.json)
create table if not exists processes (
    id uuid default uuid_generate_v4() primary key,
    process_name text not null,
    team text,
    applicant_name text default 'Wio Applicant',
    stock_id text,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    updated_at timestamp with time zone default timezone('utc'::text, now()) not null,
    status text default 'In Progress',
    year text
);

-- 2. Process Details/Sections (replaces process_{id}.json)
create table if not exists process_sections (
    id uuid default uuid_generate_v4() primary key,
    process_id uuid references processes(id) on delete cascade,
    section_name text not null, -- 'overview', 'activityLogs', 'keyDetails', 'sidebarArtifacts', 'messages'
    title text,
    content jsonb default '[]'::jsonb, -- Stores the 'items' or 'content' string
    updated_at timestamp with time zone default timezone('utc'::text, now()) not null,
    unique(process_id, section_name)
);

-- Indexes for performance
create index if not exists idx_process_sections_process_id on process_sections(process_id);
