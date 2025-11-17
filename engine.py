import random

class Ship:
    def __init__(self, size):
        self.size = size
        self.row = random.randrange(0,9)
        self.col = random.randrange(0,9)
        self.orientation = random.choice(["h", "v"])
        self.indexes = self.compute_indexes()
    
    def compute_indexes(self):
        start_index = self.row * 10 + self.col
        if self.orientation == "h":
            return [start_index + i for i in range(self.size)]
        elif self.orientation == "v":
            return [start_index + i*10 for i in range(self.size)]

class Player:
    def __init__(self):
        self.ships = []
        self.search = ["U" for i in range(100)]
        self.place_ships(sizes=[5, 4, 3, 3, 2])
        list_of_lists = [ship.indexes for ship in self.ships]
        self.indexes = [index for sublist in list_of_lists for index in sublist]
    
    def place_ships(self, sizes):
        for size in sizes:
            placed = False
            while not placed:
                # create new ship
                ship = Ship(size)

                # check possible
                possible = True
                for i in ship.indexes:
                    if i >= 100:
                        possible = False
                        break

                    new_row = i // 10
                    new_col = i % 10

                    if new_row != ship.row and new_col != ship.col:
                        possible = False
                        break

                    for other_ship in self.ships:
                        if i in other_ship.indexes:
                            possible = False
                            break

                if possible:
                    self.ships.append(ship)
                    placed = True


class Game:
    def __init__(self, human1, human2):
        self.human1 = human1
        self.human2 = human2
        self.player1 = Player()
        self.player2 = Player()
        self.player1_turn = True
        self.computer_turn = False   # Không còn AI nên luôn False
        self.over = False
        self.result = None
        self.shots_p1 = 0
        self.shots_p2 = 0
        self.n_shots = 0
        self.last_shot = None
    
    def get_ship_size(self, player_num, pos):
        player = self.player1 if player_num == 1 else self.player2
        for ship in player.ships:
            if pos in ship.indexes:
                return ship.size
        return 0
    
    def make_move(self, i):
        self.last_shot = i
        player = self.player1 if self.player1_turn else self.player2
        opponent = self.player2 if self.player1_turn else self.player1
        hit = False
        
        if i in opponent.indexes:
            player.search[i] = "H"
            hit = True

            for ship in opponent.ships:
                sunk = True
                for idx in ship.indexes:
                    if player.search[idx] == "U":
                        sunk = False
                        break
                if sunk:
                    for idx in ship.indexes:
                        player.search[idx] = "S"
        else:
            player.search[i] = "M"
        
        gameover = True
        for idx in opponent.indexes:
            if player.search[idx] == "U":
                gameover = False

        self.over = gameover
        if gameover:
            self.result = 1 if self.player1_turn else 2
        
        # switch turn
        if not hit:
            self.player1_turn = not self.player1_turn

        if self.player1_turn:
            self.shots_p1 += 1
        else:
            self.shots_p2 += 1

        self.n_shots += 1
