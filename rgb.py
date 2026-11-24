"""
Deteksi warna dari webcam

Kontrol:
  klik mouse -> kunci warna objek di titik yang diklik, mulai pelacakan
  t -> kunci warna dari kotak ROI di tengah frame, mulai pelacakan
  x -> berhenti melacak (kembali ke ROI tetap di tengah)
  c -> kalibrasi putih (arahkan kertas putih ke kotak tengah frame)
  r -> reset kalibrasi
  s -> simpan screenshot (hasil_deteksi.png)
  q -> keluar

Install: pip install opencv-python numpy
"""

from collections import deque

import cv2
import numpy as np

ROI_SIZE = 40        # setengah sisi kotak ROI tengah (piksel)
SMOOTHING = 0.8      # 0 = tanpa smoothing, mendekati 1 = sangat halus
LOCK_CAMERA = False  # True = coba matikan auto white balance/exposure kamera

# Parameter pelacakan objek
H_TOL = 12           # toleransi hue (skala OpenCV 0-179)
S_TOL = 70           # toleransi saturasi
V_TOL = 70           # toleransi value/kecerahan
MIN_AREA = 500       # luas kontur minimum (piksel) agar dianggap objek
TRAIL_LEN = 32       # panjang jejak pergerakan
CLICK_PATCH = 5      # setengah sisi patch untuk mengambil warna saat klik
SAVE_PANEL_SCALE = 0.55  # ukuran panel info pada screenshot (1.0 = sama dengan tampilan)

WINDOW = "Deteksi Warna v3"
MASK_WINDOW = "Mask pelacakan"


def name_from_hsv(h, s, v):
    """Tentukan nama warna dari HSV skala OpenCV (H: 0-179, S/V: 0-255)."""
    if v < 40:
        return "Hitam"
    if s < 35:
        if v > 210:
            return "Putih"
        return "Abu-abu"
    # Merah (hue di dekat 0 atau 179)
    if h >= 170 or h <= 4:
        if s < 110 and v > 170:
            return "Pink"
        return "Merah"
    if h <= 22:  # keluarga oranye / coklat / kulit
        if h <= 8 and s >= 170 and v >= 100:
            return "Merah"
        if v < 140:
            return "Coklat"
        if s < 150:
            return "Coklat muda / kulit"
        return "Oranye"
    if h <= 33:
        return "Kuning"
    if h <= 85:
        return "Hijau"
    if h <= 100:
        return "Cyan"
    if h <= 130:
        return "Biru"
    if h <= 150:
        return "Ungu"
    return "Magenta"


def median_hsv(bgr_pixels):
    """Median BGR -> HSV (satu piksel). bgr_pixels: array (N, 3) uint8."""
    med = np.median(bgr_pixels.reshape(-1, 3), axis=0)
    b, g, r = [int(round(x)) for x in med]
    hsv = cv2.cvtColor(np.uint8([[[b, g, r]]]), cv2.COLOR_BGR2HSV)[0][0]
    return int(hsv[0]), int(hsv[1]), int(hsv[2])


def build_mask(hsv_img, target):
    """Buat mask biner untuk warna target (h, s, v) di gambar HSV."""
    h, s, v = target
    v_lo, v_hi = max(v - V_TOL, 0), min(v + V_TOL, 255)

    if s < 40:
        # Warna akromatik (putih/abu/hitam): hue tidak bermakna, pakai S dan V saja
        lo = np.array([0, 0, v_lo])
        hi = np.array([179, min(s + 40, 255), v_hi])
        mask = cv2.inRange(hsv_img, lo, hi)
    else:
        s_lo, s_hi = max(s - S_TOL, 30), min(s + S_TOL, 255)
        h_lo, h_hi = h - H_TOL, h + H_TOL
        if h_lo < 0:  # melingkar di sekitar 0 (merah)
            m1 = cv2.inRange(hsv_img, np.array([h_lo + 180, s_lo, v_lo]),
                             np.array([179, s_hi, v_hi]))
            m2 = cv2.inRange(hsv_img, np.array([0, s_lo, v_lo]),
                             np.array([h_hi, s_hi, v_hi]))
            mask = cv2.bitwise_or(m1, m2)
        elif h_hi > 179:  # melingkar di sekitar 179
            m1 = cv2.inRange(hsv_img, np.array([h_lo, s_lo, v_lo]),
                             np.array([179, s_hi, v_hi]))
            m2 = cv2.inRange(hsv_img, np.array([0, s_lo, v_lo]),
                             np.array([h_hi - 180, s_hi, v_hi]))
            mask = cv2.bitwise_or(m1, m2)
        else:
            mask = cv2.inRange(hsv_img, np.array([h_lo, s_lo, v_lo]),
                               np.array([h_hi, s_hi, v_hi]))

    # Bersihkan noise kecil dan tutup lubang kecil
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    return mask


def find_object(mask):
    """Cari kontur terbesar. Return (kontur, bbox, pusat) atau None."""
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    best = max(contours, key=cv2.contourArea)
    if cv2.contourArea(best) < MIN_AREA:
        return None
    x, y, w, h = cv2.boundingRect(best)
    m = cv2.moments(best)
    if m["m00"] == 0:
        return None
    center = (int(m["m10"] / m["m00"]), int(m["m01"] / m["m00"]))
    return best, (x, y, w, h), center


def draw_info_panel(img, rgb, hex_code, hsv, name, status, scale):
    """Gambar panel info warna (versi diperkecil) pada img, untuk screenshot."""
    r, g, b = rgb
    hh, ss, vv = hsv

    def sc(v):
        return int(round(v * scale))

    font = cv2.FONT_HERSHEY_SIMPLEX
    fs = 0.7 * scale
    th = max(1, int(round(2 * scale)))

    cv2.rectangle(img, (sc(10), sc(10)), (sc(400), sc(185)), (0, 0, 0), -1)
    cv2.rectangle(img, (sc(20), sc(20)), (sc(80), sc(80)), (b, g, r), -1)
    cv2.putText(img, f"R:{r} G:{g} B:{b}", (sc(95), sc(40)), font, fs, (255, 255, 255), th)
    cv2.putText(img, f"HEX: {hex_code}", (sc(95), sc(70)), font, fs, (255, 255, 255), th)
    cv2.putText(img, f"HSV: {hh},{ss},{vv}", (sc(20), sc(105)), font, fs, (255, 255, 255), th)
    cv2.putText(img, f"Warna: {name}", (sc(20), sc(135)), font, fs, (255, 255, 255), th)
    cv2.putText(img, f"Mode: {status}", (sc(20), sc(165)), font, fs, (0, 255, 255), th)


def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Webcam tidak bisa dibuka.")
        return

    if LOCK_CAMERA:
        # Tidak semua webcam mendukung ini; abaikan jika tidak berpengaruh
        cap.set(cv2.CAP_PROP_AUTO_WB, 0)
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)

    gains = np.ones(3)    # faktor koreksi per kanal (urutan BGR)
    smooth = None         # nilai BGR yang sudah dihaluskan
    target = None         # warna target HSV (h, s, v); None = tidak melacak
    trail = deque(maxlen=TRAIL_LEN)
    click = {"pos": None}
    mask_visible = False

    def on_mouse(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            click["pos"] = (x, y)

    cv2.namedWindow(WINDOW)
    cv2.setMouseCallback(WINDOW, on_mouse)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Gagal membaca frame.")
            break

        frame = cv2.flip(frame, 1)
        h_f, w_f = frame.shape[:2]
        cx, cy = w_f // 2, h_f // 2
        x1, y1, x2, y2 = cx - ROI_SIZE, cy - ROI_SIZE, cx + ROI_SIZE, cy + ROI_SIZE

        # Frame yang sudah dikoreksi white balance (dipakai untuk HSV dan pelacakan)
        corrected_frame = np.clip(frame * gains, 0, 255).astype(np.uint8)

        shot = None  # salinan frame bersih untuk screenshot (diisi saat tekan 's')

        key = cv2.waitKey(1) & 0xFF
        if key == ord("c"):
            # Anggap kotak tengah = putih; hitung faktor koreksi per kanal
            raw_center = np.median(frame[y1:y2, x1:x2].reshape(-1, 3), axis=0)
            gains = 255.0 / np.maximum(raw_center, 1.0)
            smooth = None
            trail.clear()
            print("Kalibrasi putih disimpan.")
            corrected_frame = np.clip(frame * gains, 0, 255).astype(np.uint8)
        elif key == ord("r"):
            gains = np.ones(3)
            smooth = None
            trail.clear()
            print("Kalibrasi direset.")
            corrected_frame = frame.copy()
        elif key == ord("t"):
            target = median_hsv(corrected_frame[y1:y2, x1:x2])
            smooth = None
            trail.clear()
            print(f"Target dikunci dari kotak tengah: HSV {target}")
        elif key == ord("x"):
            target = None
            smooth = None
            trail.clear()
            print("Pelacakan dihentikan.")
        elif key == ord("s"):
            shot = frame.copy()  # disimpan setelah info warna dihitung (di bawah)
        elif key == ord("q"):
            break

        # Klik mouse: kunci warna di titik yang diklik
        if click["pos"] is not None:
            px, py = click["pos"]
            click["pos"] = None
            xa, xb = max(px - CLICK_PATCH, 0), min(px + CLICK_PATCH + 1, w_f)
            ya, yb = max(py - CLICK_PATCH, 0), min(py + CLICK_PATCH + 1, h_f)
            target = median_hsv(corrected_frame[ya:yb, xa:xb])
            smooth = None
            trail.clear()
            print(f"Target dikunci dari klik ({px},{py}): HSV {target}")

        # --- Pelacakan objek ---
        found = None
        mask = None
        if target is not None:
            hsv_img = cv2.cvtColor(corrected_frame, cv2.COLOR_BGR2HSV)
            mask = build_mask(hsv_img, target)
            found = find_object(mask)

        if found is not None:
            contour, (bx, by, bw, bh), center = found
            trail.append(center)
            # Ambil warna hanya dari piksel di dalam kontur objek
            obj_mask = np.zeros((h_f, w_f), np.uint8)
            cv2.drawContours(obj_mask, [contour], -1, 255, -1)
            raw = np.median(corrected_frame[obj_mask > 0], axis=0)
            box = (bx, by, bx + bw, by + bh)
            status = "Melacak objek"
        else:
            # ROI tetap di tengah (atau objek hilang saat sedang melacak)
            raw = np.median(corrected_frame[y1:y2, x1:x2].reshape(-1, 3), axis=0)
            box = (x1, y1, x2, y2)
            status = "Objek hilang" if target is not None else "ROI tetap"

        smooth = raw if smooth is None else (
            SMOOTHING * smooth + (1 - SMOOTHING) * raw)

        b, g, r = [int(round(x)) for x in smooth]
        hex_code = "#{:02X}{:02X}{:02X}".format(r, g, b)
        hsv = cv2.cvtColor(np.uint8([[[b, g, r]]]), cv2.COLOR_BGR2HSV)[0][0]
        hh, ss, vv = int(hsv[0]), int(hsv[1]), int(hsv[2])
        name = name_from_hsv(hh, ss, vv)

        # --- Gambar ---
        if found is not None:
            # Kotak tengah diredupkan supaya tidak membingungkan saat melacak
            cv2.rectangle(frame, (x1, y1), (x2, y2), (120, 120, 120), 1)
            for i in range(1, len(trail)):
                thickness = max(1, int(np.sqrt(TRAIL_LEN / float(i + 1)) * 2))
                cv2.line(frame, trail[i - 1], trail[i], (0, 255, 255), thickness)
            cv2.circle(frame, trail[-1], 5, (0, 0, 255), -1)
            cv2.rectangle(frame, box[:2], box[2:], (0, 255, 0), 2)
        else:
            cv2.rectangle(frame, box[:2], box[2:], (255, 255, 255), 2)

        # Simpan screenshot: frame + kotak objek + panel info versi kecil
        if shot is not None:
            shot = frame.copy()
            draw_info_panel(shot, (r, g, b), hex_code, (hh, ss, vv), name, status,
                            SAVE_PANEL_SCALE)
            cv2.imwrite("hasil_deteksi.png", shot)
            print("Screenshot disimpan: hasil_deteksi.png")

        cv2.rectangle(frame, (10, 10), (400, 185), (0, 0, 0), -1)
        cv2.rectangle(frame, (20, 20), (80, 80), (b, g, r), -1)
        cv2.putText(frame, f"R:{r} G:{g} B:{b}", (95, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, f"HEX: {hex_code}", (95, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, f"HSV: {hh},{ss},{vv}", (20, 105),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, f"Warna: {name}", (20, 135),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, f"Mode: {status}", (20, 165),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        cv2.imshow(WINDOW, frame)

        # Jendela mask hanya tampil saat melacak
        if mask is not None:
            cv2.imshow(MASK_WINDOW, mask)
            mask_visible = True
        elif mask_visible:
            try:
                cv2.destroyWindow(MASK_WINDOW)
            except cv2.error:
                pass
            mask_visible = False

    cap.release()
    cv2.destroyAllWindows()
    for _ in range(5):
        cv2.waitKey(1)


if __name__ == "__main__":
    main()
