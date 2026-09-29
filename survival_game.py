import math
import random
import sys
import pygame

TILE_SIZE = 32
WORLD_SIZE = 120
SCREEN_W, SCREEN_H = 1280, 720


class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 24, 24)
        self.speed = 180
        self.max_health = 100
        self.health = 100
        self.max_magic = 100
        self.magic = 100
        self.max_stamina = 100
        self.stamina = 100
        self.attack_cd = 0.0
        self.magic_cd = 0.0
        self.direction = (1, 0)
        self.weapon = "sword"
        self.inventory = {
            "sword": 1,
            "iron_sword": 0,
            "magic_staff": 1,
            "bow": 0,
            "spear": 0,
            "wood": 0,
            "stone": 0,
            "iron": 0,
            "gold": 0,
            "food": 3,
            "meat": 0,
            "fish": 0,
            "potion": 1,
            "magic_potion": 0,
            "magic_orb": 0,
            "crystal": 0,
            "rope": 0,
            "torch": 2,
        }
        self.wealth = 0
        self.boat_mode = False
        self.in_cave = False
        self.hunger = 100
        self.fatigue = 100

    def move(self, dx, dy, world):
        nx = self.rect.x + dx
        ny = self.rect.y + dy

        test_x = pygame.Rect(nx, self.rect.y, self.rect.w, self.rect.h)
        test_y = pygame.Rect(self.rect.x, ny, self.rect.w, self.rect.h)

        if not world.collides_with_block(test_x):
            self.rect.x = nx
        if not world.collides_with_block(test_y):
            self.rect.y = ny

        if dx != 0 or dy != 0:
            self.direction = (1 if dx >= 0 else -1, 1 if dy >= 0 else -1)
            self.fatigue = max(0, self.fatigue - 0.2)
            self.hunger = max(0, self.hunger - 0.1)

    def attack(self, enemy):
        if self.attack_cd > 0:
            return False
        self.attack_cd = 0.42
        if enemy is not None:
            weapon_damage = 18 if self.weapon == "sword" else 25 if self.weapon == "iron_sword" else 15
            enemy.health -= weapon_damage
            enemy.hit_flash = 0.15
            return True
        return False

    def cast_magic(self, world_mouse):
        if self.magic_cd > 0 or self.magic < 8:
            return None
        self.magic_cd = 0.32
        self.magic -= 8
        dx = world_mouse[0] - self.rect.centerx
        dy = world_mouse[1] - self.rect.centery
        dist = max(1.0, math.hypot(dx, dy))
        return {
            "x": self.rect.centerx,
            "y": self.rect.centery,
            "vx": (dx / dist) * 420,
            "vy": (dy / dist) * 420,
            "damage": 18,
            "radius": 5,
            "life": 1.1,
        }


class Enemy:
    def __init__(self, x, y, kind):
        self.kind = kind
        self.rect = pygame.Rect(x, y, 20, 20)
        if kind == "slime":
            self.health = 25
            self.speed = 48
            self.damage = 8
        elif kind == "wolf":
            self.health = 50
            self.speed = 120
            self.damage = 15
        elif kind == "bat":
            self.health = 30
            self.speed = 140
            self.damage = 12
        elif kind == "goblin":
            self.health = 40
            self.speed = 90
            self.damage = 13
        elif kind == "skeleton":
            self.health = 60
            self.speed = 80
            self.damage = 18
        elif kind == "spider":
            self.health = 35
            self.speed = 100
            self.damage = 14
        else:
            self.health = 35
            self.speed = 60
            self.damage = 10
        self.max_health = self.health
        self.hit_flash = 0.0
        self.wander_timer = random.random() * 3
        self.target_x = random.randint(0, 1)
        self.target_y = random.randint(0, 1)
        self.attack_cd = 0

    def update(self, dt, player, world):
        self.hit_flash = max(0, self.hit_flash - dt)
        self.attack_cd = max(0, self.attack_cd - dt)
        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery
        dist = math.hypot(dx, dy)

        move_x = 0
        move_y = 0

        if dist < 280:
            if dist > 0:
                move_x = (dx / dist) * self.speed * dt
                move_y = (dy / dist) * self.speed * dt
        else:
            self.wander_timer -= dt
            if self.wander_timer <= 0:
                self.wander_timer = random.uniform(1.5, 3.5)
                self.target_x = random.choice([-1, 0, 1])
                self.target_y = random.choice([-1, 0, 1])
            move_x = self.target_x * self.speed * 0.28 * dt
            move_y = self.target_y * self.speed * 0.28 * dt

        test_x = pygame.Rect(self.rect.x + move_x, self.rect.y, self.rect.w, self.rect.h)
        if not world.collides_with_block(test_x):
            self.rect.x += move_x

        test_y = pygame.Rect(self.rect.x, self.rect.y + move_y, self.rect.w, self.rect.h)
        if not world.collides_with_block(test_y):
            self.rect.y += move_y

        if dist < 35 and self.attack_cd <= 0:
            player.health -= self.damage * 0.5
            player.hit_flash = 0.2
            self.attack_cd = 1.5


class ItemDrop:
    def __init__(self, kind, x, y, amount=1):
        self.kind = kind
        self.rect = pygame.Rect(x, y, 18, 18)
        self.amount = amount
        self.pulse = random.random() * 2 * math.pi
        self.lifetime = 45.0

    def update(self, dt):
        self.pulse += dt * 6
        self.lifetime -= dt


class World:
    def __init__(self):
        self.tile_size = TILE_SIZE
        self.size = WORLD_SIZE
        self.tiles = {}
        self.resources = []
        self.structures = []
        self.player_spawn = (50 * TILE_SIZE, 50 * TILE_SIZE)
        self.boat = pygame.Rect(80 * TILE_SIZE, 75 * TILE_SIZE, 90, 34)
        self.cave_entrance = pygame.Rect(95 * TILE_SIZE, 79 * TILE_SIZE, 90, 70)
        self.village_rect = pygame.Rect(34 * TILE_SIZE, 18 * TILE_SIZE, 250, 250)
        self.underwater_cave = pygame.Rect(110 * TILE_SIZE, 85 * TILE_SIZE, 80, 60)
        self.desert_temple = pygame.Rect(30 * TILE_SIZE, 80 * TILE_SIZE, 100, 80)
        self.generate_world()

    def generate_world(self):
        center_x = self.size // 2
        center_y = self.size // 2

        for y in range(self.size):
            for x in range(self.size):
                dx = x - center_x
                dy = y - center_y
                dist = math.hypot(dx, dy)

                if dist < 24:
                    tile = "grass"
                    if random.random() < 0.08:
                        self.resources.append({"type": "tree", "x": x * self.tile_size + 10, "y": y * self.tile_size + 10, "health": 3})
                    if random.random() < 0.03:
                        self.resources.append({"type": "stone", "x": x * self.tile_size + 10, "y": y * self.tile_size + 10, "health": 2})
                    if random.random() < 0.01:
                        self.resources.append({"type": "gold_ore", "x": x * self.tile_size + 10, "y": y * self.tile_size + 10, "health": 3})
                elif dist < 26:
                    tile = "sand"
                elif dist < 30:
                    tile = "water"
                else:
                    tile = "water"

                if dist > 32 and (x + y) % 11 == 0 and random.random() < 0.2:
                    tile = "mountain"
                if dist < 24 and random.random() < 0.05:
                    tile = "forest"
                if 35 < x < 45 and 15 < y < 28:
                    tile = "grass"
                if 20 < x < 35 and 75 < y < 90:
                    tile = "sand"

                self.tiles[(x, y)] = tile

        self.structures = [
            {"type": "cave_gate", "rect": self.cave_entrance},
            {"type": "underwater_cave", "rect": self.underwater_cave},
            {"type": "desert_temple", "rect": self.desert_temple},
            {"type": "village_hut", "rect": pygame.Rect(34 * TILE_SIZE, 20 * TILE_SIZE, 80, 70)},
            {"type": "village_hut", "rect": pygame.Rect(38 * TILE_SIZE, 21 * TILE_SIZE, 80, 70)},
            {"type": "village_hut", "rect": pygame.Rect(42 * TILE_SIZE, 19 * TILE_SIZE, 80, 70)},
            {"type": "watchtower", "rect": pygame.Rect(32 * TILE_SIZE, 17 * TILE_SIZE, 50, 50)},
            {"type": "boat", "rect": self.boat},
        ]

    def get_tile(self, world_x, world_y):
        tile_x = int(world_x // self.tile_size)
        tile_y = int(world_y // self.tile_size)
        return self.tiles.get((tile_x, tile_y), "water")

    def collides_with_block(self, rect):
        if rect.left < 0 or rect.right > self.size * self.tile_size:
            return True
        if rect.top < 0 or rect.bottom > self.size * self.tile_size:
            return True

        tile_left = int(rect.left // self.tile_size)
        tile_right = int((rect.right - 1) // self.tile_size)
        tile_top = int(rect.top // self.tile_size)
        tile_bottom = int((rect.bottom - 1) // self.tile_size)

        for x in range(tile_left, tile_right + 1):
            for y in range(tile_top, tile_bottom + 1):
                tile = self.tiles.get((x, y), "water")
                if tile in {"water", "mountain"}:
                    return True

        for obj in self.structures:
            if obj["rect"].colliderect(rect):
                if obj["type"] in {"village_hut", "watchtower", "cave_gate", "underwater_cave", "desert_temple"}:
                    return True
        return False


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Island Bound: Survival RPG")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 20)
        self.med_font = pygame.font.Font(None, 28)
        self.big_font = pygame.font.Font(None, 48)
        self.game_over = False
        self.inventory_open = False
        self.day_time = 0.0
        self.world = World()
        self.player = Player(*self.world.player_spawn)
        self.enemies = []
        self.projectiles = []
        self.item_drops = []
        self.camera_x = 0
        self.camera_y = 0
        self.spawn_enemies(8)
        self.message = ""
        self.last_message = 0.0
        self.player.hit_flash = 0.0

    def spawn_enemies(self, count):
        enemy_kinds = ["slime", "wolf", "bat", "goblin", "skeleton", "spider"]
        for _ in range(count):
            x = random.randint(18, 95) * TILE_SIZE
            y = random.randint(18, 95) * TILE_SIZE
            if self.world.get_tile(x, y) in {"water", "mountain"}:
                continue
            if abs(x - self.player.rect.centerx) < 300 and abs(y - self.player.rect.centery) < 300:
                continue
            kind = random.choice(enemy_kinds)
            enemy = Enemy(x, y, kind)
            self.enemies.append(enemy)

    def fetch_debug_world_mouse(self):
        mouse_x, mouse_y = pygame.mouse.get_pos()
        return (mouse_x + self.camera_x, mouse_y + self.camera_y)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_i:
                    self.inventory_open = not self.inventory_open
                if event.key == pygame.K_e:
                    self.interact()
                if event.key == pygame.K_1:
                    self.player.weapon = "sword"
                if event.key == pygame.K_2:
                    self.player.weapon = "magic_staff"
                if event.key == pygame.K_3:
                    self.player.weapon = "iron_sword"
                if event.key == pygame.K_4:
                    self.player.weapon = "bow"
                if event.key == pygame.K_f:
                    if self.player.inventory["food"] > 0:
                        self.player.inventory["food"] -= 1
                        self.player.hunger = min(100, self.player.hunger + 30)
                        self.message = "Ovqat iste'mol qilindi!"
                        self.last_message = 1.0

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    self.player_attack()
                if event.button == 3:
                    self.cast_magic()
        return True

    def interact(self):
        if self.player.rect.colliderect(self.world.boat.inflate(40, 40)):
            self.player.boat_mode = not self.player.boat_mode
            self.message = "Kema chiqarindi!" if self.player.boat_mode else "Kema yopildi."
            self.last_message = 1.0
            return

        if self.player.rect.colliderect(self.world.cave_entrance.inflate(30, 30)):
            self.player.in_cave = not self.player.in_cave
            if self.player.in_cave:
                self.player.rect.center = (96 * TILE_SIZE, 93 * TILE_SIZE)
                self.message = "Sirlari g'orga kirib kelding!"
            else:
                self.player.rect.center = (90 * TILE_SIZE, 80 * TILE_SIZE)
                self.message = "G'or xaritasidan chiqib kelding."
            self.last_message = 2.0
            return

        for drop in self.item_drops[:]:
            if self.player.rect.colliderect(drop.rect.inflate(20, 20)):
                self.player.inventory[drop.kind] = self.player.inventory.get(drop.kind, 0) + drop.amount
                self.item_drops.remove(drop)
                self.message = f"{drop.kind.replace('_', ' ').title()} toplandi!"
                self.last_message = 1.0
                return

    def player_attack(self):
        if self.player.attack_cd > 0:
            return

        nearest = None
        best_dist = 9999
        mouse_world = self.fetch_debug_world_mouse()
        for enemy in self.enemies:
            dist = math.hypot(enemy.rect.centerx - self.player.rect.centerx, enemy.rect.centery - self.player.rect.centery)
            if dist < 65:
                angle = math.atan2(enemy.rect.centery - self.player.rect.centery, enemy.rect.centerx - self.player.rect.centerx)
                aim = math.atan2(mouse_world[1] - self.player.rect.centery, mouse_world[0] - self.player.rect.centerx)
                delta = abs((angle - aim + math.pi) % (2 * math.pi) - math.pi)
                if delta < 1.2 and dist < best_dist:
                    nearest = enemy
                    best_dist = dist

        if nearest:
            weapon_damage = 22 if self.player.weapon == "sword" else 35 if self.player.weapon == "iron_sword" else 20
            nearest.health -= weapon_damage
            nearest.hit_flash = 0.18
            self.player.attack_cd = 0.4

    def cast_magic(self):
        world_mouse = self.fetch_debug_world_mouse()
        proj = self.player.cast_magic(world_mouse)
        if proj:
            self.projectiles.append(proj)

    def update_player(self, dt):
        keys = pygame.key.get_pressed()
        move_x = (keys[pygame.K_d] - keys[pygame.K_a]) * self.player.speed * dt
        move_y = (keys[pygame.K_s] - keys[pygame.K_w]) * self.player.speed * dt

        if self.player.boat_mode:
            move_x *= 1.8
            move_y *= 1.8

        original_pos = self.player.rect.copy()
        self.player.move(move_x, 0, self.world)
        self.player.move(0, move_y, self.world)
        if self.player.rect == original_pos:
            self.player.rect.x = original_pos.x
            self.player.rect.y = original_pos.y

        if self.player.boat_mode:
            if self.world.get_tile(self.player.rect.centerx, self.player.rect.centery) == "water":
                self.player.boat_mode = True
            else:
                self.player.boat_mode = False
                self.message = "Kema shuning uchun emas!"
                self.last_message = 1.0

        self.player.attack_cd = max(0, self.player.attack_cd - dt)
        self.player.magic_cd = max(0, self.player.magic_cd - dt)
        self.player.magic = min(self.player.max_magic, self.player.magic + dt * 12)
        self.player.stamina = min(self.player.max_stamina, self.player.stamina + dt * 8)
        self.player.hunger = max(0, self.player.hunger - dt * 5)
        self.player.fatigue = min(100, self.player.fatigue + dt * 3)
        self.player.hit_flash = max(0, self.player.hit_flash - dt)

        if self.player.hunger < 20:
            self.player.health -= dt * 2
        if self.player.health < 0:
            self.player.health = 0

    def update_enemies(self, dt):
        for enemy in self.enemies[:]:
            enemy.update(dt, self.player, self.world)
            if enemy.health <= 0:
                self.enemies.remove(enemy)
                drop_kind = random.choice(["wood", "stone", "food", "meat", "magic_orb", "crystal"])
                drop_amount = random.randint(1, 3) if drop_kind == "wood" else random.randint(1, 2)
                self.item_drops.append(ItemDrop(drop_kind, enemy.rect.centerx, enemy.rect.centery, drop_amount))

    def update_projectiles(self, dt):
        for proj in self.projectiles[:]:
            proj["x"] += proj["vx"] * dt
            proj["y"] += proj["vy"] * dt
            proj["life"] -= dt
            for enemy in self.enemies:
                if enemy.rect.collidepoint((int(proj["x"]), int(proj["y"]))):
                    enemy.health -= proj["damage"]
                    enemy.hit_flash = 0.15
                    if proj in self.projectiles:
                        self.projectiles.remove(proj)
                    break
            else:
                if proj["life"] <= 0 and proj in self.projectiles:
                    self.projectiles.remove(proj)

    def update_world(self, dt):
        self.day_time += dt * 0.03
        if self.day_time > 1.0:
            self.day_time = 0.0

        if self.day_time > 0.65:
            if random.random() < 0.04:
                self.spawn_enemies(1)

        self.camera_x = max(0, min(self.player.rect.centerx - SCREEN_W // 2, self.world.size * TILE_SIZE - SCREEN_W))
        self.camera_y = max(0, min(self.player.rect.centery - SCREEN_H // 2, self.world.size * TILE_SIZE - SCREEN_H))

        self.last_message = max(0, self.last_message - dt)

        for drop in self.item_drops[:]:
            drop.update(dt)
            if drop.lifetime <= 0:
                self.item_drops.remove(drop)

    def draw_tile(self, tile_x, tile_y, tile_kind):
        x = tile_x * TILE_SIZE - self.camera_x
        y = tile_y * TILE_SIZE - self.camera_y
        rect = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)

        if tile_kind == "grass":
            pygame.draw.rect(self.screen, (70, 130, 70), rect)
            pygame.draw.rect(self.screen, (90, 150, 90), rect, 1)
        elif tile_kind == "sand":
            pygame.draw.rect(self.screen, (210, 180, 120), rect)
            pygame.draw.rect(self.screen, (170, 140, 90), rect, 1)
        elif tile_kind == "water":
            pygame.draw.rect(self.screen, (41, 100, 160), rect)
            pygame.draw.rect(self.screen, (80, 140, 200), rect, 1)
        elif tile_kind == "mountain":
            pygame.draw.rect(self.screen, (110, 110, 120), rect)
            pygame.draw.rect(self.screen, (140, 130, 150), rect, 1)
        elif tile_kind == "house":
            pygame.draw.rect(self.screen, (130, 90, 40), rect)
            pygame.draw.rect(self.screen, (160, 110, 60), rect, 1)
        elif tile_kind == "forest":
            pygame.draw.rect(self.screen, (40, 100, 50), rect)
            pygame.draw.rect(self.screen, (20, 60, 30), rect, 1)

    def draw_world(self):
        start_x = int(self.camera_x // TILE_SIZE) - 1
        end_x = int((self.camera_x + SCREEN_W) // TILE_SIZE) + 2
        start_y = int(self.camera_y // TILE_SIZE) - 1
        end_y = int((self.camera_y + SCREEN_H) // TILE_SIZE) + 2

        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                tile = self.world.tiles.get((x, y), "water")
                self.draw_tile(x, y, tile)

        for obj in self.world.structures:
            obj_rect = obj["rect"].copy()
            obj_rect.x -= self.camera_x
            obj_rect.y -= self.camera_y
            if obj["type"] == "boat":
                pygame.draw.rect(self.screen, (110, 70, 30), obj_rect)
                pygame.draw.polygon(self.screen, (180, 150, 80), [(obj_rect.centerx, obj_rect.y - 10), (obj_rect.x + 5, obj_rect.y + obj_rect.h), (obj_rect.x + obj_rect.w - 5, obj_rect.y + obj_rect.h)])
            elif obj["type"] == "cave_gate":
                pygame.draw.rect(self.screen, (30, 35, 45), obj_rect)
                pygame.draw.circle(self.screen, (10, 12, 18), obj_rect.center, 15)
            elif obj["type"] == "village_hut":
                pygame.draw.rect(self.screen, (150, 110, 70), obj_rect)
                pygame.draw.polygon(self.screen, (200, 80, 40), [(obj_rect.x, obj_rect.y), (obj_rect.x + obj_rect.w, obj_rect.y), (obj_rect.x + obj_rect.w / 2, obj_rect.y - 30)])
            elif obj["type"] == "watchtower":
                pygame.draw.rect(self.screen, (120, 90, 50), obj_rect)
                pygame.draw.rect(self.screen, (200, 180, 100), (obj_rect.x + obj_rect.w // 2 - 10, obj_rect.y - 20, 20, 20))
            elif obj["type"] == "underwater_cave":
                pygame.draw.rect(self.screen, (20, 50, 80), obj_rect)
                pygame.draw.circle(self.screen, (5, 20, 50), obj_rect.center, 12)
            elif obj["type"] == "desert_temple":
                pygame.draw.polygon(self.screen, (180, 140, 60), [(obj_rect.x + obj_rect.w // 2, obj_rect.y), (obj_rect.x, obj_rect.y + obj_rect.h), (obj_rect.x + obj_rect.w, obj_rect.y + obj_rect.h)])
                pygame.draw.rect(self.screen, (100, 70, 30), (obj_rect.x + obj_rect.w // 2 - 15, obj_rect.y + obj_rect.h // 3, 30, 30))

        for res in self.world.resources:
            rx = res["x"] - self.camera_x
            ry = res["y"] - self.camera_y
            if res["type"] == "tree":
                pygame.draw.rect(self.screen, (115, 70, 40), (rx - 2, ry + 15, 16, 25))
                pygame.draw.circle(self.screen, (45, 140, 70), (rx + 6, ry + 10), 20)
                pygame.draw.circle(self.screen, (55, 150, 80), (rx - 5, ry + 20), 12)
            elif res["type"] == "stone":
                pygame.draw.circle(self.screen, (140, 140, 145), (rx + 8, ry + 8), 11)
                pygame.draw.circle(self.screen, (155, 155, 160), (rx + 5, ry + 5), 5)
            elif res["type"] == "gold_ore":
                pygame.draw.circle(self.screen, (180, 150, 50), (rx + 8, ry + 8), 11)
                pygame.draw.circle(self.screen, (220, 200, 100), (rx + 4, ry + 4), 5)

        for item in self.item_drops:
            if item.lifetime > 0:
                x = item.rect.x - self.camera_x
                y = item.rect.y - self.camera_y
                colors = {
                    "wood": (150, 100, 50),
                    "stone": (130, 130, 135),
                    "food": (220, 120, 30),
                    "meat": (160, 40, 40),
                    "fish": (100, 150, 200),
                    "potion": (200, 50, 150),
                    "magic_orb": (150, 100, 255),
                    "crystal": (100, 200, 255),
                    "gold": (220, 180, 50),
                    "iron": (120, 120, 130),
                }
                color = colors.get(item.kind, (200, 200, 200))
                pygame.draw.circle(self.screen, color, (int(x + 9), int(y + 9)), 8 + math.sin(item.pulse) * 2)

        for enemy in self.enemies:
            ex = enemy.rect.x - self.camera_x
            ey = enemy.rect.y - self.camera_y
            color_base = {
                "slime": (100, 200, 120),
                "wolf": (160, 100, 80),
                "bat": (130, 90, 180),
                "goblin": (80, 160, 80),
                "skeleton": (200, 200, 200),
                "spider": (100, 50, 100),
            }.get(enemy.kind, (150, 150, 150))
            color = (255, 255, 255) if enemy.hit_flash > 0 else color_base
            if enemy.kind == "slime":
                pygame.draw.ellipse(self.screen, color, (ex, ey, enemy.rect.w, enemy.rect.h))
            elif enemy.kind in ["wolf", "goblin"]:
                pygame.draw.rect(self.screen, color, (ex, ey, enemy.rect.w, enemy.rect.h))
                pygame.draw.polygon(self.screen, color, [(ex + 2, ey), (ex + 6, ey - 4), (ex + 4, ey + 2)])
            elif enemy.kind == "skeleton":
                pygame.draw.circle(self.screen, color, (ex + enemy.rect.w // 2, ey + 5), 6)
                pygame.draw.rect(self.screen, color, (ex + 4, ey + 11, 12, 10))
            elif enemy.kind == "spider":
                pygame.draw.circle(self.screen, color, (ex + enemy.rect.w // 2, ey + enemy.rect.h // 2), 8)
                for i in range(4):
                    leg_x = ex + enemy.rect.w // 2 + math.cos(i * math.pi / 2) * 12
                    leg_y = ey + enemy.rect.h // 2 + math.sin(i * math.pi / 2) * 12
                    pygame.draw.line(self.screen, color, (ex + enemy.rect.w // 2, ey + enemy.rect.h // 2), (leg_x, leg_y), 2)
            else:
                pygame.draw.circle(self.screen, color, (ex + enemy.rect.w // 2, ey + enemy.rect.h // 2), 10)

            health_w = 28
            bar_x = ex - 2
            bar_y = ey - 10
            pygame.draw.rect(self.screen, (50, 50, 50), (bar_x, bar_y, health_w, 5))
            pygame.draw.rect(self.screen, (180, 40, 40), (bar_x, bar_y, health_w * max(0, enemy.health / enemy.max_health), 5))

        px = self.player.rect.x - self.camera_x
        py = self.player.rect.y - self.camera_y
        body_color = (255, 226, 160) if self.player.hit_flash <= 0 else (255, 200, 200)
        accent = (32, 85, 180)
        head_size = 8
        pygame.draw.circle(self.screen, body_color, (int(px + 12), int(py + 7)), head_size)
        pygame.draw.polygon(self.screen, body_color, [(px + 8, py + 13), (px + 16, py + 13), (px + 16, py + 19), (px + 8, py + 19)])
        pygame.draw.rect(self.screen, (80, 80, 80), (px + 3, py + 20, 4, 10))
        pygame.draw.rect(self.screen, (80, 80, 80), (px + 17, py + 20, 4, 10))
        pygame.draw.circle(self.screen, (80, 60, 40), (px + 10, py + 10), 2)
        pygame.draw.circle(self.screen, (80, 60, 40), (px + 14, py + 10), 2)

        weapon_color = {"sword": (200, 200, 200), "iron_sword": (180, 180, 200), "magic_staff": (100, 150, 255), "bow": (139, 100, 70)}.get(self.player.weapon, (200, 200, 200))
        if self.player.weapon == "magic_staff":
            pygame.draw.line(self.screen, weapon_color, (px + 12, py + 18), (px + 18, py + 8), 3)
            pygame.draw.circle(self.screen, (150, 100, 255), (px + 18, py + 8), 3)
        elif self.player.weapon == "bow":
            pygame.draw.line(self.screen, weapon_color, (px + 12, py + 18), (px + 20, py + 14), 2)
            pygame.draw.line(self.screen, (150, 100, 60), (px + 20, py + 12), (px + 20, py + 16), 2)
        else:
            pygame.draw.line(self.screen, weapon_color, (px + 12, py + 18), (px + 22, py + 14), 3)

        for proj in self.projectiles:
            pygame.draw.circle(self.screen, (100, 200, 255), (int(proj["x"] - self.camera_x), int(proj["y"] - self.camera_y)), proj["radius"])
            pygame.draw.circle(self.screen, (200, 255, 255), (int(proj["x"] - self.camera_x), int(proj["y"] - self.camera_y)), proj["radius"] // 2)

    def draw_hud(self):
        day_val = math.sin(self.day_time * math.pi * 2 - math.pi / 2)
        phase = "Kundi" if day_val > 0.2 else "Kech" if day_val < -0.2 else "Subh"
        pygame.draw.rect(self.screen, (35, 45, 55), (0, 0, SCREEN_W, 90))
        pygame.draw.rect(self.screen, (100, 100, 100), (0, 0, SCREEN_W, 90), 2)

        health_bar_w = 200
        health_fill = health_bar_w * (self.player.health / self.player.max_health)
        pygame.draw.rect(self.screen, (60, 30, 30), (20, 12, health_bar_w, 16))
        pygame.draw.rect(self.screen, (200, 50, 50), (20, 12, health_fill, 16))
        pygame.draw.rect(self.screen, (200, 200, 200), (20, 12, health_bar_w, 16), 1)

        magic_fill = health_bar_w * (self.player.magic / self.player.max_magic)
        pygame.draw.rect(self.screen, (30, 30, 60), (20, 35, health_bar_w, 16))
        pygame.draw.rect(self.screen, (100, 150, 255), (20, 35, magic_fill, 16))
        pygame.draw.rect(self.screen, (200, 200, 200), (20, 35, health_bar_w, 16), 1)

        hunger_fill = health_bar_w * (self.player.hunger / 100)
        pygame.draw.rect(self.screen, (60, 40, 20), (20, 58, health_bar_w, 16))
        pygame.draw.rect(self.screen, (220, 140, 50), (20, 58, hunger_fill, 16))
        pygame.draw.rect(self.screen, (200, 200, 200), (20, 58, health_bar_w, 16), 1)

        health_text = self.font.render(f"HP: {int(self.player.health)}/{self.player.max_health}", True, (255, 255, 255))
        magic_text = self.font.render(f"MP: {int(self.player.magic)}/{self.player.max_magic}", True, (255, 255, 255))
        hunger_text = self.font.render(f"Oziq: {int(self.player.hunger)}%", True, (255, 255, 255))
        time_text = self.font.render(f"Vaqt: {phase}", True, (255, 255, 255))
        weapon_text = self.font.render(f"Qurol: {self.player.weapon.replace('_', ' ').title()}", True, (255, 255, 255))

        self.screen.blit(health_text, (230, 14))
        self.screen.blit(magic_text, (230, 37))
        self.screen.blit(hunger_text, (230, 60))
        self.screen.blit(time_text, (SCREEN_W - 150, 20))
        self.screen.blit(weapon_text, (SCREEN_W - 150, 50))

        if self.message and self.last_message > 0:
            msg = self.med_font.render(self.message, True, (255, 255, 200))
            shadow = self.med_font.render(self.message, True, (50, 50, 50))
            self.screen.blit(shadow, (SCREEN_W // 2 - msg.get_width() // 2 + 2, SCREEN_H - 55))
            self.screen.blit(msg, (SCREEN_W // 2 - msg.get_width() // 2, SCREEN_H - 57))

    def draw_inventory(self):
        if not self.inventory_open:
            return

        panel = pygame.Rect(220, 80, 840, 540)
        pygame.draw.rect(self.screen, (25, 25, 35), panel)
        pygame.draw.rect(self.screen, (150, 150, 180), panel, 3)

        header = self.big_font.render("INVENTORY", True, (255, 255, 200))
        self.screen.blit(header, (panel.x + 30, panel.y + 15))

        inv_items = list(self.player.inventory.items())
        cols = 3
        for idx, (item_name, count) in enumerate(inv_items):
            col = idx % cols
            row = idx // cols
            x = panel.x + 30 + col * 260
            y = panel.y + 90 + row * 95
            pygame.draw.rect(self.screen, (60, 60, 80), (x, y, 240, 80))
            pygame.draw.rect(self.screen, (150, 150, 180), (x, y, 240, 80), 2)
            label = self.med_font.render(f"{item_name.replace('_', ' ').title()}", True, (255, 255, 200))
            count_text = self.font.render(f"x{count}", True, (200, 200, 255))
            self.screen.blit(label, (x + 15, y + 15))
            self.screen.blit(count_text, (x + 15, y + 50))

        help_text = self.font.render("I - Inventoryni yopish  |  F - Ovqat iste'mol", True, (200, 200, 200))
        self.screen.blit(help_text, (panel.x + 30, panel.y + panel.h - 35))

    def draw_game_over(self):
        if not self.game_over:
            return
        overlay = pygame.Surface((SCREEN_W, SCREEN_H))
        overlay.set_alpha(200)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))
        title = self.big_font.render("O'YIN TUGADI", True, (255, 100, 100))
        self.screen.blit(title, (SCREEN_W // 2 - title.get_width() // 2, SCREEN_H // 2 - 60))

    def update(self, dt):
        if self.game_over:
            return
        self.update_world(dt)
        self.update_player(dt)
        self.update_enemies(dt)
        self.update_projectiles(dt)

        for drop in self.item_drops[:]:
            if self.player.rect.colliderect(drop.rect.inflate(30, 30)):
                self.player.inventory[drop.kind] = self.player.inventory.get(drop.kind, 0) + drop.amount
                self.item_drops.remove(drop)

        if self.player.health <= 0:
            self.game_over = True

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(60) / 1000.0
            running = self.handle_events()
            self.update(dt)
            self.draw_world()
            self.draw_hud()
            self.draw_inventory()
            self.draw_game_over()
            pygame.display.flip()
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    try:
        game = Game()
        game.run()
    except Exception as e:
        print(f"Xato yuz berdi: {e}")
        import traceback
        traceback.print_exc()
