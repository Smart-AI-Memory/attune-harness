# Disposable corrected-claim fixture

For the inspected `FileStashBackend`, `search(query, cwd=project)` gives
matching-project records a score bonus; `recent(cwd=project)` puts matching
records first. Other projects can still appear. This is retrieval preference,
not project access isolation.

The supplied source and probes do not establish the behavior of other memory
backends. Whether those backends enforce project isolation remains unknown here.

Example: Cedar and Elm each contain one equal-text violet note. With `cwd="cedar"`,
the returned IDs are:

```json
{"search": ["cedar", "elm"], "recent": ["cedar", "elm"]}
```
