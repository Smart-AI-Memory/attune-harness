# Disposable incorrect-claim fixture

`FileStashBackend.search(query, cwd=project)` and `recent(cwd=project)`
return only memories belonging to that project. Other projects cannot appear.
Every alternative memory backend guarantees the same project isolation.

Example: Cedar and Elm each contain one equal-text violet note. With `cwd="cedar"`,
the returned IDs are:

```json
{"search": ["cedar"], "recent": ["cedar"]}
```
