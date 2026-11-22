# -*- coding: utf-8 -*-
"""NASA kaynaklı gezegen dokularını indirir ve oyuna uygun boyutta (2048x1024, eşdikdörtgen) kaydeder.

Kaynaklar (NASA, kamu malı):
  earth   : NASA SVS 2915  Blue Marble (bulutsuz mozaik)        https://svs.gsfc.nasa.gov/2915
  lights  : NASA SVS 5276  Black Marble 2023 gece ışıkları         https://svs.gsfc.nasa.gov/5276
  moon    : NASA SVS 4720  CGI Moon Kit, LRO LROC renkli mozaik   https://svs.gsfc.nasa.gov/4720
  mars    : NASA Mars Trek, Viking MDIM 2.1 renkli küresel mozaik  https://trek.nasa.gov/mars/
  jupiter : NASA/JPL PIA07782 Cassini silindirik harita          https://science.nasa.gov/photojournal/
Çalıştırma: python tools/fetch_nasa_maps.py   (çıktı: aetherx/nasa/*.jpg)
"""
import io
import os
import sys
import urllib.request

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aetherx", "nasa")
SIZE = (2048, 1024)
SRC = {
    "earth": "https://svs.gsfc.nasa.gov/vis/a000000/a002900/a002915/bluemarble-2048.png",
    "lights": "https://svs.gsfc.nasa.gov/vis/a000000/a005200/a005276/nightlights_flat_series_stills_only_lights.2023_web.jpg",
    "moon": "https://svs.gsfc.nasa.gov/vis/a000000/a004700/a004720/lroc_color_2k.jpg",
    "jupiter": "https://assets.science.nasa.gov/content/dam/science/psd/photojournal/pia/pia07/pia07782/PIA07782.jpg",
}
MARS_TILES = "https://trek.nasa.gov/tiles/Mars/EQ/Mars_Viking_MDIM21_ClrMosaic_global_232m/1.0.0/default/default028mm/{z}/{y}/{x}.jpg"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "kozmogenis-asset-fetch"})
    return urllib.request.urlopen(req, timeout=60).read()


def load(data, name):
    return pygame.image.load(io.BytesIO(data), name)


def mars(z=2):
    cols, rows = 2 ** (z + 1), 2 ** z          # coğrafi döşeme: z=0'da 2x1
    img = pygame.Surface((cols * 256, rows * 256))
    for y in range(rows):
        for x in range(cols):
            img.blit(load(get(MARS_TILES.format(z=z, y=y, x=x)), "t.jpg"), (x * 256, y * 256))
    return img


def main():
    pygame.init()
    os.makedirs(OUT, exist_ok=True)
    want = sys.argv[1:] or list(SRC) + ["mars"]
    for key in want:
        img = mars() if key == "mars" else load(get(SRC[key]), SRC[key].rsplit("/", 1)[-1])
        if img.get_size() != SIZE:
            img = pygame.transform.smoothscale(img.convert(24) if img.get_bitsize() != 24 else img, SIZE)
        if key == "lights":
            img.fill((0, 0, 0), (860, 600, 160, 80))     # görseldeki "2023" yıl etiketi (harita verisi değil)
        path = os.path.join(OUT, f"{key}.jpg")
        pygame.image.save(img, path)
        print(key, img.get_size(), os.path.getsize(path) // 1024, "KB")


if __name__ == "__main__":
    main()
