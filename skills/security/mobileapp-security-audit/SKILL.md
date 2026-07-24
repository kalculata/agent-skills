---
name: mobileapp-security-audit
description: >-
  Run a security audit of a mobile app repository, focused on Flutter: check
  pub/Gradle/CocoaPods dependencies for known vulnerabilities, scan the
  working tree and full git history for keystores, .env files, API keys and
  other secrets (anything bundled as a Flutter asset ships inside the APK/IPA),
  review mobile hardening issues — insecure storage, cleartext traffic,
  disabled certificate validation, debuggable/backup flags, missing
  obfuscation, exported components, WebView misuse — and read the Dart source
  for code-level flaws: SQL injection, crypto misuse, weak randomness,
  client-side-only authorization, unsafe deep-link handling, fail-open error
  handling. Use when the user asks to
  audit a mobile/Flutter app, check it for vulnerabilities, scan for leaked
  keys, or harden an app before release. Ends with a severity-ranked report
  (Critical/Medium/Small) stating how to fix each issue and whether the user
  must fix it manually or you can fix it.
---

# Mobile App Security Audit (Flutter-first)

Audit the current mobile app repository for security issues, then present a single consolidated report. This skill is **analysis first**: do not change anything during the audit. Fixes happen only in Step 8, after the user picks what to fix.

Primary target is **Flutter** (Dart + embedded Android/iOS projects). If the repo turns out to be native Android, native iOS, or React Native instead, apply the platform-side checks (Steps 3–7) that still fit and say which Flutter-specific checks were skipped.

Severity levels used throughout:

- 🔴 **Critical** — exploitable now or secrets shipped/exposed (signing keystore committed, live API secret in Dart code or a bundled asset, TLS validation disabled, `debuggable` release build).
- 🟠 **Medium** — weakens security but needs conditions to exploit (tokens in SharedPreferences, cleartext traffic allowed, missing obfuscation, vulnerable dependency without a public exploit).
- 🟡 **Small** — hygiene and hardening (version drift, missing `.gitignore` entries, verbose logging, overly broad permissions).

## Step 1 — Identify the stack

Look at the repo root and platform folders to determine what you're auditing:

- `pubspec.yaml` + `pubspec.lock` → Flutter/Dart; note the Flutter SDK constraint and key packages (`http`/`dio`, `shared_preferences`, `flutter_secure_storage`, `webview_flutter`, `firebase_*`, `flutter_dotenv`, `envied`).
- `android/` → `app/build.gradle(.kts)` (minSdk, signingConfigs, buildTypes), `AndroidManifest.xml`, `key.properties`, `google-services.json`.
- `ios/` → `Info.plist`, `Podfile`/`Podfile.lock`, entitlements, `GoogleService-Info.plist`.
- Build/CI hints: `codemagic.yaml`, `.github/workflows/`, fastlane, shorebird.

Note everything found — later steps depend on it. If there is no `pubspec.yaml`, tell the user this repo doesn't look like a Flutter app, identify what it actually is, and continue with whatever applies.

## Step 2 — Dependency audit

Dart has no built-in `pub audit`, so combine tools:

```bash
# Known-vulnerability scan across pubspec.lock, Podfile.lock and Gradle lockfiles
osv-scanner scan --lockfile pubspec.lock || osv-scanner -r .

# Version drift (discontinued packages are flagged here too)
flutter pub outdated || dart pub outdated

# Flutter SDK itself — old SDKs bundle an old Dart/engine with known CVEs
flutter --version
```

If `osv-scanner` isn't installed, prefer running it in a throwaway way (`brew install osv-scanner`, or `docker run ghcr.io/google/osv-scanner`) over guessing. If nothing can run, fall back to reading `pubspec.lock` and flagging packages that are several major versions behind or marked discontinued on pub.dev.

Also check the Android side: `android/app/build.gradle` dependencies and the Android Gradle Plugin / Kotlin versions; and `ios/Podfile.lock` for pinned pods that are far behind.

Record for the report, per finding: package, installed version, fixed version, CVE/OSV advisory if given. Severity mapping: known CVE with available fix → 🔴 if high/critical advisory, 🟠 if moderate; discontinued package or outdated major version with no known CVE → 🟠; minor/patch drift → 🟡.

Fixability: version bumps are usually **agent-fixable** (edit `pubspec.yaml`, `flutter pub get`, run `flutter analyze` and the test suite). Major-version upgrades with breaking changes, and Flutter SDK upgrades, are **manual (or agent-assisted with user approval)** — say so per package.

## Step 3 — Secrets in the working tree

Mobile repos leak differently than webapps: signing material and config files are the usual offenders, and **anything under `assets:` in `pubspec.yaml` ships inside the APK/IPA where anyone can unzip and read it**.

```bash
# Committed sensitive files
git ls-files | grep -iE '\.(jks|keystore|p12|p8|pem|key|mobileprovision)$|(^|/)key\.properties$|(^|/)\.env(\..*)?$|service.?account.*\.json|credentials|secret'

# Hardcoded credentials in Dart and platform code
git grep -nIiE '(api[_-]?key|secret|password|token|authorization)["'"'"']?\s*[:=]\s*["'"'"'][^"'"'"']{8,}' -- '*.dart' '*.kt' '*.java' '*.swift' '*.xml' '*.plist' '*.gradle*' ':!*.lock'
git grep -nIE 'AKIA[0-9A-Z]{16}|sk_live_|AIza[0-9A-Za-z_-]{35}|ghp_[A-Za-z0-9]{36}|-----BEGIN (RSA|EC|OPENSSH) PRIVATE KEY-----'
```

Then check what gets bundled:

- `flutter_dotenv` loading a `.env` listed under `assets:` → that .env ships in the app bundle. Any *server-side* secret in it (Stripe secret key, service-account JSON, admin API token) is 🔴. Client-side identifiers are lower severity — see next point.
- `google-services.json` / `GoogleService-Info.plist` and Firebase/Google Maps `AIza…` keys are *designed* to be in the app, so they are not automatically critical — but flag them 🟡 with a note to add API-key restrictions (package name + SHA-1 / bundle ID) in the Google Cloud console, and 🟠 if the key is unrestricted or is used for paid APIs.
- `--dart-define` values referenced in CI: compile-time defines end up as plain strings in the binary. Fine for endpoints and flags; 🔴 if a true secret is passed this way with the assumption it's hidden.
- Upload/signing keystore (`*.jks`, `*.keystore`) or `key.properties` with `storePassword` committed → 🔴. Losing control of the upload key is an app-identity compromise.

Also verify `.gitignore` covers `key.properties`, `*.jks`, `*.keystore`, `.env*`, and `**/xcuserdata/`. Missing entries with no secret actually committed is 🟡 Small.

**Never print secret values** in your output — show file, line, and a redacted form (`sk_live_•••`).

## Step 4 — Secrets in git history

Even if the working tree is clean, secrets may live in old commits:

```bash
# Files ever committed under sensitive names, and the commits that touched them
git log --all --diff-filter=A --name-only --format='commit %h' -- '*.jks' '*.keystore' '*.p12' '*.p8' '*.pem' 'key.properties' '*.env' '.env.*' '*credentials*' '*secret*' '*service?account*' | grep -v '^$'

# Content search across all history (can be slow on big repos — warn the user first)
git log --all -p -G'AKIA[0-9A-Z]{16}|sk_live_|AIza[0-9A-Za-z_-]{35}|ghp_|storePassword|-----BEGIN .*PRIVATE KEY' --format='commit %h %s' -- . ':!*.lock' | grep -E '^commit|AKIA|sk_live_|AIza|ghp_|storePassword|PRIVATE KEY' | head -50
```

If the repo has a public or shared remote, anything found here is 🔴 regardless of whether it was later deleted — **deletion does not remove it from history**.

When something is found, tell the user two things, in this order:

1. **Rotate first.** Exposed credentials must be treated as compromised and revoked/rotated at the provider *before* any history cleanup. For a leaked **upload keystore**, that means requesting an upload-key reset in Google Play Console (and for iOS, revoking the certificate/key in the Apple Developer portal) — rewriting history does not un-leak a key. This part is always **manual**.
2. **Propose the history rewrite.** Offer to purge the files/strings from history with `git filter-repo` (preferred) or BFG:

```bash
# example: remove every historical keystore and .env
git filter-repo --invert-paths --path-glob '*.jks' --path-glob '*.keystore' --path key.properties --path .env --path-glob '.env.*'
git push --force --all && git push --force --tags
```

Warn explicitly before doing this: it rewrites every commit hash after the earliest affected commit, requires a **force-push**, breaks open PRs, and every collaborator must re-clone. GitHub also caches old commits — the user should contact GitHub support (or make the repo private temporarily) to fully evict them. **Never run the rewrite or force-push without explicit user confirmation in this conversation.** The rewrite itself is **agent-fixable** once confirmed; rotation stays manual.

## Step 5 — Flutter & Dart hardening review

Check what you can actually verify in the code; don't speculate.

- **Token/credential storage** — `shared_preferences` used for auth tokens, refresh tokens, or PII (grep for `SharedPreferences` near `token`/`auth`/`password`). SharedPreferences/NSUserDefaults are plaintext on disk → 🟠; recommend `flutter_secure_storage` (Keychain/Keystore-backed). Sqflite/Hive/Isar databases holding sensitive data unencrypted → 🟠.
- **TLS validation disabled** — `badCertificateCallback` returning `true`, `HttpOverrides` with a permissive `createHttpClient`, dio `onBadCertificate: (_) => true` → 🔴 anywhere it can reach a release build; 🟡 if provably dev-only (guarded by `kDebugMode`).
- **Certificate pinning** — absent for apps handling sensitive data (banking/health/payments): 🟡 recommendation, not a defect. If a pinning package is present, check the pins aren't expired/commented out.
- **WebView misuse** — `webview_flutter`/`flutter_inappwebview` loading URLs built from user input or deep-link parameters, `addJavaScriptChannel` exposing native functionality to arbitrary pages, `javascriptMode: unrestricted` with untrusted content → 🟠 (note as "needs review" rather than claiming proof).
- **Logging** — `print`/`debugPrint`/`log` of tokens, responses, or PII; dio `LogInterceptor(responseBody: true)` left on in release → 🟠 if sensitive data is provably logged, 🟡 otherwise.
- **Obfuscation** — release build commands in CI/scripts/README missing `--obfuscate --split-debug-info=...` → 🟡 (raises effort to reverse-engineer Dart code; not a substitute for keeping secrets out).
- **Deep links** — `uni_links`/`app_links`/`go_router` handling: parameters passed unvalidated into navigation or WebViews → 🟠 needs review. `autoVerify`/associated-domains not set for links that assume trust → 🟡.
- **Firebase** — if `firebase_*` packages are present, you usually cannot see Security Rules from the app repo. If `firestore.rules`/`storage.rules`/`database.rules.json` are committed, review them: `allow read, write: if true` (or `if request.auth != null` guarding all data for any signed-in user) → 🔴. If rules are not in the repo, add a 🟡 line telling the user to verify rules in the Firebase console — client apps are trivially inspectable, so rules are the only real boundary.
- **Root/jailbreak & tamper detection** — absent: mention only for high-risk apps (payments, DRM) as a 🟡 recommendation.

## Step 6 — Dart source code review

Unlike the grep checks above, this step means **reading the code**. Don't read all of `lib/` on a large app — prioritize the security-relevant surface: auth/session services, API clients and interceptors, anything touching payments or PII, crypto/utils, database helpers, and deep-link/notification handlers. Say in the report which areas you read and which you skipped.

Look for:

- **SQL injection** — sqflite `rawQuery`/`rawInsert`/`rawUpdate`/`rawDelete` (or `database.execute`) built with string interpolation (`'... WHERE id = $id'`) instead of `?` placeholders and `whereArgs` → 🟠, 🔴 if the interpolated value comes from user or server input.
- **Crypto misuse** — `Random()` instead of `Random.secure()` for tokens/OTPs/nonces; hardcoded AES keys or IVs in source; ECB mode; MD5/SHA-1 for password hashing; hand-rolled crypto instead of a maintained package → 🟠, 🔴 for a hardcoded key protecting real user data.
- **Client-side-only authorization** — roles/flags (`isAdmin`, `isPremium`, feature gates, prices) read from local storage or computed in the app and trusted without server-side enforcement. The binary is public and modifiable, so client checks are UX, not security → 🟠, flagged as "verify the backend enforces this."
- **Auth/session logic** — tokens with no expiry handling or refresh-token rotation; `local_auth` biometric results not actually gating access to the protected secret (a boolean check the OS gates, while the token sits readable in storage); logout that doesn't clear stored credentials → 🟠 needs review.
- **Deep-link handling** — read the actual handlers (`app_links`/`uni_links` stream listeners, `go_router` `redirect` logic, `onGenerateRoute`), not just their registration: scheme/host not checked before acting on a link; payload values passed unvalidated into navigation routes, WebView URLs, or query parameters forwarded to the backend; links that can land directly on an authenticated or sensitive screen, skipping the login/PIN/biometric route guard; link parameters driving open-redirect-style navigation to external URLs → 🟠, 🔴 if a crafted link provably bypasses an auth gate.
- **Unvalidated external input** — notification/QR/clipboard payload values used the same ways as deep-link params above, and path traversal via server- or user-supplied filenames in `File('$dir/$name')` → 🟠.
- **Error handling** — broad or empty `catch` blocks that **fail open**: certificate-pinning or signature-verification errors swallowed and the request proceeds, an auth/permission check wrapped in try/catch that defaults to allowed on exception → 🟠, 🔴 if it provably disables a security control. Raw exception details, stack traces, or backend error bodies rendered in the UI (leaks endpoints, queries, internal versions) → 🟡. Global handlers (`FlutterError.onError`, `runZonedGuarded`, `PlatformDispatcher.onError`) forwarding tokens or PII to crash reporting → 🟠. Also flag the absence of any global error handler in `main()` as 🟡 — unhandled errors then surface raw to users or die silently.
- **Sensitive data in the wrong place** — secrets written to external/temp storage, PII in analytics/crash-reporting calls (`FirebaseCrashlytics.log`, custom events), secrets copied to the clipboard without expiry → 🟠 if provable, 🟡 otherwise.

For code-level findings, be precise about what you verified versus what needs a runtime check or backend knowledge you don't have — report the latter as "needs review", not as confirmed vulnerabilities.

## Step 7 — Platform config review (Android & iOS)

**Android** (`android/app/src/main/AndroidManifest.xml`, `build.gradle`):

- `android:debuggable="true"` in the main manifest or release build type → 🔴.
- `android:usesCleartextTraffic="true"` or a `network_security_config` permitting cleartext for non-localhost domains → 🟠.
- `android:allowBackup="true"` (default when unset) on an app storing sensitive data → 🟡; recommend `false` or backup rules excluding secrets.
- Release `signingConfig` falling back to `signingConfigs.debug` → 🔴 for a shipping app.
- Exported components: `android:exported="true"` on activities/receivers/services beyond the main launcher, especially with intent filters and no permission guard → 🟠 needs review.
- `minSdkVersion` below 23 → 🟡 (pre-M devices miss modern TLS and keystore protections).
- Overly broad permissions (`READ_EXTERNAL_STORAGE` when scoped storage suffices, location "always", `QUERY_ALL_PACKAGES`) → 🟡.

**iOS** (`ios/Runner/Info.plist`, entitlements):

- `NSAppTransportSecurity` with `NSAllowsArbitraryLoads: true` → 🟠 (🔴 if the app handles credentials/payments); per-domain exceptions are the acceptable form.
- Missing or boilerplate purpose strings (`NS*UsageDescription`) for camera/location/etc. → 🟡 (App Store rejection + privacy hygiene).
- Sensitive values (API keys, secrets) stored directly in `Info.plist` → same rules as Step 3.

## Step 8 — The report

Finish with one consolidated report — this is the deliverable. Format:

1. A one-line verdict (e.g. "11 issues: 2 critical, 5 medium, 4 small").
2. A table, **sorted Critical → Medium → Small**:

| # | Severity | Issue | Where | How to fix | Who fixes it |
|---|----------|-------|-------|------------|--------------|
| 1 | 🔴 Critical | Upload keystore + `key.properties` in git history | commits `a1b2c3d`… | Request upload-key reset in Play Console, then purge history with `git filter-repo` + force-push | Key reset: **you (manual)** · History rewrite: **me, on your go-ahead** |
| 2 | 🟠 Medium | Auth token stored in SharedPreferences | `lib/services/auth.dart:42` | Migrate to `flutter_secure_storage` | **Me** |
| 3 | 🟡 Small | Release build not obfuscated | `codemagic.yaml` | Add `--obfuscate --split-debug-info` | **Me** |

3. For every issue, "Who fixes it" must be explicit: **me** (agent can do it now), **you (manual)** (key rotation, Play/App Store consoles, Firebase console, business decisions), or **me, with your approval** (breaking upgrades, history rewrites, force-pushes).
4. End by asking which of the agent-fixable issues to apply. Apply only what the user picks, one logical change per commit if they want commits, and re-run the relevant check afterwards (`flutter analyze`, tests, re-grep) to confirm the fix.

## Safety rules

- Read-only until the user approves fixes; never auto-run `pub upgrade`, `git filter-repo`, or any push during the audit.
- Never force-push or rewrite history without explicit confirmation in this conversation, and always state the consequences (new hashes, re-clones, broken PRs) before asking.
- Never print discovered secret values — redact them.
- Exposed secrets are compromised even after a history rewrite: rotation always comes first; a leaked upload keystore needs a key reset with the store, not just repo cleanup.
- Remember the core mobile rule when judging severity: **the app bundle is public**. Anything in Dart code, assets, or `--dart-define` can be extracted from the APK/IPA — real secrets belong on a backend.
- Audit only apps/repos the user owns or is authorized to assess.
