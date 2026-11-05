"""Assemble a private rock-layer proof from registered artwork and masks."""

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def preview(scene, clean_art, ground_mask, rock_mask, shadow_mask, output):
    if scene.getextrema()[3] != (255, 255):
        raise ValueError('Select a fully covered terrain region')
    if any(image.size != scene.size for image in (clean_art, ground_mask, rock_mask, shadow_mask)):
        raise ValueError('Registered art and masks must match the scene dimensions')
    coverage = np.asarray(rock_mask)
    if not np.any(coverage == 255) or not np.any(coverage == 0):
        raise ValueError('Expected a solid rock silhouette with transparent surroundings')
    if np.any(np.asarray(ground_mask)[coverage > 0] != 255):
        raise ValueError('Clean ground must fully cover the original rock silhouette')

    ground = Image.composite(clean_art, scene, ground_mask)
    shadow = Image.new('RGBA', scene.size, (0, 0, 0, 0))
    shadow.putalpha(shadow_mask)
    rock_pixels = np.array(scene)
    rock_pixels[:, :, 3] = coverage
    rock_pixels[coverage == 0] = 0
    rock = Image.fromarray(rock_pixels)
    assembled = Image.alpha_composite(Image.alpha_composite(ground, shadow), rock)

    output.mkdir(parents=True)
    for name, layer in (('ground', ground), ('shadow', shadow), ('rock', rock), ('assembled', assembled)):
        layer.save(output / f'{name}.png')
    strip = Image.new('RGB', (scene.width * 3, scene.height + 24), (30, 30, 30))
    draw = ImageDraw.Draw(strip)
    for i, (label, layer) in enumerate((('RC1', scene), ('Ground alone', ground), ('RC2 assembled', assembled))):
        offset = i * scene.width
        strip.paste(layer, (offset, 24))
        draw.text((offset + 8, 6), label, fill='white')
    strip.save(output / 'comparison.png')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('scene', 'clean_art', 'ground_mask', 'rock_mask', 'shadow_mask', 'output'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    preview(Image.open(args.scene).convert('RGBA'), Image.open(args.clean_art).convert('RGBA'),
            Image.open(args.ground_mask).convert('L'), Image.open(args.rock_mask).convert('L'),
            Image.open(args.shadow_mask).convert('L'), args.output)
