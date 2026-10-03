"""Test CV classifier on page 40 which has actual chess pieces."""
import sys
sys.path.insert(0, '/app')

import cv2
import importlib
import app.services.piece_classifier as clf_module

importlib.reload(clf_module)
clf_module._model = None
clf_module._model_loaded = False

# Test page 3 (all empty) and page 40 (has pieces)
for page_file, label in [
    ('page003_board00_rectified.png', 'Page 3 Board 0 (likely all empty)'),
    ('page040_board00_rectified.png', 'Page 40 Board 0 (should have pieces)'),
]:
    img_path = f'/app/storage/scans/68ba94bd-b14b-40a1-8911-840ff1246794/boards/{page_file}'
    img = cv2.imread(img_path)
    if img is None:
        print(f'Cannot read {page_file}')
        continue

    cells = []
    cell_size = 80
    files = 'abcdefgh'
    ranks = '87654321'
    for row in range(8):
        for col in range(8):
            y1 = row * cell_size
            x1 = col * cell_size
            cell_img = img[y1:y1+cell_size, x1:x1+cell_size]
            cells.append({'square': files[col]+ranks[row], 'row': row, 'col': col, 'image': cell_img})

    results = clf_module.classify_cells(cells)
    non_empty = [r for r in results if r['piece'] != 'empty']
    print(f'\n{label}:')
    print(f'  Non-empty cells: {len(non_empty)}/64')
    for r in non_empty:
        print(f"    {r['square']}: {r['piece']} conf={r['confidence']:.2f}")
