# EHCS France Product DB Sync

Install this module in the source database, e.g. France.

Configure Hong Kong DB URL, DB name, username, and password in Settings.

This module pushes from France to Hong Kong. In Hong Kong, install `EHCS Hong Kong Product Sync Fields` first. France searches Hong Kong records by:

- `ehcs_source_db = France database name`
- `ehcs_source_id = France record ID`

## Performance update

Auto sync now syncs only changed records:

- Attribute value change syncs only its related attribute.
- Product variant default code/barcode/active changes sync only that variant's template.
- Manual/cron sync on empty recordset still syncs all records.
