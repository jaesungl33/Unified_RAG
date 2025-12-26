# Fix Database Function Overload Error

## Problem

Your Supabase database has two versions of the `match_gdd_chunks` function, causing PostgREST to fail with error `PGRST203` (function overload resolution).

## Solution

Run the SQL script in your Supabase SQL Editor to fix this.

## Steps

1. **Open Supabase Dashboard**
   - Go to your Supabase project
   - Navigate to **SQL Editor**

2. **Run the Fix Script**
   - Open the file `fix_database_function_overload.sql`
   - Copy the entire contents
   - Paste into Supabase SQL Editor
   - Click **Run** or press `Ctrl+Enter`

3. **Verify the Fix**
   - The script will show you which functions exist before and after
   - You should see only one `match_gdd_chunks` function remaining (the 4-parameter version)

4. **Test Again**
   ```bash
   python test_all_docs_requirements.py
   ```

## What the Script Does

- **Drops** the 7-parameter version of `match_gdd_chunks`
- **Keeps** the 4-parameter version that your code uses
- **Shows** you what functions exist before and after

## Alternative: Rename Instead of Drop

If you need the 7-parameter version later, you can rename it instead of dropping it. Uncomment the `ALTER FUNCTION ... RENAME TO` line in the script.

## After Running the Script

Once you've fixed the database, the requirement matching should work properly. The error was preventing the system from extracting requirements from GDD documents, which is why you saw 0 requirements evaluated.


