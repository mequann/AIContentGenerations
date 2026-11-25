# Real photographs

Put real photos used by the film here (referenced from `storyboard.json → keyframe.image`).

- `today.jpg`: Mequannt, Aemro and Mikias today (shot s13). Landscape works best; the 9:16 version uses a
  blurred-background fill so nobody gets cropped out.

Photos of real people are **not committed** (see `.gitignore`) to keep them out of the public repository.
On a clean clone without the photo, the pipeline logs a `fallback` and generates s13 from its prompt instead,
so the film still builds end to end.
