# Website editor review — 7 October 2026

Reviewed the launcher, setup, configuration, application shell, shared utilities, and every editor tab. These fixes are included in editor release v1.5.2, together with the relay-record and gallery-footer repairs.

The bounded source reviews used the installed WebAgentGPT bridge. Repository inspection, implementation, integration decisions and testing were performed locally.

| Area | Confirmed failure | Correction |
| --- | --- | --- |
| Saving | Interrupted writes/copies could truncate existing HTML, JSON or assets. | Write a complete temporary file and replace the destination after success. |
| Sponsor save batches | A later category's write failure could leave earlier categories changed. | Render every category first; journal the batch, roll back failed writes and recover interrupted batches before loading tabs. Preserve backups if recovery needs manual intervention. |
| Save feedback | The text editor could report success after a failed write; news could mutate its model before a failed save. | Return explicit success/failure and commit news model changes after saving succeeds. |
| Drafts | Switching news items, refreshing tabs or closing could discard pending changes; publishing omitted drafts. | Track saved state, confirm discards, preserve dirty tabs on automatic reload and require saving before publication. |
| Calendar events | Saving sorted the live events list, changing indices captured by Edit/Delete buttons. | Sort a copy for serialization; preserve the live list order. |
| Calendar months | Changing the year could write the old checkboxes into the new year's selection. | Persist the year actually displayed; validate typed years. |
| Malformed data | Invalid JSON structures, duplicate ids and invalid folder paths could crash tabs or expose an empty model that could overwrite the original file. | Validate schemas before loading; preserve previous models and disable relevant writes after failed loads. |
| Uploads | Matching filenames could overwrite assets referenced by another article, person, sponsor or document. | Import under an available filename and update the new reference. Explicit Media replacement remains a replacement operation. |
| Cancelled uploads | Discarded edits could leave unused imported files in the site. | Track files created by this editor session; remove unchanged, unreferenced imports after discard, while protecting persisted references, other drafts and existing assets. |
| Gallery deletion | Asset files were removed before gallery JSON was saved. A save failure left broken references. | Save metadata first, restore the model on failure and retain images still referenced by another gallery entry. |
| Website text | Unchanged saves collapsed raw whitespace and removed empty site containers. Equal text in separate DOM nodes shared one dictionary entry. | Preserve unchanged displayed text and original whitespace, retain existing empty containers and identify nodes by object identity. |
| Dialogs | Failed asset copies and FAQ saves could close the modal and lose the entered draft. | Keep the dialog open when its callback rejects the save. |
| Trainers | Editing a trainer in the same group moved it to the end; new groups referenced invented image filenames. | Update in place; use an existing placeholder and an empty thumbnail list. |
| Sponsors | Editing an item reselected the last item; saves rebuilt sponsor markup and lost extra attributes/picture content. | Reselect the edited index and retain the source item markup while updating owned fields. |
| Ages | Changing table rows rebuilt the unchanged introduction and removed links/formatting. | Retain the original introduction when its text is unchanged. |
| Downloads | Duplicate labels/filenames could cause an action on the first matching entry rather than the selected row. | Use the original model index as the row identity, including after sorting. |
| Media | A replacement could put one image format under another extension. Rotation could flatten an animation into JPEG and overwrite in place. | Require a matching replacement format, preserve the original file on failed rotation and refuse animation flattening. |
| Git publication | A failed pull could leave local changes hidden in a stash; conflict handling overwrote whole upstream files and dropped the stash. | Track the exact new stash, restore after a failed pull, preserve conflicts for recovery, use fast-forward pulls and normal pushes. Never rebuild the index by deleting it/resetting staging. |
| Publication exclusions | Files excluded from publication could still enter a commit through an existing staged change. | Apply the same exclusions to staging, change detection and committing; retain excluded staged changes locally. |
| Background work | Worker threads called Tk; editing/closing during Git operations could interfere with file changes. | Queue completions onto the main thread, cover the editor during Git operations and wait before closing. |
| Reload feedback | Failed reloads could be followed by a misleading ready message. | Report failed tab reloads and always restore the discard guard. |
| Paths/preview | Local asset URLs ignored the HTML directory/query suffix; lexical containment checks could follow junctions outside the site. | Resolve local URLs relative to their source document and validate resolved filesystem paths, including preview index files. |
| Image previews | A missing/corrupt image destroyed a preview window, then initialization continued against that destroyed window. | Stop initialization after failure and close image file handles promptly. |

Validation: `python -m unittest discover -s tests -v` — **49 tests passed**. The checks cover interrupted writes/copies, interrupted multi-file saves and recovery, asset ownership/cleanup, malformed data, duplicate filenames, hidden Tk windows, draft cancellation, all tab initialization, calendar/download identities, text preservation, media formats, and real Git recovery/publication in isolated temporary repositories. The record tests round-trip all 61 club-record pages twice. No test publishes to the real repository.

The Windows executable passed its hidden startup check: all 12 tabs initialized with no pending edits; Pillow, PyMuPDF, lxml and Beautiful Soup were available; its embedded version is 1.5.2.0.

Git conflicts or diverged branches stop publication and preserve work for reconciliation. Recovery also preserves backup files if another process has changed a target since an interrupted save.

The editor source, regression tests, build specification and pinned build dependencies are now versioned. Generated executables are distributed through GitHub releases. See `RELEASE_NOTES.md` for build instructions.
