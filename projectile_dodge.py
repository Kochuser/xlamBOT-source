"""Screen-space projectile tracking and short-horizon collision avoidance.

Only small red/pink moving components are supported. Uncertain camera motion,
ambiguous associations and missing frames discard tracks rather than guessing.
"""

import math
import cv2
import numpy as np

CAMERA_SIZE = (160, 90)


def reduced_frame(frame):
    h, w = frame.shape[:2]
    scale = min(1.0, 640 / w)
    return cv2.resize(
        frame, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_AREA
    )


def components(frame, player, excluded, small=None):
    h, w = frame.shape[:2]
    scale = min(1.0, 640 / w)
    if small is None:
        small = reduced_frame(frame)
    red, green, blue = (small[:, :, channel].astype(np.uint16) for channel in range(3))
    # Conservative RGB dominance avoids a second full-frame color conversion.
    mask = ((red >= 185) & (green * 100 <= red * 43) & (blue * 85 <= red * 100)).astype(
        np.uint8
    )
    sh, sw = mask.shape
    mask[: round(sh * 0.08)] = 0
    mask[round(sh * 0.64) :, round(sw * 0.74) :] = 0
    mask[round(sh * 0.72) :, : round(sw * 0.19)] = 0
    for box in excluded:
        x1, y1, x2, y2 = box[:4]
        # Include names, health bars and character effects in the exclusion.
        mask[
            max(0, round((y1 - 35) * scale)) : min(sh, round((y2 + 10) * scale)),
            max(0, round((x1 - 20) * scale)) : min(sw, round((x2 + 20) * scale)),
        ] = 0
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out = []
    for contour in contours:
        area = cv2.contourArea(contour) / (scale * scale)
        x, y, bw, bh = cv2.boundingRect(contour)
        if (
            not 8 <= area <= 500
            or max(bw, bh) / scale > 65
            or max(bw, bh) > 7 * max(1, min(bw, bh))
        ):
            continue
        moments = cv2.moments(contour)
        px = moments["m10"] / moments["m00"] / scale
        py = moments["m01"] / moments["m00"] / scale
        if math.hypot(px - player[0], py - player[1]) > min(w, h) * 0.55:
            continue
        out.append((float(px), float(py), max(3.0, math.sqrt(area / math.pi))))
    return sorted(out, key=lambda p: math.hypot(p[0] - player[0], p[1] - player[1]))[
        :24
    ]


class ProjectileDodge:
    def __init__(self):
        self.reset()

    def reset(self):
        self.stamp = None
        self.gray = None
        self.tracks = []
        self.threats = []
        self.shape = None
        self.heading = None
        self.heading_at = 0.0
        self.active = False
        self.camera_ok = False

    def observe(self, frame, stamp, player, excluded):
        self.active = False
        self.threats = []
        self.camera_ok = False
        if frame is None or not math.isfinite(stamp):
            self.reset()
            return
        if self.stamp is not None and stamp <= self.stamp:
            return
        h, w = frame.shape[:2]
        if self.shape is not None and self.shape != (h, w):
            self.reset()
        self.shape = (h, w)
        small = reduced_frame(frame)
        gray = cv2.cvtColor(
            cv2.resize(small, CAMERA_SIZE, interpolation=cv2.INTER_AREA),
            cv2.COLOR_RGB2GRAY,
        ).astype(np.float32)
        points = components(frame, player, excluded, small=small)
        dt = stamp - self.stamp if self.stamp is not None else 0
        shift = (0.0, 0.0)
        valid = False
        if self.gray is not None and 0.02 <= dt <= 0.35:
            delta, response = cv2.phaseCorrelate(self.gray, gray)
            shift = (delta[0] * w / CAMERA_SIZE[0], delta[1] * h / CAMERA_SIZE[1])
            valid = (
                response >= 0.45
                and all(math.isfinite(v) for v in shift)
                and math.hypot(*shift) < h * 0.12
            )
        previous = self.tracks if valid else []
        self.camera_ok = valid
        self.gray = gray
        self.stamp = stamp
        tracks = []
        used = set()
        for x, y, radius in points:
            matches = []
            for i, old in enumerate(previous):
                if i in used:
                    continue
                px = old["x"] + shift[0] + old["vx"] * dt
                py = old["y"] + shift[1] + old["vy"] * dt
                distance = math.hypot(x - px, y - py)
                if distance <= max(18.0, 900 * dt) and 0.5 <= radius / old["r"] <= 2:
                    matches.append((distance, i, old))
            track = dict(x=x, y=y, r=radius, vx=0.0, vy=0.0, hits=1)
            if matches:
                matches.sort(key=lambda m: m[0])
                # Crossing shots or a dense effect cluster have no reliable identity.
                if len(matches) == 1 or matches[1][0] - matches[0][0] > 12:
                    _, i, old = matches[0]
                    used.add(i)
                    vx = (x - old["x"] - shift[0]) / dt
                    vy = (y - old["y"] - shift[1]) / dt
                    speed = math.hypot(vx, vy)
                    old_speed = math.hypot(old["vx"], old["vy"])
                    consistent = old["hits"] == 1 or (
                        old_speed > 0
                        and 0.5 < speed / old_speed < 2
                        and (vx * old["vx"] + vy * old["vy"])
                        / (max(speed * old_speed, 1))
                        > 0.85
                    )
                    if 60 <= speed <= 1500 and consistent:
                        track.update(vx=vx, vy=vy, hits=old["hits"] + 1)
            tracks.append(track)
            if track["hits"] >= 3:
                self.threats.append(track)
        self.tracks = tracks
        if not valid:
            self.heading = None

    @staticmethod
    def clearance(shots, player, body, velocity, horizon=0.45):
        best = float("inf")
        for shot in shots:
            dx, dy = shot["x"] - player[0], shot["y"] - player[1]
            vx, vy = shot["vx"] - velocity[0], shot["vy"] - velocity[1]
            squared = vx * vx + vy * vy
            closest = (
                min(horizon, max(0.0, -(dx * vx + dy * vy) / squared))
                if squared > 1e-6
                else 0.0
            )
            best = min(
                best,
                math.hypot(dx + vx * closest, dy + vy * closest) - body - shot["r"],
            )
        return best

    def choose(self, base, player, body, speed, stamp, safe):
        self.active = False
        if (
            not self.threats
            or self.stamp is None
            or not 0 <= stamp - self.stamp <= 0.15
        ):
            self.heading = None
            return base
        norm = math.hypot(*base)
        velocity = tuple(v * speed / norm for v in base) if norm > 0 else (0.0, 0.0)
        age = stamp - self.stamp
        shots = [
            dict(shot, x=shot["x"] + shot["vx"] * age, y=shot["y"] + shot["vy"] * age)
            for shot in self.threats
        ]
        # The unseen player displacement during inference remains uncertain.
        body += speed * age
        baseline = self.clearance(shots, player, body, velocity)
        if baseline > 6:
            return base
        directions = [
            (math.cos(i * math.tau / 24), math.sin(i * math.tau / 24))
            for i in range(24)
        ]
        choices = []
        for direction in directions:
            clearance = self.clearance(
                shots, player, body, tuple(v * speed for v in direction)
            )
            if clearance <= baseline + 5:
                continue
            preference = sum(a * b for a, b in zip(direction, velocity)) / max(speed, 1)
            choices.append((clearance + 2 * preference, clearance, direction))
        # Check geometry only until the best admissible escape is found.
        best = next(
            (
                choice
                for choice in sorted(choices, key=lambda c: c[0], reverse=True)
                if safe(choice[2])
            ),
            None,
        )
        if best is None:
            return base
        _, clearance, direction = best
        if (
            self.heading is not None
            and stamp - self.heading_at < 0.20
            and safe(self.heading)
        ):
            held = self.clearance(
                shots, player, body, tuple(v * speed for v in self.heading)
            )
            if held > baseline + 5 and held >= clearance - 4:
                direction = self.heading
        if direction != self.heading:
            self.heading_at = stamp
        self.heading = direction
        self.active = True
        return tuple(v * max(norm, 1.0) for v in direction)

    def snapshot(self):
        return dict(
            active=self.active,
            tracked=len(self.tracks),
            threats=len(self.threats),
            camera_ok=self.camera_ok,
            shots=[dict(shot) for shot in self.threats[:8]],
        )
