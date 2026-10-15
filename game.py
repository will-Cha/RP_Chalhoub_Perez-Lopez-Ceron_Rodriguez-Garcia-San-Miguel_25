"""Purple Defender - a small arcade game written with pygame.

First Assessment | Robot Programming Course | UC3M

The player controls a purple ship at the bottom of the screen and has to
destroy the enemies that fall from the top. Enemies get faster and more
frequent as the game goes on. Letting an enemy reach the bottom, or
crashing into one, costs a life. The game ends when all lives are gone.

Controls
--------
LEFT / RIGHT  or  A / D : move the ship
SPACE                   : shoot
R                       : play again (on the game over screen)
Q or ESC                : quit

Run it with:  python3 game.py
"""

import random
import sys

import pygame

# ---------------------------------------------------------------------------
# Configuration - every tunable value of the game lives here
# ---------------------------------------------------------------------------

# Screen (requirement 11: one consistent screen size used everywhere)
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60
TITLE = "Purple Defender"

# Colours as (red, green, blue)
BACKGROUND = (18, 16, 38)
PURPLE = (138, 79, 255)          # requirement 10: the player is purple
MINT = (160, 232, 200)
CORAL = (240, 110, 90)
YELLOW = (250, 205, 70)
WHITE = (240, 240, 245)
GREY = (130, 130, 155)

# Player
PLAYER_SIZE = 42
PLAYER_SPEED = 7                 # pixels per frame
SHOOT_COOLDOWN = 200             # milliseconds between two shots

# Bullets
BULLET_WIDTH = 5
BULLET_HEIGHT = 16
BULLET_SPEED = 10

# Enemies
ENEMY_SIZE = 34
ENEMY_START_SPEED = 1.3
ENEMY_START_SPAWN_MS = 1150       # time between two enemies at level 1

# Difficulty (requirement 9)
LEVEL_UP_MS = 12000              # a new level every 15 seconds
SPEED_STEP = 0.4                 # enemies get this much faster each level
SPAWN_STEP = 90                 # enemies appear this many ms sooner
MIN_SPAWN_MS = 330               # but never faster than this

# Rules
STARTING_LIVES = 5
POINTS_PER_ENEMY = 10

# The welcome screen ignores key presses for this long, so that a key pressed
# while the window is opening does not skip it by accident.
WELCOME_ARM_MS = 2000


# ---------------------------------------------------------------------------
# Sprites
# ---------------------------------------------------------------------------

class Player(pygame.sprite.Sprite):
    """The purple ship controlled by the player."""

    def __init__(self):
        super().__init__()
        # The ship is drawn with code, so the game needs no image files.
        self.image = pygame.Surface((PLAYER_SIZE, PLAYER_SIZE), pygame.SRCALPHA)
        pygame.draw.polygon(
            self.image,
            PURPLE,
            [(PLAYER_SIZE // 2, 0), (PLAYER_SIZE, PLAYER_SIZE), (0, PLAYER_SIZE)],
        )
        pygame.draw.rect(self.image, WHITE, (PLAYER_SIZE // 2 - 3, 6, 6, 11))

        self.rect = self.image.get_rect(
            midbottom=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 24)
        )
        self.last_shot = 0

    def update(self, keys):
        """Move the ship according to the keys currently held down."""
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.rect.x -= PLAYER_SPEED
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.rect.x += PLAYER_SPEED

        # Keep the ship inside the window.
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH

    def shoot(self, now, bullets):
        """Fire a bullet, unless the weapon is still cooling down."""
        if now - self.last_shot >= SHOOT_COOLDOWN:
            self.last_shot = now
            bullets.add(Bullet(self.rect.centerx, self.rect.top))


class Bullet(pygame.sprite.Sprite):
    """A shot fired by the player, travelling upwards."""

    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((BULLET_WIDTH, BULLET_HEIGHT))
        self.image.fill(YELLOW)
        self.rect = self.image.get_rect(midbottom=(x, y))

    def update(self):
        self.rect.y -= BULLET_SPEED
        if self.rect.bottom < 0:      # left the screen, no longer needed
            self.kill()


class Enemy(pygame.sprite.Sprite):
    """An enemy that falls from the top of the screen on its own."""

    def __init__(self, speed):
        super().__init__()
        self.image = pygame.Surface((ENEMY_SIZE, ENEMY_SIZE), pygame.SRCALPHA)
        colour = random.choice([MINT, CORAL])
        pygame.draw.rect(self.image, colour, (0, 0, ENEMY_SIZE, ENEMY_SIZE))
        pygame.draw.circle(self.image, BACKGROUND, (11, 13), 4)
        pygame.draw.circle(self.image, BACKGROUND, (ENEMY_SIZE - 11, 13), 4)

        start_x = random.randint(0, SCREEN_WIDTH - ENEMY_SIZE)
        self.rect = self.image.get_rect(topleft=(start_x, -ENEMY_SIZE))

        # The rectangle only stores whole pixels, so the exact vertical
        # position is kept separately as a float.
        self.y = float(self.rect.y)
        self.speed = speed
        self.drift = random.choice([-1, 0, 1])   # slight sideways movement

    def update(self):
        self.y += self.speed
        self.rect.y = int(self.y)

        self.rect.x += self.drift
        if self.rect.left < 0 or self.rect.right > SCREEN_WIDTH:
            self.drift = -self.drift             # bounce off the walls

    def has_escaped(self):
        """True once the enemy has fallen past the bottom of the screen."""
        return self.rect.top > SCREEN_HEIGHT


# ---------------------------------------------------------------------------
# The game itself
# ---------------------------------------------------------------------------

class Game:
    """Holds the whole game: its state, the sprites and the main loop."""

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()

        self.font_big = pygame.font.Font(None, 76)
        self.font_mid = pygame.font.Font(None, 38)
        self.font_small = pygame.font.Font(None, 26)

        # A few stars in the background, generated once.
        self.stars = [
            (random.randint(0, SCREEN_WIDTH), random.randint(0, SCREEN_HEIGHT),
             random.randint(1, 2))
            for _ in range(70)
        ]

        self.best_score = 0
        self.state = "welcome"       # "welcome", "playing" or "game_over"
        self.welcome_shown_at = pygame.time.get_ticks()
        self.new_round()

    # -- setting up a round --------------------------------------------------

    def new_round(self):
        """Reset everything so a fresh game can start."""
        self.player = Player()
        self.bullets = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()

        self.score = 0
        self.lives = STARTING_LIVES
        self.level = 1
        self.enemy_speed = ENEMY_START_SPEED
        self.spawn_delay = ENEMY_START_SPAWN_MS

        now = pygame.time.get_ticks()
        self.last_spawn = now
        self.last_level_up = now

    # -- input ---------------------------------------------------------------

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit()

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.quit()

                elif self.state == "welcome":
                    # Requirement 2: any key starts the game, but only once
                    # the screen has been visible for a moment.
                    ready = (pygame.time.get_ticks() - self.welcome_shown_at
                             >= WELCOME_ARM_MS)
                    if ready:
                        self.new_round()
                        self.state = "playing"

                elif self.state == "game_over":
                    if event.key == pygame.K_r:
                        self.new_round()
                        self.state = "playing"
                    elif event.key == pygame.K_q:
                        self.quit()

    # -- game logic ----------------------------------------------------------

    def update(self):
        now = pygame.time.get_ticks()
        keys = pygame.key.get_pressed()

        self.player.update(keys)
        if keys[pygame.K_SPACE]:
            self.player.shoot(now, self.bullets)

        self.bullets.update()
        self.enemies.update()

        # New enemies appear on their own (requirement 4).
        if now - self.last_spawn >= self.spawn_delay:
            self.last_spawn = now
            self.enemies.add(Enemy(self.enemy_speed))

        # The game gets harder over time (requirement 9).
        if now - self.last_level_up >= LEVEL_UP_MS:
            self.last_level_up = now
            self.level += 1
            self.enemy_speed += SPEED_STEP
            self.spawn_delay = max(MIN_SPAWN_MS, self.spawn_delay - SPAWN_STEP)

        # A bullet destroying an enemy gives points (requirement 6).
        hits = pygame.sprite.groupcollide(self.bullets, self.enemies, True, True)
        for destroyed in hits.values():
            self.score += POINTS_PER_ENEMY * len(destroyed)

        # An enemy that reaches the bottom costs a life.
        for enemy in list(self.enemies):
            if enemy.has_escaped():
                enemy.kill()
                self.lose_life()

        # Crashing into an enemy also costs a life (requirement 5).
        if pygame.sprite.spritecollide(self.player, self.enemies, True):
            self.lose_life()

    def lose_life(self):
        self.lives -= 1
        if self.lives <= 0:
            self.lives = 0
            self.best_score = max(self.best_score, self.score)
            self.state = "game_over"

    # -- drawing -------------------------------------------------------------

    def centred_text(self, text, font, colour, y):
        surface = font.render(text, True, colour)
        self.screen.blit(surface, surface.get_rect(center=(SCREEN_WIDTH // 2, y)))

    def draw_background(self):
        self.screen.fill(BACKGROUND)
        for x, y, size in self.stars:
            pygame.draw.circle(self.screen, (60, 58, 95), (x, y), size)

    def draw_welcome(self):
        self.draw_background()
        self.centred_text(TITLE.upper(), self.font_big, PURPLE, 170)
        self.centred_text("Shoot the enemies before they reach the bottom",
                          self.font_mid, WHITE, 250)
        self.centred_text("Arrow keys or A / D to move      SPACE to shoot",
                          self.font_small, GREY, 330)
        self.centred_text("ESC to quit at any time", self.font_small, GREY, 362)

        waited = pygame.time.get_ticks() - self.welcome_shown_at
        if waited < WELCOME_ARM_MS:
            self.centred_text("Get ready...", self.font_mid, GREY, 460)
        elif (pygame.time.get_ticks() // 500) % 2 == 0:
            # The prompt blinks so it is easy to notice.
            self.centred_text("PRESS ANY KEY TO START",
                              self.font_mid, YELLOW, 460)

    def draw_hud(self):
        # A band behind the texts so enemies falling past do not hide them.
        band = pygame.Surface((SCREEN_WIDTH, 56), pygame.SRCALPHA)
        band.fill((18, 16, 38, 215))
        self.screen.blit(band, (0, 0))

        score = self.font_mid.render("Score: %d" % self.score, True, WHITE)
        self.screen.blit(score, (20, 18))

        level = self.font_small.render("Level %d" % self.level, True, GREY)
        self.screen.blit(level, level.get_rect(midtop=(SCREEN_WIDTH // 2, 24)))

        # The row of lives is right aligned and always has room for the full
        # number, so the label does not move when a life is lost.
        row_width = STARTING_LIVES * 26 - 8
        row_x = SCREEN_WIDTH - 20 - row_width

        lives = self.font_small.render("Lives", True, GREY)
        self.screen.blit(lives, lives.get_rect(topright=(row_x - 14, 24)))
        for i in range(self.lives):
            pygame.draw.rect(
                self.screen, PURPLE, (row_x + i * 26, 24, 18, 18),
            )

    def draw_playing(self):
        self.draw_background()
        self.bullets.draw(self.screen)
        self.enemies.draw(self.screen)
        self.screen.blit(self.player.image, self.player.rect)
        self.draw_hud()                      # requirement 7: score on screen

    def draw_game_over(self):
        self.draw_background()
        self.centred_text("GAME OVER", self.font_big, CORAL, 190)
        self.centred_text("Final score: %d" % self.score,
                          self.font_mid, WHITE, 280)
        self.centred_text("Best this session: %d" % self.best_score,
                          self.font_small, GREY, 320)
        self.centred_text("Press R to play again", self.font_mid, MINT, 410)
        self.centred_text("Press Q to quit", self.font_mid, GREY, 455)

    def draw(self):
        if self.state == "welcome":
            self.draw_welcome()
        elif self.state == "playing":
            self.draw_playing()
        else:
            self.draw_game_over()
        pygame.display.flip()

    # -- main loop -----------------------------------------------------------

    def run(self):
        while True:
            self.handle_events()
            if self.state == "playing":
                self.update()
            self.draw()
            self.clock.tick(FPS)     # keeps the speed smooth and constant

    def quit(self):
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    Game().run()
