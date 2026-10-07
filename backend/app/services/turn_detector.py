import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)

class TurnDetector:
    def detect_turn(self, img: np.ndarray, board_bbox: dict, default_turn: str = "w") -> str:
        """
        Detects whether it is White or Black to move by finding a square icon
        near the board. Returns 'w' or 'b', falling back to default_turn if no icon is found.
        """
        try:
            if img is None:
                return default_turn
            
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            x, y, w, h = board_bbox["x"], board_bbox["y"], board_bbox["width"], board_bbox["height"]
            
            # Expand region by 15% to include icons near the board
            margin_x = int(w * 0.15)
            margin_y = int(h * 0.15)
            
            roi_x1 = max(0, x - margin_x)
            roi_y1 = max(0, y - margin_y)
            roi_x2 = min(img.shape[1], x + w + margin_x)
            roi_y2 = min(img.shape[0], y + h + margin_y)
            
            roi = gray[roi_y1:roi_y2, roi_x1:roi_x2]
            
            # Mask out the board itself to avoid detecting squares inside the board
            board_x_roi = x - roi_x1
            board_y_roi = y - roi_y1
            mask = np.ones(roi.shape, dtype=np.uint8) * 255
            cv2.rectangle(mask, (board_x_roi, board_y_roi), (board_x_roi + w, board_y_roi + h), 0, -1)
            
            roi_outside = cv2.bitwise_and(roi, mask)
            
            # Threshold to find dark objects (the icon outlines or black icon)
            _, thresh = cv2.threshold(roi_outside, 200, 255, cv2.THRESH_BINARY_INV)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            best_square = None
            best_area = 0
            
            for c in contours:
                peri = cv2.arcLength(c, True)
                approx = cv2.approxPolyDP(c, 0.05 * peri, True)
                
                # Check for quadrilaterals
                if len(approx) == 4:
                    cx, cy, cw, ch = cv2.boundingRect(approx)
                    aspect = cw / float(ch)
                    area = cw * ch
                    
                    # Icon square is usually small but not too small compared to board
                    # board area is w*h. Icon is usually about the size of a chess cell (w/8)*(h/8)
                    cell_area = (w / 8.0) * (h / 8.0)
                    if 0.8 < aspect < 1.2 and cell_area * 0.05 < area < cell_area * 1.5:
                        if area > best_area:
                            best_area = area
                            best_square = (cx, cy, cw, ch)
            
            if best_square:
                cx, cy, cw, ch = best_square
                # Check average pixel intensity in the original grayscale image
                # to determine if it is black (filled) or white (empty inside)
                # We look at the center of the square
                center_roi = roi[cy + int(ch*0.2):cy + int(ch*0.8), cx + int(cw*0.2):cx + int(cw*0.8)]
                if center_roi.size > 0:
                    mean_val = np.mean(center_roi)
                    logger.info("Found icon square in board region %s. Mean pixel value: %f", board_bbox, mean_val)
                    if mean_val < 128:
                        return "b"
                    else:
                        return "w"
                        
        except Exception as e:
            logger.error("Error detecting turn: %s", e)
            
        return default_turn
