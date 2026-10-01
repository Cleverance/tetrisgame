"""
TETRIS EDUKASI - Dibuat dengan Python & Pygame
================================================
Sebuah implementasi Tetris klasik dengan fitur-fitur modern DAN sentuhan edukasi:
- Ghost piece (bayangan posisi jatuh)
- Hold piece (menyimpan 1 balok untuk dipakai nanti)
- Next piece preview (3 balok berikutnya)
- Sistem 7-bag randomizer (distribusi balok lebih adil, seperti Tetris asli)
- Level & kecepatan yang meningkat seiring skor
- Efek suara sederhana yang dibuat langsung dari kode (tanpa file eksternal)
- High score yang tersimpan otomatis di file lokal
- Pause, restart, dan game over yang rapi

FITUR EDUKASI (BARU):
- Sesekali muncul BALOK SPESIAL bertanda emas berkedip.
- Kalau baris yang mengandung balok spesial berhasil dibersihkan, muncul
  TANTANGAN MATEMATIKA berisi 3 soal sederhana (tambah/kurang/kali).
- Jawab 3 dari 3 benar -> dapat BONUS KEKUATAN acak:
    * Ledakan Papan   : seluruh papan langsung bersih
    * Tukar Bebas     : hold/tukar balok tanpa batas untuk 8 balok ke depan
    * Waktu Melambat  : kecepatan jatuh diperlambat 15 detik
    * Skor Ganda      : semua perolehan skor dikali 2 selama 20 detik
    * Baris Instan    : 2 baris paling bawah langsung dibersihkan
- Jawab 2 dari 3 benar -> tetap dapat bonus skor (usaha belajar dihargai).
- Jawab 0-1 dari 3 benar -> tanpa bonus kekuatan, tapi jawaban yang benar
  tetap ditampilkan supaya pemain belajar dari kesalahannya.

Kontrol:
    Kiri / Kanan   : Menggerakkan balok
    Bawah          : Soft drop (turun lebih cepat, +skor kecil)
    Spasi          : Hard drop (langsung jatuh, +skor lebih besar)
    Panah Atas / X : Putar balok searah jarum jam
    Z              : Putar balok berlawanan arah jarum jam
    C              : Hold (simpan balok)
    P / Esc        : Pause
    R              : Restart (saat game over)
    M              : Mute/unmute suara
    (Saat tantangan matematika muncul, ketik angka + Enter untuk menjawab)
"""

import pygame
import random
import sys
import os
import json
import math

# ============================================================
# KONFIGURASI DASAR
# ============================================================
COLS, ROWS = 10, 20
CELL = 30                      # ukuran satu blok (piksel)
BOARD_X, BOARD_Y = 40, 40      # posisi papan permainan di layar
SIDEBAR_W = 220

WIDTH = BOARD_X * 2 + COLS * CELL + SIDEBAR_W
HEIGHT = BOARD_Y * 2 + ROWS * CELL

FPS = 60
HIGHSCORE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "highscore.json")

# Warna (R, G, B)
BLACK = (18, 18, 24)
DARK = (28, 28, 36)
GRID_LINE = (45, 45, 58)
WHITE = (240, 240, 245)
GRAY = (120, 120, 135)
RED = (231, 76, 60)
GREEN = (90, 210, 120)
GOLD = (255, 215, 0)
GHOST_ALPHA = 60

COLORS = {
    'I': (0, 200, 210),
    'O': (240, 200, 0),
    'T': (170, 80, 220),
    'S': (60, 200, 90),
    'Z': (230, 70, 70),
    'J': (60, 110, 230),
    'L': (240, 140, 30),
}

# Definisi bentuk setiap piece untuk tiap rotasinya.
# Setiap koordinat (row, col) relatif terhadap kotak pembungkus piece.
SHAPES = {
    'I': [
        [(0, 0), (0, 1), (0, 2), (0, 3)],
        [(0, 0), (1, 0), (2, 0), (3, 0)],
    ],
    'O': [
        [(0, 0), (0, 1), (1, 0), (1, 1)],
    ],
    'T': [
        [(0, 0), (0, 1), (0, 2), (1, 1)],
        [(0, 1), (1, 1), (2, 1), (1, 0)],
        [(1, 0), (1, 1), (1, 2), (0, 1)],
        [(0, 0), (1, 0), (2, 0), (1, 1)],
    ],
    'S': [
        [(1, 0), (1, 1), (0, 1), (0, 2)],
        [(0, 0), (1, 0), (1, 1), (2, 1)],
    ],
    'Z': [
        [(0, 0), (0, 1), (1, 1), (1, 2)],
        [(0, 1), (1, 0), (1, 1), (2, 0)],
    ],
    'J': [
        [(0, 0), (1, 0), (1, 1), (1, 2)],
        [(0, 0), (0, 1), (1, 0), (2, 0)],
        [(0, 0), (0, 1), (0, 2), (1, 2)],
        [(0, 1), (1, 1), (2, 0), (2, 1)],
    ],
    'L': [
        [(0, 2), (1, 0), (1, 1), (1, 2)],
        [(0, 0), (1, 0), (2, 0), (2, 1)],
        [(0, 0), (0, 1), (0, 2), (1, 0)],
        [(0, 0), (0, 1), (1, 1), (2, 1)],
    ],
}

SCORE_TABLE = {1: 100, 2: 300, 3: 500, 4: 800}  # dikalikan level

BONUS_NAMES = {
    'clear_board': 'Ledakan Papan! Semua blok hancur!',
    'free_swap': 'Tukar Bebas! Hold tanpa batas untuk 8 balok berikutnya!',
    'slow_time': 'Waktu Melambat selama 15 detik!',
    'double_score': 'Skor Ganda selama 20 detik!',
    'bottom_clear': 'Baris paling bawah langsung dibersihkan!',
}


# ============================================================
# SUARA PROSEDURAL (dibuat dari kode, tidak butuh file audio)
# ============================================================
class SoundEngine:
    """Membuat efek suara sederhana secara langsung memakai gelombang sinus.
    Dibungkus try/except supaya game tetap berjalan normal walau perangkat
    audio tidak tersedia (misalnya saat dijalankan di server/headless)."""

    def __init__(self):
        self.enabled = False
        self.sounds = {}
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=1)
            import numpy as np

            def make_tone(freq, duration, volume=0.4, fade=True):
                sample_rate = 44100
                n = int(sample_rate * duration)
                t = np.linspace(0, duration, n, False)
                wave = np.sin(freq * t * 2 * np.pi)
                if fade:
                    fade_len = max(1, n // 6)
                    envelope = np.ones(n)
                    envelope[-fade_len:] = np.linspace(1, 0, fade_len)
                    wave = wave * envelope
                audio = (wave * volume * 32767).astype(np.int16)
                return pygame.sndarray.make_sound(audio)

            self.sounds['move'] = make_tone(220, 0.03, 0.15)
            self.sounds['rotate'] = make_tone(330, 0.05, 0.2)
            self.sounds['lock'] = make_tone(150, 0.06, 0.25)
            self.sounds['clear'] = make_tone(660, 0.15, 0.35)
            self.sounds['tetris'] = make_tone(880, 0.25, 0.4)
            self.sounds['drop'] = make_tone(100, 0.08, 0.3)
            self.sounds['gameover'] = make_tone(110, 0.4, 0.35)
            self.sounds['levelup'] = make_tone(550, 0.2, 0.35)
            self.sounds['correct'] = make_tone(700, 0.12, 0.35)
            self.sounds['wrong'] = make_tone(180, 0.18, 0.3)
            self.sounds['bonus'] = make_tone(950, 0.3, 0.4)
            self.enabled = True
        except Exception:
            # Tidak ada perangkat audio / numpy bermasalah -> game tetap jalan tanpa suara
            self.enabled = False

    def play(self, name):
        if self.enabled and name in self.sounds:
            try:
                self.sounds[name].play()
            except Exception:
                pass


# ============================================================
# PIECE (BALOK) YANG SEDANG DIMAINKAN
# ============================================================
class Piece:
    def __init__(self, kind):
        self.kind = kind
        self.rotation = 0
        self.color = COLORS[kind]
        self.special = False  # balok spesial (edukasi) ditandai lewat atribut ini
        # posisi spawn di tengah atas papan.
        # Baris spawn dihitung dari tinggi bentuk piece itu sendiri, supaya
        # bagian bawah piece selalu tepat menyentuh baris paling atas papan
        # (baris index 0). Ini penting: kalau baris spawn selalu tetap seperti
        # -2 untuk semua piece, piece yang pendek (O, T, S, Z, J, L, I mendatar)
        # tidak akan pernah "menyentuh" baris 0 saat baru muncul, sehingga
        # deteksi papan-penuh/game-over tidak akan pernah aktif.
        self.col = COLS // 2 - 2
        max_rel_row = max(r for r, c in SHAPES[kind][0])
        self.row = -max_rel_row

    def cells(self, rotation=None, row_offset=0, col_offset=0):
        rot = self.rotation if rotation is None else rotation
        shape = SHAPES[self.kind][rot % len(SHAPES[self.kind])]
        return [(r + self.row + row_offset, c + self.col + col_offset) for r, c in shape]


class Bag:
    """7-bag randomizer: setiap 7 piece unik muncul sekali sebelum diacak ulang.
    Ini membuat distribusi balok terasa adil, sama seperti Tetris versi resmi."""

    def __init__(self):
        self.queue = []

    def next(self):
        if not self.queue:
            self.queue = list(SHAPES.keys())
            random.shuffle(self.queue)
        return self.queue.pop(0)


# ============================================================
# ENGINE UTAMA GAME
# ============================================================
class Tetris:
    def __init__(self, sound):
        self.sound = sound
        self.bag = Bag()
        self.reset()

    def reset(self):
        self.board = [[None for _ in range(COLS)] for _ in range(ROWS)]
        self.special = [[False for _ in range(COLS)] for _ in range(ROWS)]  # penanda sel balok spesial
        self.bag = Bag()

        # penjadwal balok spesial: muncul setiap 4-7 balok secara acak
        self.pieces_since_special = 0
        self.next_special_threshold = random.randint(4, 7)

        self.current = self._make_piece(self.bag.next())
        self.next_pieces = [self._make_piece(self.bag.next()) for _ in range(3)]
        self.hold_piece = None
        self.can_hold = True
        self.score = 0
        self.lines_cleared = 0
        self.level = 1
        self.fall_time = 0
        self.fall_speed = 800  # ms per turun 1 baris
        self.lock_delay = 400
        self.lock_timer = 0
        self.locking = False
        self.game_over = False
        self.paused = False
        self.combo = 0
        self.clearing_rows = []
        self.clear_anim_timer = 0
        self.pending_special_clear = False

        # status tantangan matematika (quiz) & efek bonus yang sedang aktif
        self.quiz = None
        self.quiz_correct_total = 0
        self.quiz_attempted_total = 0
        self.free_swap_remaining = 0
        self.slow_time_timer = 0
        self.double_score_timer = 0
        self.last_bonus_message = ""
        self.last_bonus_timer = 0

    # ---------- pembuatan piece (dengan kemungkinan menjadi spesial) ----------
    def _make_piece(self, kind):
        piece = Piece(kind)
        self.pieces_since_special += 1
        if self.pieces_since_special >= self.next_special_threshold:
            piece.special = True
            self.pieces_since_special = 0
            self.next_special_threshold = random.randint(4, 7)
        return piece

    # ---------- skor dengan pengali bonus ----------
    def add_score(self, amount):
        multiplier = 2 if self.double_score_timer > 0 else 1
        self.score += int(amount * multiplier)

    # ---------- validasi posisi ----------
    def valid(self, piece, row_offset=0, col_offset=0, rotation=None):
        for r, c in piece.cells(rotation, row_offset, col_offset):
            if c < 0 or c >= COLS or r >= ROWS:
                return False
            if r >= 0 and self.board[r][c] is not None:
                return False
        return True

    # ---------- kontrol pemain ----------
    def move(self, dx):
        if self.valid(self.current, col_offset=dx):
            self.current.col += dx
            self.sound.play('move')
            if self.locking:
                self.lock_timer = 0  # reset lock delay saat masih bisa bergerak

    def rotate(self, direction=1):
        new_rot = (self.current.rotation + direction) % len(SHAPES[self.current.kind])
        # coba rotasi langsung, lalu coba beberapa "kick" sederhana bila mentok
        kicks = [0, -1, 1, -2, 2]
        for kick in kicks:
            if self.valid(self.current, col_offset=kick, rotation=new_rot):
                self.current.rotation = new_rot
                self.current.col += kick
                self.sound.play('rotate')
                if self.locking:
                    self.lock_timer = 0
                return

    def soft_drop(self):
        if self.valid(self.current, row_offset=1):
            self.current.row += 1
            self.add_score(1)
            return True
        return False

    def hard_drop(self):
        dist = 0
        while self.valid(self.current, row_offset=dist + 1):
            dist += 1
        self.current.row += dist
        self.add_score(dist * 2)
        self.sound.play('drop')
        self.lock_piece()

    def hold(self):
        # Tukar Bebas (bonus edukasi): selama free_swap_remaining > 0, hold
        # boleh dipakai berkali-kali pada balok yang sama, tidak hanya sekali.
        if not self.can_hold and self.free_swap_remaining <= 0:
            return
        if self.hold_piece is None:
            new_hold = Piece(self.current.kind)
            new_hold.special = self.current.special
            self.hold_piece = new_hold
            self._spawn_next()
        else:
            swap_kind = self.hold_piece.kind
            swap_special = self.hold_piece.special
            new_hold = Piece(self.current.kind)
            new_hold.special = self.current.special
            self.hold_piece = new_hold
            self.current = Piece(swap_kind)
            self.current.special = swap_special
        if self.free_swap_remaining <= 0:
            self.can_hold = False
        self.sound.play('rotate')

    # ---------- siklus jatuh & penguncian piece ----------
    def _spawn_next(self):
        self.current = self.next_pieces.pop(0)
        self.next_pieces.append(self._make_piece(self.bag.next()))
        self.can_hold = True
        self.locking = False
        self.lock_timer = 0
        if self.free_swap_remaining > 0:
            self.free_swap_remaining -= 1
        if not self.valid(self.current):
            self.game_over = True
            self.sound.play('gameover')
            self._save_highscore()

    def ghost_row(self):
        dist = 0
        while self.valid(self.current, row_offset=dist + 1):
            dist += 1
        return self.current.row + dist

    def lock_piece(self):
        for r, c in self.current.cells():
            if 0 <= r < ROWS and 0 <= c < COLS:
                self.board[r][c] = self.current.color
                if self.current.special:
                    self.special[r][c] = True
        self.sound.play('lock')
        full_rows = [r for r in range(ROWS) if all(self.board[r][c] is not None for c in range(COLS))]
        if full_rows:
            # catat dulu apakah baris yang akan hilang ini mengandung sel spesial,
            # SEBELUM baris tersebut benar-benar dihapus dari papan
            self.pending_special_clear = any(self.special[r][c] for r in full_rows for c in range(COLS))
            self.clearing_rows = full_rows
            self.clear_anim_timer = 120  # ms animasi kedip sebelum baris dihapus
        else:
            self._spawn_next()

    def _finish_clear(self):
        n = len(self.clearing_rows)
        for r in self.clearing_rows:
            del self.board[r]
            del self.special[r]
            self.board.insert(0, [None for _ in range(COLS)])
            self.special.insert(0, [False for _ in range(COLS)])
        self.lines_cleared += n
        self.combo += 1
        gained = SCORE_TABLE.get(n, 0) * self.level
        gained += (self.combo - 1) * 50 * self.level if self.combo > 1 else 0
        self.add_score(gained)
        self.sound.play('tetris' if n == 4 else 'clear')

        new_level = self.lines_cleared // 10 + 1
        if new_level != self.level:
            self.level = new_level
            self.sound.play('levelup')
        self.fall_speed = max(100, 800 - (self.level - 1) * 60)
        self.clearing_rows = []

        was_special = self.pending_special_clear
        self.pending_special_clear = False
        self._spawn_next()

        # kalau baris yang barusan hilang mengandung balok spesial, saatnya
        # tantangan matematika muncul (kecuali kalau game sudah berakhir)
        if was_special and not self.game_over:
            self.start_quiz()

    def update(self, dt_ms):
        if self.game_over or self.paused:
            return

        if self.quiz is not None:
            self._quiz_update(dt_ms)
            return

        if self.slow_time_timer > 0:
            self.slow_time_timer = max(0, self.slow_time_timer - dt_ms)
        if self.double_score_timer > 0:
            self.double_score_timer = max(0, self.double_score_timer - dt_ms)
        if self.last_bonus_timer > 0:
            self.last_bonus_timer = max(0, self.last_bonus_timer - dt_ms)

        if self.clearing_rows:
            self.clear_anim_timer -= dt_ms
            if self.clear_anim_timer <= 0:
                self._finish_clear()
            return

        effective_fall_speed = self.fall_speed * (1.7 if self.slow_time_timer > 0 else 1)

        can_fall = self.valid(self.current, row_offset=1)
        if can_fall:
            self.locking = False
            self.lock_timer = 0
            self.fall_time += dt_ms
            if self.fall_time >= effective_fall_speed:
                self.fall_time = 0
                self.current.row += 1
                if not self.valid(self.current, row_offset=1):
                    self.locking = True
        else:
            self.locking = True
            self.lock_timer += dt_ms
            if self.lock_timer >= self.lock_delay:
                self.lock_piece()
                if not self.clearing_rows:
                    self.combo = 0

    # ---------- TANTANGAN MATEMATIKA (fitur edukasi) ----------
    def _gen_question(self):
        op = random.choice(['+', '-', 'x'])
        if op == '+':
            a, b = random.randint(1, 50), random.randint(1, 50)
            answer = a + b
        elif op == '-':
            a = random.randint(10, 60)
            b = random.randint(1, a)
            answer = a - b
        else:
            a, b = random.randint(2, 12), random.randint(2, 12)
            answer = a * b
        return {'a': a, 'b': b, 'op': op, 'answer': answer}

    def start_quiz(self):
        self.quiz = {
            'questions': [self._gen_question() for _ in range(3)],
            'index': 0,
            'input': '',
            'stage': 'ask',   # 'ask' -> 'feedback' -> (ulang) -> 'summary'
            'timer': 0,
            'results': [],
            'summary_msg': '',
        }

    def quiz_key(self, event):
        if self.quiz is None or self.quiz['stage'] != 'ask':
            return
        if event.key == pygame.K_BACKSPACE:
            self.quiz['input'] = self.quiz['input'][:-1]
        elif event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
            self._quiz_submit()
        elif event.unicode.isdigit() and len(self.quiz['input']) < 6:
            self.quiz['input'] += event.unicode

    def _quiz_submit(self):
        q = self.quiz['questions'][self.quiz['index']]
        given = self.quiz['input']
        try:
            given_val = int(given) if given != '' else None
        except ValueError:
            given_val = None
        correct = (given_val is not None and given_val == q['answer'])
        self.quiz['results'].append({**q, 'given': given, 'correct': correct})
        self.quiz_attempted_total += 1
        if correct:
            self.quiz_correct_total += 1
            self.add_score(50)
            self.sound.play('correct')
        else:
            self.sound.play('wrong')
        self.quiz['stage'] = 'feedback'
        self.quiz['timer'] = 1500
        self.quiz['input'] = ''

    def _quiz_update(self, dt_ms):
        q = self.quiz
        if q['stage'] == 'feedback':
            q['timer'] -= dt_ms
            if q['timer'] <= 0:
                if q['index'] + 1 < len(q['questions']):
                    q['index'] += 1
                    q['stage'] = 'ask'
                else:
                    correct_n = sum(1 for r in q['results'] if r['correct'])
                    q['summary_msg'] = self._resolve_bonus(correct_n)
                    q['stage'] = 'summary'
                    q['timer'] = 2600
        elif q['stage'] == 'summary':
            q['timer'] -= dt_ms
            if q['timer'] <= 0:
                self.quiz = None  # tantangan selesai, lanjut bermain seperti biasa

    def _resolve_bonus(self, correct_n):
        if correct_n == 3:
            effect = random.choice(list(BONUS_NAMES.keys()))
            self._apply_bonus(effect)
            self.sound.play('bonus')
            msg = f"SEMPURNA! 3/3 benar -> {BONUS_NAMES[effect]}"
        elif correct_n == 2:
            bonus = 150 * self.level
            self.add_score(bonus)
            msg = f"BAGUS! 2/3 benar -> Bonus skor +{bonus}"
        else:
            msg = f"{correct_n}/3 benar. Belum dapat bonus kali ini, semangat coba lagi!"
        self.last_bonus_message = msg
        self.last_bonus_timer = 4000
        return msg

    def _apply_bonus(self, effect):
        if effect == 'clear_board':
            self.board = [[None for _ in range(COLS)] for _ in range(ROWS)]
            self.special = [[False for _ in range(COLS)] for _ in range(ROWS)]
            self.add_score(300 * self.level)
        elif effect == 'free_swap':
            self.free_swap_remaining = 8
        elif effect == 'slow_time':
            self.slow_time_timer = 15000
        elif effect == 'double_score':
            self.double_score_timer = 20000
        elif effect == 'bottom_clear':
            for _ in range(2):
                del self.board[ROWS - 1]
                del self.special[ROWS - 1]
                self.board.insert(0, [None for _ in range(COLS)])
                self.special.insert(0, [False for _ in range(COLS)])
            self.add_score(200 * self.level)

    def _save_highscore(self):
        try:
            best = 0
            if os.path.exists(HIGHSCORE_FILE):
                with open(HIGHSCORE_FILE, 'r') as f:
                    best = json.load(f).get('highscore', 0)
            if self.score > best:
                with open(HIGHSCORE_FILE, 'w') as f:
                    json.dump({'highscore': self.score}, f)
        except Exception:
            pass  # tidak masalah kalau gagal simpan, tidak boleh menghentikan game

    @staticmethod
    def load_highscore():
        try:
            if os.path.exists(HIGHSCORE_FILE):
                with open(HIGHSCORE_FILE, 'r') as f:
                    return json.load(f).get('highscore', 0)
        except Exception:
            pass
        return 0


# ============================================================
# TAMPILAN / RENDERING
# ============================================================
def draw_block(surface, x, y, color, size=CELL, alpha=255, special=False):
    rect = pygame.Rect(x, y, size, size)
    block = pygame.Surface((size, size), pygame.SRCALPHA)
    base = (*color, alpha)
    light = tuple(min(255, c + 45) for c in color) + (alpha,)
    dark = tuple(max(0, c - 45) for c in color) + (alpha,)
    pygame.draw.rect(block, base, (0, 0, size, size))
    pygame.draw.line(block, light, (0, 0), (size - 1, 0), 3)
    pygame.draw.line(block, light, (0, 0), (0, size - 1), 3)
    pygame.draw.line(block, dark, (size - 1, 0), (size - 1, size - 1), 3)
    pygame.draw.line(block, dark, (0, size - 1), (size - 1, size - 1), 3)
    surface.blit(block, rect)

    if special:
        # bingkai emas berkedip untuk menandai balok spesial (fitur edukasi)
        pulse = 140 + int(100 * abs(math.sin(pygame.time.get_ticks() / 180)))
        glow = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.rect(glow, (*GOLD, pulse), (0, 0, size, size), width=3, border_radius=3)
        surface.blit(glow, (x, y))


def draw_star_badge(surface, cx, cy, size=8):
    """Lencana bintang kecil emas untuk menandai piece spesial di preview/hold."""
    points = []
    for i in range(8):
        angle = math.pi / 4 * i
        r = size if i % 2 == 0 else size * 0.45
        points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    pygame.draw.polygon(surface, GOLD, points)


def draw_mini_piece(surface, kind, x, y, scale=18, special=False):
    shape = SHAPES[kind][0]
    color = COLORS[kind]
    max_r = max(r for r, c in shape)
    max_c = max(c for r, c in shape)
    off_x = x + (4 - (max_c + 1)) * scale // 2
    off_y = y + (4 - (max_r + 1)) * scale // 2
    for r, c in shape:
        draw_block(surface, off_x + c * scale, off_y + r * scale, color, size=scale - 2, special=special)
    if special:
        draw_star_badge(surface, x + 78, y - 6, size=7)


def draw_text(surface, text, size, color, x, y, center=False, bold=False):
    font = pygame.font.SysFont("consolas", size, bold=bold)
    label = font.render(text, True, color)
    rect = label.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    surface.blit(label, rect)
    return rect


def draw_quiz_overlay(screen, quiz):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 195))
    screen.blit(overlay, (0, 0))

    box_w, box_h = 460, 260
    box = pygame.Rect((WIDTH - box_w) // 2, (HEIGHT - box_h) // 2, box_w, box_h)
    pygame.draw.rect(screen, DARK, box, border_radius=12)
    pygame.draw.rect(screen, GOLD, box, width=3, border_radius=12)

    cx = box.centerx
    top = box.top + 24

    draw_text(screen, "TANTANGAN MATEMATIKA", 22, GOLD, cx, top, center=True, bold=True)
    draw_text(screen, f"Soal {quiz['index'] + 1} dari {len(quiz['questions'])}", 14, GRAY, cx, top + 28, center=True)

    q = quiz['questions'][quiz['index']]

    if quiz['stage'] == 'ask':
        question_str = f"{q['a']} {q['op']} {q['b']} = ?"
        draw_text(screen, question_str, 40, WHITE, cx, box.centery - 20, center=True, bold=True)
        input_display = quiz['input'] if quiz['input'] else "_"
        draw_text(screen, input_display, 30, (120, 220, 255), cx, box.centery + 35, center=True, bold=True)
        draw_text(screen, "Ketik angka lalu tekan Enter", 15, GRAY, cx, box.bottom - 30, center=True)

    elif quiz['stage'] == 'feedback':
        last = quiz['results'][-1]
        question_str = f"{last['a']} {last['op']} {last['b']} = {last['answer']}"
        if last['correct']:
            draw_text(screen, "BENAR!", 34, GREEN, cx, box.centery - 20, center=True, bold=True)
        else:
            given_txt = last['given'] if last['given'] else "(kosong)"
            draw_text(screen, "BELUM TEPAT", 30, RED, cx, box.centery - 30, center=True, bold=True)
            draw_text(screen, f"Jawabanmu: {given_txt}", 16, GRAY, cx, box.centery + 2, center=True)
        draw_text(screen, question_str, 20, WHITE, cx, box.centery + 30, center=True)

    elif quiz['stage'] == 'summary':
        draw_text(screen, "HASIL TANTANGAN", 22, WHITE, cx, box.centery - 40, center=True, bold=True)
        # bungkus teks panjang menjadi beberapa baris pendek
        words = quiz['summary_msg'].split(' ')
        lines, cur = [], ""
        for w in words:
            test = (cur + " " + w).strip()
            if len(test) > 34:
                lines.append(cur)
                cur = w
            else:
                cur = test
        if cur:
            lines.append(cur)
        for i, line in enumerate(lines):
            draw_text(screen, line, 18, GOLD, cx, box.centery + i * 24, center=True, bold=True)


def render(screen, game: Tetris, highscore, muted):
    screen.fill(BLACK)

    board_rect = pygame.Rect(BOARD_X - 4, BOARD_Y - 4, COLS * CELL + 8, ROWS * CELL + 8)
    pygame.draw.rect(screen, DARK, board_rect, border_radius=6)
    pygame.draw.rect(screen, GRID_LINE, board_rect, width=2, border_radius=6)

    # grid halus
    for r in range(ROWS + 1):
        y = BOARD_Y + r * CELL
        pygame.draw.line(screen, GRID_LINE, (BOARD_X, y), (BOARD_X + COLS * CELL, y))
    for c in range(COLS + 1):
        x = BOARD_X + c * CELL
        pygame.draw.line(screen, GRID_LINE, (x, BOARD_Y), (x, BOARD_Y + ROWS * CELL))

    # balok yang sudah terkunci di papan
    flashing = bool(game.clearing_rows) and (pygame.time.get_ticks() // 80) % 2 == 0
    for r in range(ROWS):
        for c in range(COLS):
            color = game.board[r][c]
            if color is not None:
                is_special = game.special[r][c]
                if r in game.clearing_rows and flashing:
                    color = WHITE
                draw_block(screen, BOARD_X + c * CELL, BOARD_Y + r * CELL, color, special=is_special)

    if not game.game_over and not game.clearing_rows and game.quiz is None:
        # ghost piece (bayangan posisi jatuh)
        ghost_r = game.ghost_row()
        for r, c in game.current.cells(row_offset=ghost_r - game.current.row):
            if r >= 0:
                draw_block(screen, BOARD_X + c * CELL, BOARD_Y + r * CELL, game.current.color, alpha=GHOST_ALPHA)
        # piece aktif
        for r, c in game.current.cells():
            if r >= 0:
                draw_block(screen, BOARD_X + c * CELL, BOARD_Y + r * CELL, game.current.color, special=game.current.special)

    # ---------------- SIDEBAR ----------------
    sx = BOARD_X * 2 + COLS * CELL
    draw_text(screen, "TETRIS", 30, WHITE, sx, 20, bold=True)

    draw_text(screen, "SKOR", 16, GRAY, sx, 70)
    draw_text(screen, f"{game.score}", 26, WHITE, sx, 92, bold=True)

    draw_text(screen, "TERTINGGI", 16, GRAY, sx, 135)
    draw_text(screen, f"{max(highscore, game.score)}", 22, (255, 215, 80), sx, 156, bold=True)

    draw_text(screen, "LEVEL", 16, GRAY, sx, 195)
    draw_text(screen, f"{game.level}", 22, WHITE, sx, 216, bold=True)

    draw_text(screen, "BARIS", 16, GRAY, sx, 255)
    draw_text(screen, f"{game.lines_cleared}", 22, WHITE, sx, 276, bold=True)

    y_cursor = 310
    if game.combo > 1:
        draw_text(screen, f"COMBO x{game.combo}", 15, (255, 140, 60), sx, y_cursor, bold=True)
        y_cursor += 20

    # indikator bonus aktif (edukasi)
    if game.double_score_timer > 0:
        draw_text(screen, f"SKOR GANDA {game.double_score_timer // 1000 + 1}s", 13, (255, 215, 80), sx, y_cursor, bold=True)
        y_cursor += 18
    if game.slow_time_timer > 0:
        draw_text(screen, f"MELAMBAT {game.slow_time_timer // 1000 + 1}s", 13, (120, 220, 255), sx, y_cursor, bold=True)
        y_cursor += 18
    if game.free_swap_remaining > 0:
        draw_text(screen, f"TUKAR BEBAS x{game.free_swap_remaining}", 13, (170, 255, 170), sx, y_cursor, bold=True)
        y_cursor += 18

    draw_text(screen, "HOLD (C)", 16, GRAY, sx, 350)
    hold_box = pygame.Rect(sx, 372, 90, 70)
    pygame.draw.rect(screen, DARK, hold_box, border_radius=6)
    pygame.draw.rect(screen, GRID_LINE, hold_box, width=2, border_radius=6)
    if game.hold_piece:
        draw_mini_piece(screen, game.hold_piece.kind, sx + 5, 378, special=game.hold_piece.special)

    draw_text(screen, "BERIKUTNYA", 16, GRAY, sx, 460)
    for i, p in enumerate(game.next_pieces):
        box = pygame.Rect(sx, 482 + i * 78, 90, 70)
        pygame.draw.rect(screen, DARK, box, border_radius=6)
        pygame.draw.rect(screen, GRID_LINE, box, width=2, border_radius=6)
        draw_mini_piece(screen, p.kind, sx + 5, 488 + i * 78, special=p.special)

    if game.quiz_attempted_total > 0:
        draw_text(screen, f"Edukasi: {game.quiz_correct_total}/{game.quiz_attempted_total}", 12, GRAY, sx, HEIGHT - 48)

    mute_label = "SUARA: MATI (M)" if muted else "SUARA: NYALA (M)"
    draw_text(screen, mute_label, 13, GRAY, sx, HEIGHT - 30)

    # pesan hasil bonus terakhir (muncul sebentar di atas papan setelah quiz selesai)
    if game.last_bonus_timer > 0 and game.quiz is None:
        msg_surface = pygame.Surface((COLS * CELL, 30), pygame.SRCALPHA)
        alpha = min(220, game.last_bonus_timer)
        pygame.draw.rect(msg_surface, (0, 0, 0, alpha), (0, 0, COLS * CELL, 30), border_radius=6)
        screen.blit(msg_surface, (BOARD_X, BOARD_Y - 36))
        draw_text(screen, game.last_bonus_message[:42], 13, GOLD, BOARD_X + 6, BOARD_Y - 30)

    # overlay tantangan matematika
    if game.quiz is not None:
        draw_quiz_overlay(screen, game.quiz)

    # overlay pause
    if game.paused and not game.game_over:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        screen.blit(overlay, (0, 0))
        draw_text(screen, "PAUSE", 44, WHITE, WIDTH // 2, HEIGHT // 2 - 20, center=True, bold=True)
        draw_text(screen, "Tekan P atau Esc untuk lanjut", 18, GRAY, WIDTH // 2, HEIGHT // 2 + 25, center=True)

    # overlay game over
    if game.game_over:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        screen.blit(overlay, (0, 0))
        draw_text(screen, "GAME OVER", 46, RED, WIDTH // 2, HEIGHT // 2 - 60, center=True, bold=True)
        draw_text(screen, f"Skor Akhir: {game.score}", 24, WHITE, WIDTH // 2, HEIGHT // 2 - 10, center=True)
        if game.score >= highscore and game.score > 0:
            draw_text(screen, "REKOR BARU!", 20, (255, 215, 80), WIDTH // 2, HEIGHT // 2 + 22, center=True, bold=True)
        draw_text(screen, "Tekan R untuk main lagi", 18, GRAY, WIDTH // 2, HEIGHT // 2 + 60, center=True)
        draw_text(screen, "Tekan Esc untuk keluar", 18, GRAY, WIDTH // 2, HEIGHT // 2 + 85, center=True)

    pygame.display.flip()


# ============================================================
# LOOP UTAMA
# ============================================================
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Tetris Edukasi - Python & Pygame")
    clock = pygame.time.Clock()

    sound = SoundEngine()
    muted = False
    game = Tetris(sound)
    highscore = Tetris.load_highscore()

    # tombol yang perlu diulang otomatis saat ditahan (DAS/ARR sederhana)
    move_keys = {pygame.K_LEFT: -1, pygame.K_RIGHT: 1}
    key_hold_time = {pygame.K_LEFT: 0, pygame.K_RIGHT: 0}
    DAS = 150   # delay sebelum repeat mulai (ms)
    ARR = 40    # jeda antar repeat (ms)
    soft_drop_held = False

    running = True
    while running:
        dt = clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                # saat tantangan matematika aktif, input keyboard dialihkan ke quiz
                if game.quiz is not None:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    else:
                        game.quiz_key(event)
                    continue

                if event.key in (pygame.K_ESCAPE,):
                    if game.game_over:
                        running = False
                    else:
                        game.paused = not game.paused

                elif event.key == pygame.K_p and not game.game_over:
                    game.paused = not game.paused

                elif event.key == pygame.K_r and game.game_over:
                    highscore = max(highscore, game.score)
                    game.reset()

                elif event.key == pygame.K_m:
                    muted = not muted
                    sound.enabled = not muted

                if not game.game_over and not game.paused:
                    if event.key in move_keys:
                        game.move(move_keys[event.key])
                        key_hold_time[event.key] = -DAS  # beri jeda sebelum auto-repeat
                    elif event.key == pygame.K_DOWN:
                        soft_drop_held = True
                    elif event.key in (pygame.K_UP, pygame.K_x):
                        game.rotate(1)
                    elif event.key == pygame.K_z:
                        game.rotate(-1)
                    elif event.key == pygame.K_SPACE:
                        game.hard_drop()
                    elif event.key == pygame.K_c:
                        game.hold()

            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_DOWN:
                    soft_drop_held = False
                if event.key in key_hold_time:
                    key_hold_time[event.key] = 0

        if not game.game_over and not game.paused and game.quiz is None:
            # auto-repeat gerak kiri/kanan saat tombol ditahan
            keys = pygame.key.get_pressed()
            for key, direction in move_keys.items():
                if keys[key]:
                    key_hold_time[key] += dt
                    if key_hold_time[key] >= DAS:
                        key_hold_time[key] -= ARR
                        game.move(direction)
                else:
                    key_hold_time[key] = 0

            if soft_drop_held:
                game.soft_drop()

        if not game.game_over and not game.paused:
            game.update(dt)

        render(screen, game, highscore, muted)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
