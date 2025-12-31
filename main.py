import atexit
import random
import select
import sys
import termios
import time

fd = sys.stdin.fileno()
old_term = termios.tcgetattr(fd)


def cleanup():
    termios.tcsetattr(fd, termios.TCSADRAIN, old_term)
    print("\033[?25h")


new = old_term[:]
new[3] &= ~(termios.ECHO | termios.ICANON)
new[6][termios.VMIN] = 0
new[6][termios.VTIME] = 0

termios.tcsetattr(fd, termios.TCSADRAIN, new)


atexit.register(cleanup)

print("\033[?25l")
print("\033[2J")


def get_keys():
    keys = []
    while True:
        dr, _, _ = select.select([sys.stdin], [], [], 0)
        if dr:
            ch = sys.stdin.read(1)
            keys.append(ch)
        else:
            break
    return [] if keys == [] else keys[-1]


class Game:
    def __init__(self, arrayHolesTop, arrayHolesBottom):
        self.time_holes = 300
        self.downtime = self.time_holes * 7
        self.board = []
        self.width = 60
        self.platformMax = self.width * 8
        self.tickOverFlow = self.platformMax * 2
        self.lives = 6
        self.gameover = False
        self.arrayHolesTop = arrayHolesTop
        self.arrayHolesBottom = arrayHolesBottom
        self.level = 0
        self.current_time = 0
        self.fall_time = 0
        self.lastInput = 0
        self.lastKeys = []
        self.nextLevel()

    def nextLevel(self):
        self.holesTop = self.arrayHolesTop[self.level]
        self.holesBottom = self.arrayHolesBottom[self.level]
        self.jump = 0
        self.jump_time = 0
        self.falling = 0
        self.imobolized = 0
        self.x = 25
        self.y = 0
        self.tickNum = 0

    def levelComplete(self):
        if len(self.arrayHolesTop) > self.level + 1:
            self.level += 1
            print(f"\033[{len(self.board) // 2 + 1}A", end="", flush=True)
            print(
                " " * (max(self.width - 11, 0) // 2)
                + f"Level {self.level} Beaten"
                + " " * ((max(self.width - 11, 0) // 2) + 1)
            )
            print("\n" * ((len(self.board) // 2) - 1))
            time.sleep(3)
            self.nextLevel()
        else:
            print(f"\033[{len(self.board) // 2 + 1}A", end="", flush=True)
            print(
                " " * (max(self.width - 11, 0) // 2)
                + "Game Beaten"
                + " " * ((max(self.width - 11, 0) // 2) + 1)
            )
            print("\n" * ((len(self.board) // 2) - 1))
            time.sleep(3)
            self.gameover = True

    def handleInput(self, keys):
        if self.imobolized == 0 and self.jump == 0 and self.falling == 0:
            if " " in keys:
                self.jump = 5
                self.jump_time = self.current_time
            elif self.lastInput + self.time_holes > self.current_time:
                if keys != []:
                    self.lastKeys = keys
            else:
                if self.lastKeys != []:
                    if keys == []:
                        keys = self.lastKeys
                    self.lastKeys = []
                if "a" in keys:
                    self.lastInput = self.current_time
                    self.movePlayer(-1, 0)
                elif "d" in keys:
                    self.lastInput = self.current_time
                    self.movePlayer(1, 0)

    def printBoard(self):
        print(f"\033[{len(self.board) + 1}A", end="", flush=True)
        for line in self.board[::-1]:
            print("".join(line))
        print(str(self.lives) + " " * (self.width - 3) + str(self.level))

    def makeHole(self, posNum):
        posNum %= self.platformMax
        self.board[(posNum // self.width * 3) + 2][posNum % self.width] = " "

    def movePlayer(self, x, y):
        if self.y + y >= len(self.board):
            self.levelComplete()
        elif self.board[self.y + y][(self.x + x) % self.width] == " ":
            self.x += x
            self.x %= self.width
            self.y += y
        else:
            self.imobolized = self.current_time
            self.jump = 0

    def gameOver(self):
        self.gameover = True
        print(f"\033[{len(self.board) // 2 + 1}A", end="", flush=True)
        print(
            " " * (max(self.width - 11, 0) // 2)
            + "Game Over"
            + " " * ((max(self.width - 11, 0) // 2) + 1)
        )
        print("\n" * ((len(self.board) // 2) - 1))
        time.sleep(3)

    def fall(self):
        if self.current_time > self.fall_time + self.time_holes / 2:
            if self.y > 0 and self.jump <= 0:
                if self.board[self.y - 1][self.x] == " ":
                    self.falling += 1
                    self.movePlayer(0, -1)
                    self.fall_time = self.current_time
                else:
                    if self.falling > 1:
                        self.imobolized = self.current_time
                    self.falling = 0
            else:
                if self.falling > 0:
                    self.lives -= 1
                    self.imobolized = self.current_time
                    if self.lives == 0:
                        self.gameOver()
                    self.falling = 0

    def tick(self, keys):
        self.current_time = int(time.time() * 1000)
        if self.gameover:
            return

        if self.current_time > self.imobolized + self.downtime:
            self.imobolized = 0

        self.board = [
            ["¯"] * self.width if i % 3 == 2 else [" "] * self.width for i in range(24)
        ]
        # Make holes
        curpos = (self.current_time // self.time_holes) % self.platformMax
        for i in self.holesBottom:
            curpos += i
            self.makeHole(curpos)
            self.makeHole(curpos + 1)
        curpos = (-self.current_time // self.time_holes) % self.platformMax
        for i in self.holesTop:
            curpos += i
            self.makeHole(curpos)
            self.makeHole(curpos + 1)

        # Handle fall
        self.fall()

        # Handle input
        self.handleInput(keys)

        # Handle jump
        if (
            self.jump_time + ((self.time_holes / 2) * (6 - self.jump))
            < self.current_time
        ):
            if self.jump > 0:
                if self.jump == 1:
                    self.jump = 0
                else:
                    self.jump -= 1
                    self.movePlayer(0, 1)

        self.board[self.y][self.x] = "@" if self.imobolized == 0 else "X"

        self.printBoard()
        time.sleep(0.01)


def generate_random_list():
    numbers = []
    total = 0
    while True:
        n = random.choices(range(5, 71), weights=[(i - 4) for i in range(5, 71)], k=1)[
            0
        ]
        if total + n >= 60 * 8:
            break
        numbers.append(n)
        total += n
    return numbers


holesTop = [
    generate_random_list(),
    generate_random_list(),
    generate_random_list(),
    generate_random_list(),
]

holesBottom = [
    generate_random_list(),
    generate_random_list(),
    generate_random_list(),
    generate_random_list(),
]
b = Game(holesTop, holesBottom)
while not b.gameover:
    b.tick(get_keys())
