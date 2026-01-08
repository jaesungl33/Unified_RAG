# Dictionary Role Fields Migration Guide

This guide explains how to populate the `component_type` and `reference_role` fields in the dictionary tables.

## Overview

The dictionary system uses two key fields to classify components and references:

1. **`component_type`** (in `dictionary_components`):
   - `COMPONENT`: Normal gameplay entity (Tank, Turret, etc.)
   - `GLOBAL_UI`: UI without a component anchor (HUD, menus, etc.)

2. **`reference_role`** (in `dictionary_references`):
   - `CORE`: Defines what the component IS
   - `UI`: UI attached to a component
   - `GLOBAL_UI`: UI not attached to any component
   - `META`: Notes, TODOs, placeholders (usually excluded)

## Prerequisites

✅ **No prerequisites needed!** The migration script will:
- Create tables if they don't exist
- Add columns if they don't exist
- Set default values for existing data

## Migration Steps

### Step 1: Run SQL Migration

Run the SQL migration script in Supabase SQL Editor:

```bash
# File: deploy/populate_dictionary_role_fields.sql
```

This script will:
- **Create tables** if they don't exist (`dictionary_components`, `dictionary_references`)
- **Add columns** `component_type` and `reference_role` if they don't exist
- Set `component_type = 'COMPONENT'` for all existing components (default)
- Set `reference_role = 'CORE'` for all existing references (default)
- Add CHECK constraints and default values for future inserts

**Note:** For a complete schema with all indexes, see `deploy/dictionary_schema.sql` (optional, for optimization)

**To run:**
1. Open Supabase Dashboard → SQL Editor
2. Copy and paste the contents of `deploy/populate_dictionary_role_fields.sql`
3. Click "Run" or press `Ctrl+Enter`

### Step 2: Validate Migration

Run the validation script to check data quality:

```bash
python scripts/validate_dictionary_roles.py
```

This will check:
- ✅ All components have `component_type` set (no NULLs)
- ✅ All references have `reference_role` set (no NULLs)
- ✅ All values are valid (within CHECK constraints)
- ✅ GLOBAL_UI components have appropriate references
- ✅ Reference roles match component types where applicable

### Step 3: Manual Classification (Required)

After the migration, you need to manually classify:

#### 3.1 Identify GLOBAL_UI Components

Find components that represent UI without gameplay entities:

```sql
-- Example: Find components that might be GLOBAL_UI
SELECT component_key, display_name_vi
FROM dictionary_components
WHERE component_key LIKE '%ui%' 
   OR component_key LIKE '%menu%'
   OR component_key LIKE '%hud%'
   OR display_name_vi ILIKE '%giao diện%'
   OR display_name_vi ILIKE '%menu%';
```

Update them:

```sql
-- Example: Mark a component as GLOBAL_UI
UPDATE dictionary_components
SET component_type = 'GLOBAL_UI'
WHERE component_key = 'global_ui';  -- or your actual key
```

#### 3.2 Classify Reference Roles

For each component, classify its references:

**CORE references** (defines the component):
```sql
-- Example: Mark references that define the component
UPDATE dictionary_references
SET reference_role = 'CORE'
WHERE component_key = 'tank'
  AND section_path LIKE '%Tank/Definition%'
  AND reference_role = 'CORE';  -- already default, but explicit
```

**UI references** (UI attached to component):
```sql
-- Example: Mark UI references for a component
UPDATE dictionary_references
SET reference_role = 'UI'
WHERE component_key = 'tank'
  AND (section_path LIKE '%Garage%'
       OR section_path LIKE '%UI%'
       OR section_path LIKE '%Selection%');
```

**GLOBAL_UI references** (UI without component):
```sql
-- Example: Mark global UI references
UPDATE dictionary_references
SET reference_role = 'GLOBAL_UI'
WHERE component_key = 'global_ui'
  AND (section_path LIKE '%HUD%'
       OR section_path LIKE '%Menu%'
       OR section_path LIKE '%Settings%');
```

**META references** (notes, TODOs):
```sql
-- Example: Mark meta references (usually exclude these)
UPDATE dictionary_references
SET reference_role = 'META'
WHERE evidence_text_vi ILIKE '%TODO%'
   OR evidence_text_vi ILIKE '%NOTE%'
   OR evidence_text_vi ILIKE '%PLACEHOLDER%';
```

## Classification Rules

### Component Classification

| Pattern | component_type | Example |
|---------|---------------|---------|
| Gameplay entity | `COMPONENT` | Tank, Turret, Cannon, Wrap |
| UI without entity | `GLOBAL_UI` | HUD, Main Menu, Settings |
| Special case: "global_ui" key | `GLOBAL_UI` | Component key = "global_ui" |

### Reference Classification

| Pattern | reference_role | Example |
|---------|---------------|---------|
| Defines component | `CORE` | "Tank is a vehicle that..." |
| UI for component | `UI` | "Tank Garage UI", "Wrap Selection UI" |
| UI without component | `GLOBAL_UI` | "HUD Clock", "Main Menu" |
| Notes/TODOs | `META` | "TODO: Add more details" |

### Special Cases

**Tank Garage UI:**
- Component: `component_key = "tank"`, `component_type = "COMPONENT"`
- Reference: `component_key = "tank"`, `reference_role = "UI"`, `section_path = "Tank/Garage/Wrap"`

**HUD Clock:**
- Component: `component_key = "global_ui"`, `component_type = "GLOBAL_UI"`
- Reference: `component_key = "global_ui"`, `reference_role = "GLOBAL_UI"`, `section_path = "HUD/GameClock"`

**Tank HP Bar:**
- Choose ONE approach and be consistent:
  - Option A: `component_key = "global_ui"`, `reference_role = "GLOBAL_UI"` (strict physical)
  - Option B: `component_key = "tank"`, `reference_role = "UI"` (attribute visualization)

## Verification Queries

After classification, verify your data:

```sql
-- Check component type distribution
SELECT 
    component_type,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage
FROM dictionary_components
GROUP BY component_type
ORDER BY count DESC;

-- Check reference role distribution
SELECT 
    reference_role,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage
FROM dictionary_references
GROUP BY reference_role
ORDER BY count DESC;

-- Check GLOBAL_UI components and their references
SELECT 
    c.component_key,
    c.display_name_vi,
    c.component_type,
    COUNT(r.id) as reference_count,
    COUNT(CASE WHEN r.reference_role = 'GLOBAL_UI' THEN 1 END) as global_ui_refs
FROM dictionary_components c
LEFT JOIN dictionary_references r ON c.component_key = r.component_key
WHERE c.component_type = 'GLOBAL_UI'
GROUP BY c.component_key, c.display_name_vi, c.component_type
ORDER BY reference_count DESC;

-- Check for mismatched roles
SELECT 
    r.component_key,
    c.component_type,
    r.reference_role,
    COUNT(*) as count
FROM dictionary_references r
JOIN dictionary_components c ON r.component_key = c.component_key
WHERE (c.component_type = 'GLOBAL_UI' AND r.reference_role != 'GLOBAL_UI')
   OR (c.component_type = 'COMPONENT' AND r.reference_role = 'GLOBAL_UI')
GROUP BY r.component_key, c.component_type, r.reference_role
ORDER BY count DESC;
```

## Next Steps

After migration and classification:

1. ✅ **Test retrieval modes:**
   - `COMPONENTS` mode should only return CORE references
   - `UI` mode should only return UI and GLOBAL_UI references
   - `BOTH` mode should return CORE and UI references

2. ✅ **Re-run validation:**
   ```bash
   python scripts/validate_dictionary_roles.py
   ```

3. ✅ **Test dictionary retrieval:**
   ```python
   from backend.dictionary_retrieval import dictionary_semantic_retrieval, RetrievalMode
   
   # Test COMPONENTS mode
   result = dictionary_semantic_retrieval("tank", mode=RetrievalMode.COMPONENTS)
   
   # Test UI mode
   result = dictionary_semantic_retrieval("garage", mode=RetrievalMode.UI)
   
   # Test BOTH mode
   result = dictionary_semantic_retrieval("tank", mode=RetrievalMode.BOTH)
   ```

## Troubleshooting

### Issue: NULL values after migration

**Solution:** Re-run the UPDATE statements in the migration script.

### Issue: Invalid values (CHECK constraint violation)

**Solution:** Check for typos or incorrect values:
```sql
-- Find invalid component_type values
SELECT component_key, component_type
FROM dictionary_components
WHERE component_type NOT IN ('COMPONENT', 'GLOBAL_UI');

-- Find invalid reference_role values
SELECT component_key, reference_role
FROM dictionary_references
WHERE reference_role NOT IN ('CORE', 'UI', 'GLOBAL_UI', 'META');
```

### Issue: GLOBAL_UI references pointing to COMPONENT components

**Solution:** Either:
1. Change the component to `GLOBAL_UI` type, OR
2. Change the reference role to `UI` (if it's UI for that component)

## Support

For questions or issues:
1. Check validation script output: `python scripts/validate_dictionary_roles.py`
2. Review classification rules in this document
3. Check Supabase logs for constraint violations

