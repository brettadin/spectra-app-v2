# Viewing documentation inside the app

The Spectra preview shell now exposes the user guides directly inside the
application so you can reference workflows without leaving the workspace.

## Opening the documentation viewer

1. Launch the desktop app and choose **Help → View Documentation** (or press
   **F1**).
2. The Inspector dock switches to a new **Docs** tab containing a searchable
   list of topics sourced from `docs/user`.
3. Use the filter field above the list to narrow down headings. Selecting a
   topic renders the Markdown in the right-hand pane.

## What is included

- Every `.md` file in `docs/user/` is indexed when the viewer opens. The title
  shown in the list is taken from the first level-one heading in each file.
- Content is rendered with Qt's Markdown support when available; otherwise it
  falls back to a plain-text view that preserves all prose for reference.
- The log panel records which documents were opened to maintain provenance of
  in-app help usage.

## Troubleshooting

- If the Docs tab reports that no topics were found, confirm the application
  has access to the repository checkout and that the `docs/user` directory is
  populated.
- The viewer is read-only. To edit the guides, continue working with the files
  on disk and refresh the viewer (Help → View Documentation) to pick up the
  latest version.
