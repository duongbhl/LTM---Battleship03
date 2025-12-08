CC = gcc
CFLAGS = -Wall -Iinclude -pthread
LDFLAGS = -lsqlite3 -lm

SRC_DIR = src
OBJ_DIR = obj

SRCS = $(SRC_DIR)/main.c \
       $(SRC_DIR)/server.c \
       $(SRC_DIR)/auth.c \
       $(SRC_DIR)/database.c \
       $(SRC_DIR)/utils.c \
       $(SRC_DIR)/game_session.c \
       $(SRC_DIR)/matchmaking.c \
       $(SRC_DIR)/elo.c \
       $(SRC_DIR)/afk.c \

OBJS = $(SRCS:$(SRC_DIR)/%.c=$(OBJ_DIR)/%.o)

TARGET = server

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CC) $(CFLAGS) $(OBJS) -o $(TARGET) $(LDFLAGS)

$(OBJ_DIR)/%.o: $(SRC_DIR)/%.c
	mkdir -p $(OBJ_DIR)
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -rf $(OBJ_DIR) $(TARGET)
