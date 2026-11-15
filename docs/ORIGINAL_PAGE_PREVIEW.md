# Original PDF-page preview — visible-source acceptance

## Why I changed the viewer

The original implementation exposed exact authenticated PDF bytes and linked
extraction citations to page/text/box coordinates. In a headless hosted browser,
the native PDF plugin displayed a broken-document symbol despite successful
HTTP and Blob URL checks. Those checks were valid for transport only. I did not
weaken the Content Security Policy or label the plugin icon a rendered page.

The first real PNG replacement made page rendering possible but an operator
could trigger a second same-page request between the pixel assertion and the
screen capture. The request temporarily hid the image. A subsequent fix retains
the currently displayed raster and coalesces redundant in-flight requests.

## Implementation and trust boundary

- `GET /api/documents/{id}/preview?page=N` requires the same bearer
  identity as the original-download API. It never interprets a caller-supplied
  path or URL; it uses the stored immutable content address.
- The parent checks the PDF hash and strict byte/page/time/memory budgets.
  A separate Python child activates the existing parser's Linux seccomp policy
  and PDF structural active-content rejection before PDFium rasterization.
- One bounded RGB PNG is produced, with page number, pixel dimensions and
  digest reread before the parent returns `image/png`. Original PDFs remain
  available through authenticated download; raster images do not replace
  the original record or its evidence.
- JavaScript fences previews by authenticated session, case/document identity,
  selected revision and request generation. A late response cannot overwrite
  a newer document. A same-page field click does not hide or refetch a readable
  image. The page is explicitly marked unavailable if rendering fails.
- The browser qualification requires an image to decode to real dimensions,
  contain nonblank rendered pixels and remain visible **at the moment** each
  desktop/mobile screenshot is captured.

This is a non-executable alternative to the embedded PDF viewer. It is
subject to the existing Linux isolation boundary and is not a sanitization
certificate for arbitrary malicious supplier PDFs. The source is designed for
synthetic demonstration and an isolated reference environment, not an
Internet-accessible document-processing service.

## Executed evidence

| Check | Original observation |
| --- | --- |
| Executed application source | `32fb196bcc496b31071d87d02453dd6936b98ccf` |
| GitHub Actions | [Full workflow 43774003311](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43774003311): all three jobs succeeded |
| Python | 128 passed on the original downloaded report |
| JavaScript | 24 passed, including same-page view stability |
| Real Chrome browser | 36 passed; actual decoded page content and screenshot-time visibility |
| Screenshots | Two original Chrome 157 desktop/mobile images downloaded and visually inspected |
| CircleCI | Separate fast `build-and-test` status success |
| Functional limits | No external host deployment; no claim of general PDF accessibility or enterprise security |

The negative login test intentionally returned HTTP 401, appearing as one
expected console network error. No unexpected external requests or page-level
JavaScript exceptions were reported. The immutable initial `v0.1.0rc1` tag
continues to point to the original prerelease. This correction is not a new
tag or a claim that the local-linear/Qwen model acceptance criteria passed.

## Reproduction and maintenance

The GitHub workflow runs the actual `scripts/browser_smoke.py` with Chrome,
a cloned isolated synthetic state and the real API/worker. It retains the
`browser/report.json`, `browser/desktop-review.png`,
`browser/mobile-review.png` and unmodified test logs in the named
`dci-checks-*` artifact. CI artifacts have finite retention; the source
commit and browser assertion names remain permanently in this repo.

After merge, repeat the full workflow at the *merged source*, verify the
actual screenshot files and original downloadable PDF, and update
[acceptance](ACCEPTANCE.md) and [issue #11](https://github.com/mehdisafer/document-control-intelligence/issues/11)
with the observed commit. Do not infer the new main's acceptance merely from a
passing feature PR.

The broader local model, supplier-general accuracy, deployment, backup
objectives and release-maintenance gates remain in [acceptance](ACCEPTANCE.md)
and the operating guide.
