Regenerate the banner (needs [uv](https://docs.astral.sh/uv/)):

```sh
# font (OFL, not committed because it is 6.7 MB)
gh release download -R TakWolf/fusion-pixel-font -p "fusion-pixel-font-12px-monospaced-ttf-v*.zip" -O /tmp/fpx.zip
unzip -jo /tmp/fpx.zip "*zh_hans.ttf" -d tools/

uvx --from pillow python tools/crt.py
```

Edit `LINES` in `tools/crt.py` to change the text, replace `tools/avatar.png` to change the portrait.
