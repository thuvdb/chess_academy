"""Thử nghiệm các model chess-piece-yolo trên board đã rectify (diagram sách)."""
import glob
import cv2
from ultralytics import YOLO

jid = "68ba94bd-b14b-40a1-8911-840ff1246794"
for mp in ("chess_yolov8s", "chess_yolov8n", "chess_yolo_pico"):
    m = YOLO(f"/app/models/{mp}.pt")
    print("==", mp, m.task, m.names)
    for name in ("page040_board00", "page003_board00"):
        p = glob.glob(f"/app/storage/scans/{jid}/boards/{name}_rectified.png")[0]
        img = cv2.imread(p)
        h, w = img.shape[:2]
        r = m.predict(img, conf=0.25, verbose=False)[0]
        print(name, "boxes:", len(r.boxes))
        for b in r.boxes:
            x1, y1, x2, y2 = b.xyxy[0].tolist()
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            sq = "abcdefgh"[min(7, int(cx / (w / 8)))] + str(8 - min(7, int(cy / (h / 8))))
            print("  ", m.names[int(b.cls)], round(float(b.conf), 2), sq)
