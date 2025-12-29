-- Check Row Level Security (RLS) Status and Policies
-- Run this in Supabase SQL Editor to verify RLS setup

-- ============================================================================
-- 1. Check if RLS is enabled on tables
-- ============================================================================

SELECT 
    schemaname,
    tablename,
    rowsecurity as rls_enabled
FROM pg_tables
WHERE schemaname = 'public'
    AND tablename IN ('gdd_documents', 'gdd_chunks', 'code_files', 'code_chunks')
ORDER BY tablename;

-- ============================================================================
-- 2. List all RLS policies on our tables
-- ============================================================================

SELECT 
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd as command,
    qual as using_expression,
    with_check as with_check_expression
FROM pg_policies
WHERE schemaname = 'public'
    AND tablename IN ('gdd_documents', 'gdd_chunks', 'code_files', 'code_chunks')
ORDER BY tablename, policyname;

-- ============================================================================
-- 3. Check current user/role context
-- ============================================================================

SELECT 
    current_user as current_role,
    session_user as session_role;

-- ============================================================================
-- 4. Test if service_role can insert (this will fail if run as anon, but shows the check)
-- ============================================================================

-- This query shows what roles have what permissions
SELECT 
    grantee as role_name,
    table_name,
    privilege_type
FROM information_schema.role_table_grants
WHERE table_schema = 'public'
    AND table_name IN ('gdd_documents', 'gdd_chunks', 'code_files', 'code_chunks')
    AND grantee IN ('anon', 'service_role', 'authenticated')
ORDER BY table_name, grantee, privilege_type;

-- ============================================================================
-- 5. Count existing data (to verify tables are accessible)
-- ============================================================================

SELECT 'gdd_documents' as table_name, COUNT(*) as row_count FROM gdd_documents
UNION ALL
SELECT 'gdd_chunks', COUNT(*) FROM gdd_chunks
UNION ALL
SELECT 'code_files', COUNT(*) FROM code_files
UNION ALL
SELECT 'code_chunks', COUNT(*) FROM code_chunks;

