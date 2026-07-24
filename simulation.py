"""
탄소 배출과 지구온난화 — Pygame UI 껍데기
디자인 기획서 기반: 사이드바 / 2x2 메인 / 하단 타임라인
"""


from __future__ import annotations


import math
import os
import random
import sys


import pygame


# ── 해상도 & 레이아웃 ──────────────────────────────────────────
WIDTH, HEIGHT = 1280, 720
SIDEBAR_W = 280
TIMELINE_H = 72
MAIN_X = SIDEBAR_W
MAIN_W = WIDTH - SIDEBAR_W
MAIN_H = HEIGHT - TIMELINE_H
PANEL_W = MAIN_W // 2
PANEL_H = MAIN_H // 2


YEAR_MIN, YEAR_MAX = 1850, 2100


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(BASE_DIR, "img")


# ── 색상 ──────────────────────────────────────────────────────
BG = (18, 24, 32)
SIDEBAR_BG = (28, 36, 48)
PANEL_BG = (24, 32, 44)
PANEL_BORDER = (160, 170, 180)
TEXT = (230, 235, 240)
MUTED = (140, 150, 165)
ACCENT = (70, 160, 200)


SCENARIO_COLORS = {
    "ssp126": (60, 180, 120),   # 친환경
    "ssp245": (220, 170, 60),   # 중도
    "ssp585": (210, 70, 60),    # 화석연료
}


SCENARIOS = [
    {"id": "ssp126", "label": "SSP1-2.6", "sub": "친환경 경로"},
    {"id": "ssp245", "label": "SSP2-4.5", "sub": "중도 경로"},
    {"id": "ssp585", "label": "SSP5-8.5", "sub": "화석연료 중심"},
]




def year_progress(year: float) -> float:
    """1850→0.0, 2100→1.0"""
    return (year - YEAR_MIN) / (YEAR_MAX - YEAR_MIN)




def scenario_delta_t(scenario_id: str, progress: float) -> float:
    """
    껍데기용 단순 온도 상승량(°C, 1850 대비 근사).
    이후 IPCC 실데이터로 교체 가능.
    """
    curves = {
        "ssp126": 1.8,   # ~+1.8°C
        "ssp245": 2.7,   # ~+2.7°C
        "ssp585": 4.4,   # ~+4.4°C
    }
    peak = curves.get(scenario_id, 2.7)
    # 초반 완만, 후반 가속 (SSP5는 더 가파름)
    power = 1.4 if scenario_id == "ssp585" else 1.15
    return peak * (progress ** power)




def lerp_color(c1, c2, t: float):
    t = max(0.0, min(1.0, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))




def earth_color(delta_t: float):
    """푸른색 → 노랑 → 빨강 보간 (0~4.5°C 기준)"""
    t = min(delta_t / 4.5, 1.0)
    cold = (40, 120, 200)
    warm = (230, 200, 50)
    hot = (200, 40, 30)
    if t < 0.5:
        return lerp_color(cold, warm, t * 2)
    return lerp_color(warm, hot, (t - 0.5) * 2)




def load_keyed_image(path: str) -> pygame.Surface:
    """검은 배경을 투명 처리해 로드."""
    img = pygame.image.load(path).convert()
    img.set_colorkey((0, 0, 0))
    return img




def scale_keep_aspect(surf: pygame.Surface, target_h: int) -> pygame.Surface:
    w, h = surf.get_size()
    scale = target_h / h
    new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
    return pygame.transform.smoothscale(surf, new_size)




class Spark:
    """기존 원형 불꽃 파티클 (느낌 유지)."""


    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = random.uniform(-1.2, 1.2)
        self.vy = random.uniform(-3.5, -1.0)
        self.life = random.uniform(0.4, 1.0)
        self.size = random.randint(2, 5)
        self.color = random.choice([
            (255, 140, 40),
            (255, 80, 30),
            (255, 200, 60),
        ])


    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.08
        self.life -= 0.02
        return self.life > 0


    def draw(self, surface):
        alpha = max(0, min(255, int(self.life * 255)))
        s = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha), (self.size, self.size), self.size)
        surface.blit(s, (int(self.x - self.size), int(self.y - self.size)))




class FireEffect:
    """
    불꽃 스프라이트 애니메이션.
    set 0: f1~f5 / set 1: f6~f10 을 1→5 프레임으로 순환.
    """


    FRAME_DT = 0.09  # 프레임당 초


    def __init__(self, x: float, y: float, set_id: int, scale: float, framesets: list):
        self.x = x
        self.y = y  # 이펙트 하단(불꽃 뿌리) 기준
        self.set_id = set_id
        self.frames = framesets[set_id]
        self.frame = 0
        self.timer = random.uniform(0, self.FRAME_DT)
        self.scale = scale
        self.life = random.uniform(2.5, 5.0)
        self._scaled: list[pygame.Surface] | None = None


    def _get_frames(self) -> list[pygame.Surface]:
        if self._scaled is None:
            h = max(40, int(120 * self.scale))
            self._scaled = [scale_keep_aspect(f, h) for f in self.frames]
        return self._scaled


    def update(self, dt: float) -> bool:
        self.timer += dt
        while self.timer >= self.FRAME_DT:
            self.timer -= self.FRAME_DT
            self.frame = (self.frame + 1) % len(self.frames)
        self.life -= dt
        return self.life > 0


    def draw(self, surface: pygame.Surface):
        frames = self._get_frames()
        img = frames[self.frame]
        # 하단 정렬: 불꽃 뿌리를 (x, y)에 맞춤
        rect = img.get_rect(midbottom=(int(self.x), int(self.y)))
        surface.blit(img, rect)




class Simulation:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("탄소 배출과 지구온난화 — 기후 시뮬레이션")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("malgun gothic", 18)
        self.font_sm = pygame.font.SysFont("malgun gothic", 14)
        self.font_lg = pygame.font.SysFont("malgun gothic", 22, bold=True)
        self.font_title = pygame.font.SysFont("malgun gothic", 16, bold=True)


        self.scenario = "ssp245"
        self.year = float(YEAR_MIN)
        self.playing = False
        self.dragging = False
        self.sparks: list[Spark] = []
        self.fire_effects: list[FireEffect] = []


        # 버튼 / 슬라이더 rect (매 프레임 갱신)
        self.scenario_btns: list[tuple[pygame.Rect, str]] = []
        self.slider_track = pygame.Rect(0, 0, 0, 0)
        self.slider_handle = pygame.Rect(0, 0, 0, 0)
        self.play_btn = pygame.Rect(0, 0, 0, 0)


        # 그래프 히스토리 (시나리오별)
        self.graph_points: dict[str, list[tuple[float, float]]] = {
            s["id"]: [] for s in SCENARIOS
        }


        self._load_assets()
        self.trees: list[dict] = []  # 패널 기준 나무 배치 (최초 그리기 때 생성)


    def _load_assets(self):
        # 나무 t1(어린) / t2(중간) / t3(큰)
        self.tree_imgs = [
            load_keyed_image(os.path.join(IMG_DIR, f"t{i}.png"))
            for i in (1, 2, 3)
        ]
        # 불꽃 세트1: f1~f5 / 세트2: f6~f10
        set_a = [
            load_keyed_image(os.path.join(IMG_DIR, f"f{i}.png"))
            for i in range(1, 6)
        ]
        set_b = [
            load_keyed_image(os.path.join(IMG_DIR, f"f{i}.png"))
            for i in range(6, 11)
        ]
        self.fire_framesets = [set_a, set_b]


    def _ensure_trees(self, ground: pygame.Rect):
        """바닥에 맞춰 9그루 골고루 배치 (겹침 허용). 온도↑ 시 최대 4그루까지 감소."""
        if self.trees:
            return


        # (타입인덱스, 표시높이) — 어린/중간/큰 섞어 9그루
        specs = [
            (0, 105),  # t1 어린
            (1, 145),  # t2 중간
            (2, 185),  # t3 큰
            (0, 95),
            (1, 140),
            (2, 170),
            (0, 110),
            (1, 135),
            (2, 160),
        ]
        n = len(specs)
        margin = 24
        usable = ground.width - margin * 2
        for i, (kind, th) in enumerate(specs):
            frac = (i + 0.5) / n
            jitter = random.randint(-14, 14)
            cx = ground.left + margin + int(frac * usable) + jitter
            ground_y = ground.bottom - 10
            img = scale_keep_aspect(self.tree_imgs[kind], th)
            self.trees.append({
                "img": img,
                "cx": cx,
                "ground_y": ground_y,
                "kind": kind,
            })


        # 큰 나무부터 그려 작은 나무가 앞에 오도록
        self.trees.sort(key=lambda t: -t["img"].get_height())
        # 소실 순서: 어린 나무·가장자리부터 먼저 사라지도록
        burn_order = sorted(
            range(len(self.trees)),
            key=lambda i: (self.trees[i]["kind"], abs(self.trees[i]["cx"] - ground.centerx)),
        )
        for rank, idx in enumerate(burn_order):
            self.trees[idx]["burn_rank"] = rank  # 0이 가장 먼저 소실


    def _tree_alpha(self, burn_rank: int, danger: float) -> float:
        """
        온도↑에 따라 burn_rank 낮은 나무부터 소실.
        9그루 → 최고온에서 4그루. 소실 중인 나무는 페이드아웃.
        """
        burned = danger * 5.0  # 0~5그루 분량 소실
        if burn_rank < math.floor(burned):
            return 0.0  # 이미 소실
        if burn_rank == math.floor(burned) and burned < 5:
            return 1.0 - (burned - math.floor(burned))  # 소실 중
        return 1.0


    def _tint_tree(self, img: pygame.Surface, danger: float, alpha: float = 1.0) -> pygame.Surface:
        """온도↑ → 붉고 어두운 틴트 + 알파."""
        out = img.copy()
        r = int(255 - danger * 40)
        g = int(255 - danger * 130)
        b = int(255 - danger * 160)
        tint = pygame.Surface(out.get_size())
        tint.fill((max(80, r), max(40, g), max(30, b)))
        out.blit(tint, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        if alpha < 0.99:
            out.set_alpha(int(255 * alpha))
        return out


    # ── 레이아웃 helpers ──────────────────────────────────────
    def panel_rect(self, col: int, row: int) -> pygame.Rect:
        pad = 8
        x = MAIN_X + col * PANEL_W + pad
        y = row * PANEL_H + pad
        w = PANEL_W - pad * 2
        h = PANEL_H - pad * 2
        return pygame.Rect(x, y, w, h)


    def _fire_ground(self) -> pygame.Rect:
        rect = self.panel_rect(1, 1)
        ground = rect.inflate(-24, -40)
        ground.top += 16
        return ground


    # ── 이벤트 ────────────────────────────────────────────────
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return False


            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._on_click(event.pos)
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.dragging = False
            if event.type == pygame.MOUSEMOTION and self.dragging:
                self._set_year_from_x(event.pos[0])
        return True


    def _on_click(self, pos):
        for rect, sid in self.scenario_btns:
            if rect.collidepoint(pos):
                self.scenario = sid
                return
        if self.play_btn.collidepoint(pos):
            self.playing = not self.playing
            return
        if self.slider_track.inflate(0, 20).collidepoint(pos) or self.slider_handle.collidepoint(pos):
            self.dragging = True
            self.playing = False
            self._set_year_from_x(pos[0])


    def _set_year_from_x(self, mx: int):
        t = (mx - self.slider_track.left) / max(1, self.slider_track.width)
        t = max(0.0, min(1.0, t))
        self.year = YEAR_MIN + t * (YEAR_MAX - YEAR_MIN)


    # ── 업데이트 ──────────────────────────────────────────────
    def update(self, dt: float):
        if self.playing and not self.dragging:
            # 약 40초에 1850→2100
            self.year += (YEAR_MAX - YEAR_MIN) / 40.0 * dt
            if self.year >= YEAR_MAX:
                self.year = float(YEAR_MAX)
                self.playing = False


        progress = year_progress(self.year)
        delta_t = scenario_delta_t(self.scenario, progress)


        # 그래프 포인트 누적 (연도 증가 시에만)
        pts = self.graph_points[self.scenario]
        if not pts or self.year > pts[-1][0] + 0.5:
            pts.append((self.year, delta_t))
            if len(pts) > 400:
                self.graph_points[self.scenario] = pts[-400:]


        # 산불: 원형 스파크 + 스프라이트 이펙트
        fire_intensity = max(0.0, (delta_t - 1.0) / 3.5)  # 1°C 넘으면 시작
        ground = self._fire_ground()


        # 원형 스파크 (기존 느낌 유지)
        spawn_n = int(fire_intensity * 4)
        if fire_intensity > 0.05 and random.random() < fire_intensity:
            for _ in range(max(1, spawn_n)):
                sx = random.randint(ground.left + 20, ground.right - 20)
                sy = ground.bottom - 40
                self.sparks.append(Spark(sx, sy))


        self.sparks = [s for s in self.sparks if s.update()]


        # 스프라이트 불꽃: 목표 개수 = 온도에 비례 (위·아래 골고루)
        target_fx = int(fire_intensity * 14)  # 최대 ~14개
        if fire_intensity > 0.08 and len(self.fire_effects) < target_fx:
            need = min(2, target_fx - len(self.fire_effects))
            for _ in range(need):
                self._spawn_fire_effect(ground, fire_intensity)


        self.fire_effects = [fx for fx in self.fire_effects if fx.update(dt)]
        # 온도가 떨어지면 초과분 수명 단축
        if len(self.fire_effects) > target_fx:
            for fx in self.fire_effects[target_fx:]:
                fx.life = min(fx.life, 0.4)


    def _spawn_fire_effect(self, ground: pygame.Rect, intensity: float):
        """화면 위·아래에 불꽃 이펙트를 섞어 스폰."""
        set_id = random.choice([0, 1])  # f1~5 / f6~10 섞기
        x = random.randint(ground.left + 16, ground.right - 16)
        # 위쪽(수관) / 아래쪽(지면) 반반
        if random.random() < 0.5:
            # 위: 패널 상단~중상단
            y = random.randint(ground.top + 70, ground.centery + 10)
        else:
            # 아래: 지면 근처 (불꽃 하단 = 바닥)
            y = random.randint(ground.bottom - 50, ground.bottom - 8)
        scale = random.uniform(0.55, 0.85 + intensity * 0.4)
        self.fire_effects.append(
            FireEffect(x, y, set_id, scale, self.fire_framesets)
        )


    # ── 그리기 ────────────────────────────────────────────────
    def draw(self):
        self.screen.fill(BG)
        self._draw_sidebar()
        self._draw_graph_panel()
        self._draw_earth_panel()
        self._draw_ice_panel()
        self._draw_fire_panel()
        self._draw_timeline()
        pygame.display.flip()


    def _draw_sidebar(self):
        pygame.draw.rect(self.screen, SIDEBAR_BG, (0, 0, SIDEBAR_W, HEIGHT))
        pygame.draw.line(self.screen, (50, 60, 75), (SIDEBAR_W - 1, 0), (SIDEBAR_W - 1, HEIGHT), 2)


        title = self.font_lg.render("시나리오 선택", True, TEXT)
        self.screen.blit(title, (24, 28))
        hint = self.font_sm.render("IPCC SSP 경로", True, MUTED)
        self.screen.blit(hint, (24, 58))


        self.scenario_btns = []
        start_y = 110
        gap = 100


        for i, sc in enumerate(SCENARIOS):
            cy = start_y + i * gap
            color = SCENARIO_COLORS[sc["id"]]
            selected = self.scenario == sc["id"]


            # 원형 버튼
            radius = 28 if selected else 24
            cx, cy_btn = 56, cy + 20
            if selected:
                pygame.draw.circle(self.screen, (*color, ), (cx, cy_btn), radius + 6, 3)
            pygame.draw.circle(self.screen, color, (cx, cy_btn), radius)
            pygame.draw.circle(self.screen, (255, 255, 255) if selected else (40, 48, 60), (cx, cy_btn), radius, 2)


            # 라벨
            label = self.font_title.render(sc["label"], True, TEXT if selected else MUTED)
            sub = self.font_sm.render(sc["sub"], True, color if selected else MUTED)
            self.screen.blit(label, (100, cy + 6))
            self.screen.blit(sub, (100, cy + 30))


            hit = pygame.Rect(16, cy - 10, SIDEBAR_W - 32, 70)
            self.scenario_btns.append((hit, sc["id"]))
            if selected:
                pygame.draw.rect(self.screen, (*color, ), hit, 1, border_radius=8)


        # 현재 상태 요약
        progress = year_progress(self.year)
        delta_t = scenario_delta_t(self.scenario, progress)
        y_info = HEIGHT - 140
        pygame.draw.line(self.screen, (50, 60, 75), (20, y_info), (SIDEBAR_W - 20, y_info), 1)
        info_lines = [
            f"연도  {int(self.year)}",
            f"ΔT    +{delta_t:.2f} °C",
            f"진행  {progress * 100:.0f}%",
        ]
        for j, line in enumerate(info_lines):
            surf = self.font.render(line, True, TEXT)
            self.screen.blit(surf, (24, y_info + 16 + j * 28))


    def _draw_panel_frame(self, rect: pygame.Rect, title: str):
        pygame.draw.rect(self.screen, PANEL_BG, rect, border_radius=6)
        pygame.draw.rect(self.screen, PANEL_BORDER, rect, 1, border_radius=6)
        t = self.font_sm.render(title, True, MUTED)
        self.screen.blit(t, (rect.left + 12, rect.top + 8))


    def _draw_graph_panel(self):
        rect = self.panel_rect(0, 0)
        self._draw_panel_frame(rect, "통계 대시보드 — 온도 상승 (°C)")


        plot = rect.inflate(-36, -48)
        plot.top += 12
        pygame.draw.rect(self.screen, (20, 26, 36), plot)
        pygame.draw.rect(self.screen, (70, 80, 95), plot, 1)


        # 축
        pygame.draw.line(self.screen, MUTED, (plot.left, plot.bottom), (plot.right, plot.bottom), 1)
        pygame.draw.line(self.screen, MUTED, (plot.left, plot.top), (plot.left, plot.bottom), 1)


        # Y 눈금 0~5
        for v in range(0, 6):
            yy = plot.bottom - int((v / 5.0) * plot.height)
            pygame.draw.line(self.screen, (45, 55, 70), (plot.left, yy), (plot.right, yy), 1)
            lbl = self.font_sm.render(str(v), True, MUTED)
            self.screen.blit(lbl, (plot.left - 18, yy - 7))


        # X 라벨
        for yr, label in [(1850, "1850"), (1975, "1975"), (2100, "2100")]:
            xx = plot.left + int(year_progress(yr) * plot.width)
            lbl = self.font_sm.render(label, True, MUTED)
            self.screen.blit(lbl, (xx - 14, plot.bottom + 4))


        # 현재 시나리오 곡선 (전체 경로 미리보기 + 진행분)
        color = SCENARIO_COLORS[self.scenario]
        preview = []
        for i in range(0, 101):
            p = i / 100.0
            y = YEAR_MIN + p * (YEAR_MAX - YEAR_MIN)
            dt = scenario_delta_t(self.scenario, p)
            px = plot.left + int(p * plot.width)
            py = plot.bottom - int(min(dt / 5.0, 1.0) * plot.height)
            preview.append((px, py))
        if len(preview) >= 2:
            # 아직 안 간 구간은 흐리게
            prog = year_progress(self.year)
            cut = max(2, int(prog * len(preview)))
            if cut < len(preview):
                faint = tuple(c // 3 for c in color)
                pygame.draw.lines(self.screen, faint, False, preview[cut - 1 :], 1)
            pygame.draw.lines(self.screen, color, False, preview[:cut], 2)


        # 현재 위치 점
        dt = scenario_delta_t(self.scenario, year_progress(self.year))
        cx = plot.left + int(year_progress(self.year) * plot.width)
        cy = plot.bottom - int(min(dt / 5.0, 1.0) * plot.height)
        pygame.draw.circle(self.screen, color, (cx, cy), 5)
        pygame.draw.circle(self.screen, TEXT, (cx, cy), 5, 1)


    def _draw_earth_panel(self):
        rect = self.panel_rect(1, 0)
        self._draw_panel_frame(rect, "지구 온도 시각화")


        progress = year_progress(self.year)
        delta_t = scenario_delta_t(self.scenario, progress)
        color = earth_color(delta_t)


        cx, cy = rect.centerx, rect.centery + 8
        r = min(rect.w, rect.h) // 2 - 36


        # 대기권 글로우
        glow = lerp_color(color, (255, 255, 255), 0.3)
        pygame.draw.circle(self.screen, glow, (cx, cy), r + 8, 3)
        pygame.draw.circle(self.screen, color, (cx, cy), r)


        # 단순 대륙선
        land = lerp_color(color, (30, 90, 50), 0.35)
        for angle in (20, 80, 150, 220, 300):
            rad = math.radians(angle)
            lx = cx + int(math.cos(rad) * r * 0.35)
            ly = cy + int(math.sin(rad) * r * 0.4)
            pygame.draw.ellipse(self.screen, land, (lx - 18, ly - 10, 36, 20))


        # 온도 라벨
        label = self.font.render(f"+{delta_t:.2f} °C", True, TEXT)
        self.screen.blit(label, (rect.centerx - label.get_width() // 2, rect.bottom - 32))


    def _draw_ice_panel(self):
        rect = self.panel_rect(0, 1)
        self._draw_panel_frame(rect, "빙하 · 해수면 변화")


        progress = year_progress(self.year)
        delta_t = scenario_delta_t(self.scenario, progress)
        # 빙하 축소율: 온도에 비례 (0°C→거의 풀, 4.5°C→매우 작음)
        melt = min(delta_t / 4.5, 1.0)
        ice_scale = 1.0 - melt * 0.75  # 최대 75% 축소


        ocean = rect.inflate(-24, -40)
        ocean.top += 16
        pygame.draw.rect(self.screen, (20, 70, 130), ocean, border_radius=4)


        # 빙하 다각형 (하단 중심에서 위로 솟은 형태, 축소)
        cx = ocean.centerx
        base_y = ocean.bottom
        top_y = ocean.top + int(ocean.height * 0.15)
        half_w = int(ocean.width * 0.42 * ice_scale)
        peak_h = int((base_y - top_y) * ice_scale)


        ice = [
            (cx - half_w, base_y - 4),
            (cx - half_w * 0.55, base_y - int(peak_h * 0.55)),
            (cx - half_w * 0.2, base_y - int(peak_h * 0.85)),
            (cx, base_y - peak_h),
            (cx + half_w * 0.25, base_y - int(peak_h * 0.8)),
            (cx + half_w * 0.6, base_y - int(peak_h * 0.5)),
            (cx + half_w, base_y - 4),
        ]
        pygame.draw.polygon(self.screen, (220, 240, 255), ice)
        pygame.draw.polygon(self.screen, (160, 200, 230), ice, 2)


        # 해수면 라인 (온도↑ → 살짝 상승)
        sea_rise = int(melt * 18)
        sea_y = ocean.bottom - 8 - sea_rise
        pygame.draw.line(self.screen, (80, 160, 220), (ocean.left, sea_y), (ocean.right, sea_y), 2)


        note = self.font_sm.render(f"빙하 면적 {ice_scale * 100:.0f}%", True, TEXT)
        self.screen.blit(note, (rect.left + 14, rect.bottom - 28))


    def _draw_fire_panel(self):
        rect = self.panel_rect(1, 1)
        self._draw_panel_frame(rect, "산불 위험도")


        ground = self._fire_ground()
        progress = year_progress(self.year)
        delta_t = scenario_delta_t(self.scenario, progress)
        danger = max(0.0, min(1.0, (delta_t - 0.8) / 3.5))


        # 온도↑ → 숲 배경도 어둡고 붉게
        bg = lerp_color((28, 48, 32), (36, 22, 18), danger)
        soil_c = lerp_color((42, 58, 36), (48, 28, 22), danger)
        pygame.draw.rect(self.screen, bg, ground, border_radius=4)
        soil = pygame.Rect(ground.left, ground.bottom - 14, ground.width, 14)
        pygame.draw.rect(self.screen, soil_c, soil)


        self._ensure_trees(ground)


        prev_clip = self.screen.get_clip()
        self.screen.set_clip(ground)


        # 나무: 하단=바닥, burn_rank 낮은 것부터 소실 (9→4)
        for tree in self.trees:
            alpha = self._tree_alpha(tree["burn_rank"], danger)
            if alpha < 0.05:
                continue
            img = self._tint_tree(tree["img"], danger, alpha)
            dest = img.get_rect(midbottom=(tree["cx"], tree["ground_y"]))
            self.screen.blit(img, dest)


        for fx in self.fire_effects:
            fx.draw(self.screen)


        for spark in self.sparks:
            spark.draw(self.screen)


        # 분위기 필터: 붉고 어두운 오버레이
        if danger > 0.02:
            haze = pygame.Surface(ground.size, pygame.SRCALPHA)
            haze.fill((90, 18, 8, int(danger * 70)))
            glow_a = int(danger * 45)
            half_h = max(1, ground.height // 2)
            for i in range(0, half_h, 4):
                a = int(glow_a * (1.0 - i / half_h))
                if a <= 0:
                    break
                pygame.draw.rect(haze, (180, 50, 20, a), (0, i, ground.width, 4))
            self.screen.blit(haze, ground.topleft)


        self.screen.set_clip(prev_clip)


        bar = pygame.Rect(rect.left + 14, rect.bottom - 28, rect.width - 28, 10)
        pygame.draw.rect(self.screen, (40, 50, 60), bar, border_radius=3)
        fill_w = int(bar.width * danger)
        if fill_w > 0:
            fill_color = lerp_color((60, 180, 80), (220, 50, 30), danger)
            pygame.draw.rect(self.screen, fill_color, (bar.left, bar.top, fill_w, bar.height), border_radius=3)


    def _draw_timeline(self):
        y0 = MAIN_H
        pygame.draw.rect(self.screen, SIDEBAR_BG, (MAIN_X, y0, MAIN_W, TIMELINE_H))
        pygame.draw.line(self.screen, (50, 60, 75), (MAIN_X, y0), (WIDTH, y0), 1)


        # 재생 버튼
        self.play_btn = pygame.Rect(MAIN_X + 16, y0 + 18, 44, 36)
        pygame.draw.rect(self.screen, ACCENT if self.playing else (50, 70, 90), self.play_btn, border_radius=6)
        if self.playing:
            # pause
            pygame.draw.rect(self.screen, TEXT, (self.play_btn.x + 12, self.play_btn.y + 8, 6, 20))
            pygame.draw.rect(self.screen, TEXT, (self.play_btn.x + 26, self.play_btn.y + 8, 6, 20))
        else:
            # play triangle
            pts = [
                (self.play_btn.x + 16, self.play_btn.y + 8),
                (self.play_btn.x + 16, self.play_btn.y + 28),
                (self.play_btn.x + 34, self.play_btn.y + 18),
            ]
            pygame.draw.polygon(self.screen, TEXT, pts)


        # 슬라이더 트랙
        track_left = MAIN_X + 80
        track_right = WIDTH - 120
        track_y = y0 + 34
        self.slider_track = pygame.Rect(track_left, track_y - 3, track_right - track_left, 6)
        pygame.draw.rect(self.screen, (50, 60, 75), self.slider_track, border_radius=3)


        # 채움
        prog = year_progress(self.year)
        fill_w = int(self.slider_track.width * prog)
        if fill_w > 0:
            pygame.draw.rect(
                self.screen,
                SCENARIO_COLORS[self.scenario],
                (self.slider_track.left, self.slider_track.top, fill_w, self.slider_track.height),
                border_radius=3,
            )


        # 핸들
        hx = self.slider_track.left + fill_w
        self.slider_handle = pygame.Rect(hx - 9, track_y - 12, 18, 24)
        pygame.draw.rect(self.screen, TEXT, self.slider_handle, border_radius=4)
        pygame.draw.rect(self.screen, SCENARIO_COLORS[self.scenario], self.slider_handle, 2, border_radius=4)


        # 연도 라벨
        year_label = self.font_lg.render(str(int(self.year)), True, TEXT)
        self.screen.blit(year_label, (WIDTH - 100, y0 + 22))


        # 눈금
        for yr in (1850, 1900, 1950, 2000, 2050, 2100):
            p = year_progress(yr)
            xx = self.slider_track.left + int(p * self.slider_track.width)
            pygame.draw.line(self.screen, MUTED, (xx, track_y + 8), (xx, track_y + 14), 1)
            if yr in (1850, 2100):
                lbl = self.font_sm.render(str(yr), True, MUTED)
                self.screen.blit(lbl, (xx - 14, track_y + 16))


    def run(self):
        running = True
        while running:
            dt = self.clock.tick(60) / 1000.0
            running = self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()
        sys.exit(0)




if __name__ == "__main__":
    Simulation().run()




