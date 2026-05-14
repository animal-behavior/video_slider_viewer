# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Dependency management and execution go through `uv` (the project has a `uv.lock` and uses `pyproject.toml` as the single source of truth)

There are no tests, lint config, or formatter config in this repo.

## Architecture

Single-file PyQt5 desktop application (`video_slider_viewer.py`, ~300 LOC). All logic lives in one `VideoPlayer(QMainWindow)` class — there are no modules, packages, or other source files.

The app overlays a CSV-driven skeleton on top of video frames:

- **Video** is opened with `cv2.VideoCapture` and frames are seeked via `CAP_PROP_POS_FRAMES`. Each requested frame is drawn into a `QLabel` as a `QPixmap` after a BGR→RGB conversion. The `QLabel` is resized to the native video resolution, so very large videos produce very large windows.
- **CSV** is loaded with pandas. The first column must be `frame`; remaining columns are interpreted as `(x, y)` pairs in order. Pair labels are derived from the x-column name by lowercasing and stripping `_` and `x` — see `load_csv` (`video_slider_viewer.py:163`).
- **Skeleton overlay** is hard-coded in `show_frame` (`video_slider_viewer.py:214`) to the joint sequence `iliac crest → hip → knee → ankle → mtp → toe`. Only those labels are drawn; any other CSV columns are silently ignored. Connecting yellow lines are drawn in CSV order, not skeleton order — adding/reordering joints requires editing both the `key_points` list and ensuring CSV column order matches.
- **Frame range** is user-controlled via two `QSpinBox` widgets and a "Set Frame Range" button that updates `self.min_frame`/`self.max_frame` and the slider bounds. Arrow keys step ±1 frame within that range (`keyPressEvent`, `video_slider_viewer.py:271`).

Cross-platform note: `PyQt5-Qt5==5.15.2` is pinned in `pyproject.toml` with `sys_platform == 'win32'` because newer `PyQt5-Qt5` releases publish no Windows wheels. Don't loosen this pin without verifying Windows wheel availability.
