# PS4 Exploit Host
Firmwares: `5.05` `6.72` `7.XX` `8.XX` `9.XX` `10.XX` `11.XX` `12.XX` `13.XX` `14.00` `14.02`

## Steps:

- In the console browser go to: https://houbi39.github.io/gameover/
- Select the firmware of your console.
- Allow the offline cache installation/update to finish. When the page confirms success, close and reopen the PS4 browser.
- Then go back to Access Browser and Enjoy.

## Offline cache maintenance

This host retains the legacy HTML Application Cache for compatibility with the PS4 browser. Do not replace it with Service Workers without testing on the console.

Before every GitHub Pages deployment, the workflow runs `scripts/update_appcache_manifests.py`. It hashes the local resources listed in each `CACHE` section, updates the manifest version comment whenever any cached resource changes, validates every listed file (including query-versioned paths), and checks the generated manifests. The cache installer pages activate completed updates with `swapCache()` and ask the user to reopen the browser so newly loaded resources come from the new cache.

For local maintenance:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/update_appcache_manifests.py
python3 scripts/update_appcache_manifests.py --check
```
