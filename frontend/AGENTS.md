<!-- LOVABLE:BEGIN -->
> [!IMPORTANT]
> This project is connected to [Lovable](https://lovable.dev). Avoid rewriting
> published git history — force pushing, or rebasing/amending/squashing commits
> that are already pushed — as it rewrites history on Lovable's side and the
> user will likely lose their project history.
>
> Commits you push to the connected branch sync back to Lovable and show up in
> the editor, so keep the branch in a working state.
<!-- LOVABLE:END -->

## Architecture rules
- All backend access goes through `src/lib/api.ts` (currently a browser mock: localStorage + IndexedDB). Why: the user will replace it with their own backend; keep function signatures stable so UI needn't change.
- Pure domain rules (date format, tag/password validation, duplicates, discoverability) live in `src/lib/domain.ts` with tests in `domain.test.ts`. Why: shared by the mock and any future backend.
- Signed-in pages live under the `_app` pathless layout with `ssr: false`. Why: the mock session is in localStorage.
