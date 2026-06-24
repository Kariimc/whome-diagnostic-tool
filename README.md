# WHome Diagnostic Tool

A lightweight, native **Windows** repair utility with a real GUI. Just **tell it
what's wrong in plain English** and it builds and runs the right repair plan —
in the correct order, starting with a safety restore point. Under the hood it
drives the genuinely useful built-in Windows tools — the **Windows Update
reset**, **SFC**, **DISM**, **CHKDSK**, restore points, and the network resets —
asynchronously, streaming their output live so the window never freezes.

Built with [Flet](https://flet.dev) (Flutter-powered desktop UI) and `asyncio`.

### ⭐ The guided way: tell it what to fix

The app opens on the **Fix My PC** tab:

1. Type the problem in your own words — e.g. *“Windows won't finish updating and
   I'm stuck on an old version”* — and click **Build my fix plan** (or pick a
   common problem button).
2. The app shows **exactly what it will do**, step by step, with risk and time
   for each.
3. Turn **Safe Mode** off (top-right) when you're ready, then click
   **Run the full fix**. It creates a restore point first, then runs every step
   in order, streaming progress live.

For the **stuck-update** case it runs the complete, canonical repair:
restore point → **clear the corrupted update cache** (stop services → rename
`SoftwareDistribution` + `catroot2` → restart) → **repair the Windows image**
(DISM) → **repair system files** (SFC) → **re-check for updates** → open the
official upgrade page. Then reboot and open *Settings ▸ Windows Update*.

#### One-click upgrade for PCs that are too far behind

If your PC is on an out-of-support build (e.g. **1903**), Windows Update often
can't climb all the way to the current release on its own. When you pick the
update problem, the plan preview shows an **“Upgrade to 22H2 now”** button that
**downloads Microsoft's official Update Assistant and launches it** for an
in-place upgrade — keeping your files and apps. (It's also a card on the
**Updates** tab.) Downloads via `curl.exe` with a PowerShell fallback; if a
network blocks it, the app tells you to use the **Open the upgrade page** button
instead. Plan on 30–90 minutes and a few automatic reboots.

> Prefer to drive it yourself? The **Updates**, **OS Repair** and **Network**
> tabs expose every tool individually, each with its own Run button.

> **Safety first:** the app starts in **Safe Mode (Dry Run)** — commands are
> *simulated*, nothing on your PC changes. Flip the **Safe Mode** switch off when
> you're ready to perform real repairs.

---

## ▶ Use it today (two ways)

You need a **Windows PC** (these are Windows-only tools). Get the code onto it
(clone the repo or download it as a ZIP), then pick one path:

### Option A — Run it now (fastest, ~1 minute)

1. Make sure **Python** is installed — <https://www.python.org/downloads/>
   (on the first installer screen, tick **“Add python.exe to PATH”**).
2. **Double-click `run.bat`.**
   It creates a virtual environment, installs Flet, and launches the app.
3. For full repair powers, **right-click `run.bat` → “Run as administrator.”**
   (Or just click **Restart as Administrator** in the app when it asks.)

### Option B — Build a standalone `.exe` (no Python needed to run it later)

1. **Double-click `build.bat`** (needs Python once, for the build).
2. When it finishes, your app is at **`dist\WHomeDiagnostics.exe`** — a single
   file you can copy to any Windows PC and double-click. Windows will prompt for
   Administrator rights automatically.

> ℹ️ **Why isn't a prebuilt `.exe` included?** A Windows `.exe` must be packaged
> **on Windows** (PyInstaller/`flet pack` can't cross-compile from Linux, where
> this repo was generated). `build.bat` does it for you in a couple of clicks.

---

## What it can fix

| Section | Tool | What it does |
|---|---|---|
| **Windows Update** | **Reset Windows Update** | Stops services, clears `SoftwareDistribution` + `catroot2` caches, restarts — the #1 fix for stuck updates |
| | Repair image / files / re-scan | DISM + SFC + `UsoClient StartScan` to finish the update repair |
| | **Upgrade to 22H2 now** | Downloads + launches Microsoft's Update Assistant for an in-place upgrade (the fix for out-of-support builds like 1903) |
| | Restart Update services only | Lighter bounce of `wuauserv` + `bits` for a hung check |
| **OS Repair** | DISM `/RestoreHealth` | Repairs the Windows image from Windows Update |
| | SFC `/scannow` | Repairs corrupted protected system files |
| | SFC `/verifyonly` | Checks system files **without** changing anything |
| | DISM `/CheckHealth`, `/ScanHealth` | Quick / deep component-store checks |
| | CHKDSK `C:` | Read-only scan of the system drive |
| | DISM `/StartComponentCleanup` | Frees disk space from superseded components |
| **Network & Runtime** | `ipconfig /flushdns` | Clears the DNS cache |
| | `netsh winsock reset` | Fixes “connected but no internet” (reboot after) |
| | `netsh int ip reset` | Resets the TCP/IP stack (reboot after) |
| | `ipconfig /renew` | Requests a fresh DHCP lease |
| | `ipconfig /all`, `systeminfo` | Read-only system/network information |

Each tool is tagged **SAFE / MODIFIES SYSTEM / REBOOT AFTER** in the UI, with an
estimated runtime and whether it needs Administrator rights.

**Typical repair flow:** run **DISM → Repair Windows image** first, then
**SFC → Repair system files**. Logs are saved to
`Documents\..\WHomeDiagnostics-Logs` via the 💾 button in the console.

---

## Project structure

```
whome-diagnostic-tool/
├── main.py                 # Entry point: Flet page setup + privilege guard
├── requirements.txt        # flet==0.25.2
├── run.bat                 # One-click: install deps + launch
├── build.bat               # One-click: build standalone .exe (flet pack)
├── README.md
├── core/                   # Business logic — NO UI imports (one-way deps)
│   ├── __init__.py
│   ├── admin.py            # IsUserAnAdmin() check + UAC self-elevation
│   ├── executor.py         # asyncio.create_subprocess_exec + live stream piping
│   ├── tasks.py            # Data-only catalog of repair tools (cmd / multi-step / action)
│   ├── plans.py            # Symptom -> ordered plan, + free-text classifier
│   ├── upgrade.py          # Download + launch the Windows 10 Update Assistant
│   └── state.py            # Shared state incl. the global dry_run flag
├── ui/                     # Flet controls — import core, never the reverse
│   ├── __init__.py
│   ├── sidebar.py          # NavigationRail (Fix My PC / Updates / OS / Network)
│   ├── fixer.py            # Guided "describe it, I'll fix it" view
│   ├── dashboard.py        # Task cards + Run buttons per category
│   ├── header.py           # Global Safe-Mode switch + admin chip + banner
│   ├── logger.py           # Read-only streaming TextField console
│   └── dialogs.py          # Admin / privilege modals
└── assets/                 # Optional icons, etc.
```

### Architecture notes

- **Async, non-blocking.** `core/executor.py` uses
  `asyncio.create_subprocess_exec` with `asyncio.subprocess.PIPE` and reads
  output in chunks, so even a 20-minute `DISM /RestoreHealth` streams live while
  the UI stays responsive. A threaded fallback covers event loops that can't
  spawn subprocesses.
- **No circular imports.** The dependency arrow points one way: `ui → core`.
  `core` never imports `ui`. The executor takes an `emit(text)` callback (the
  console’s `append` method) instead of importing the console.
- **Privilege guard.** On startup `core/admin.py` calls
  `ctypes.windll.shell32.IsUserAnAdmin()`. If not elevated, a modal offers to
  relaunch via the UAC `runas` verb.
- **Safety.** A global `dry_run` flag (default **True**) is passed explicitly to
  every executor call. In dry-run mode the executor prints
  `DRY RUN: Executing <command>` and streams a simulated run instead of touching
  the system.

---

## Packaging details (`flet pack`)

`build.bat` runs:

```bat
flet pack main.py ^
  --name WHomeDiagnostics ^
  --product-name "WHome Diagnostic Tool" ^
  --file-description "Windows diagnostic and repair utility" ^
  --product-version 1.0.0 ^
  --file-version 1.0.0.0 ^
  --uac-admin ^
  --yes
```

- **`--uac-admin`** embeds a manifest so the `.exe` **requests Administrator
  elevation on launch** — exactly what a repair tool wants.
- **No-console / windowed:** `flet pack` produces a **windowed app with no
  console by default** — there is no separate `--noconsole` flag to pass (that is
  PyInstaller’s flag, and `flet pack` already applies it for you). If you ever
  need to *show* a console for debugging, use `--debug-console`. To pass raw
  PyInstaller flags explicitly you can use
  `--pyinstaller-build-args="--noconsole"`, but it is redundant here.
- **Single file:** `flet pack` builds a one-file `.exe` by default. Add `-D` /
  `--onedir` for a folder bundle instead.
- **Custom icon:** add `--icon assets\app.ico`.

Output lands in **`dist\WHomeDiagnostics.exe`**.

---

## Requirements

- **Windows 10 / 11** to actually run the repair commands.
- **Python 3.9–3.12** (only needed to run from source or to build the `.exe`).

## Troubleshooting

- **“Python was not found.”** Install it and tick *Add to PATH*, or run
  `build.bat` on a machine that has it and copy the resulting `.exe`.
- **A command says “access denied” / does nothing.** Run elevated — click
  **Restart as Administrator** in the app, or right-click → *Run as administrator*.
- **First launch is slow.** Flet downloads its desktop runtime once; later
  launches are fast.
- **Not on Windows?** The UI still opens in **Preview mode** with Safe Mode
  locked on, so you can explore it safely.
