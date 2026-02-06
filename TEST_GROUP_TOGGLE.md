# Testing Group Toggle - Debug Guide

## To Test

1. **Launch the app** with the new debug logging

2. **Create a new group:**
   - Right-click in Datasets panel → "New Group"
   - Name it "CO2"

3. **Move files into the group:**
   - Select 2 files
   - Right-click → "Move to Group" → "CO2"

4. **Click the group checkbox** (next to "CO2" group name)

5. **Check the Log panel** (bottom of screen) for debug messages:
   ```
   [Groups] Toggle visibility: group_id=..., visible=False
   [Groups] Group found: CO2
   [Groups] Found X datasets in group: [...]
   ```

## Expected Behavior

✅ **If it works:**
- Log shows: "Found 2 datasets in group: [dataset_id1, dataset_id2]"
- Both datasets toggle visibility on the plot
- Checkboxes for individual datasets also toggle

❌ **If it doesn't work:**
- Log shows: "Found 0 datasets in group: []"
- This means group_service isn't tracking the assignments

## If group_service has 0 datasets

The problem is that when you move datasets to a group, the group_service isn't being updated.

**Check:**
1. Does the log show "Moved 2 dataset(s) to 'CO2'"?
2. If yes, but group still has 0 datasets, then `group_service.assign_to_group()` isn't working

**Next step:** Check `app/services/dataset_group_service.py` to see if there's an issue with `assign_to_group()`
