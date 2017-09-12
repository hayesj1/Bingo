# coding=utf-8

from collections import namedtuple
from enum import unique, IntEnum

from time import sleep
from datetime import datetime, timedelta

from random import randrange

BoardGrid = namedtuple('BoardGrid', 'b, i, n, g, o', verbose=False)
boardBounds = {
	'step':      20,
	'cntPerCol': 5,
	'min':       1,
	'max':       None
}
boardBounds['max'] = 5 * boardBounds['step']
tdZero = timedelta(0)


@unique
class GameSpeed(IntEnum):
	FAST = 3
	NORMAL = 5
	SLOW = 7


class DrawListener:
	id = datetime.utcnow().timestamp()
	lastNumber = None
	lastColumn = None
	newNum = False

	def hasNewNumber(self) -> bool:
		return self.newNum

	def getNumber(self) -> (str, int):
		self.newNum = False
		return self.lastColumn, self.lastNumber

	def numberDrawn(self, num) -> None:
		self.lastNumber = num
		self.lastColumn = self.findColumnFor(num)
		self.newNum = True

	@staticmethod
	def findColumnFor(num) -> str:
		cols = ['b', 'i', 'n', 'g', 'o']
		idx = num // (boardBounds['step'] + 1)
		return cols[idx]

	def __eq__(self, o: object) -> bool:
		if not isinstance(o, DrawListener): return False
		return self.id is o.id


class Board:
	# columns = { 'b': None, 'i': None, 'n': None, 'g': None, 'o': None }
	bingo = False
	markedIndices = []
	getMarkedIndicesKey = lambda item: (item[0], item[1])

	def __init__(self):
		cols = self.createColumns()
		self.columns = BoardGrid._make(cols)
		self.id = datetime.utcnow().timestamp()

	# self.columns['b'] = cols[0]
	# self.columns['i'] = cols[1]
	# self.columns['n'] = cols[2]
	# self.columns['g'] = cols[3]
	# self.columns['o'] = cols[4]

	@staticmethod
	def createColumns() -> list:
		step = boardBounds['step']
		cnt = boardBounds['cntPerCol']
		cols = [[], [], [], [], []]
		i = 0
		lwrBnd = boardBounds['min']
		uprBnd = step
		while i < 5:
			j = 0
			while j < cnt:
				n = randrange(lwrBnd, uprBnd, 1)
				if n in cols[i]:
					continue
				else:
					cols[i].append(n)
					j += 1
			cols[i].sort()
			i += 1
			lwrBnd += step
			uprBnd += step
		return cols

	def hasNumber(self, col, num) -> bool:
		return num in self.columns[col]

	def markNumber(self, col, num) -> None:
		if self.hasNumber(col, num):
			idx = self.columns[col].index(num)
			self.markedIndices.append((col, idx))
			self.markedIndices.sort(key=self.getMarkedIndicesKey)
			self.bingo = self.hasBingo()

	def hasBingo(self) -> bool:
		size = boardBounds['cntPerCol']
		# Not enough marks for a Bingo
		if len(self.markedIndices) < size: return False

		marked = { 'b': [False] * size, 'i': [False] * size, 'n': [False] * size, 'g': [False] * size,
		           'o': [False] * size }
		for (column, index) in self.markedIndices: marked[column][index] = True

		# Bingo cases
		# Case: Diagonal LR
		if marked['b'][0] and marked['i'][1] and marked['n'][2] and marked['g'][3] and marked['o'][4]: return True
		# Case: Diagonal RL
		if marked['b'][4] and marked['i'][3] and marked['n'][2] and marked['g'][1] and marked['o'][0]: return True
		# Case: Vertical
		if marked['b'][0] and marked['b'][1] and marked['b'][2] and marked['b'][3] and marked['b'][4]: return True
		if marked['i'][0] and marked['i'][1] and marked['i'][2] and marked['i'][3] and marked['i'][4]: return True
		if marked['n'][0] and marked['n'][1] and marked['n'][2] and marked['n'][3] and marked['n'][4]: return True
		if marked['g'][0] and marked['g'][1] and marked['g'][2] and marked['g'][3] and marked['g'][4]: return True
		if marked['o'][0] and marked['o'][1] and marked['o'][2] and marked['o'][3] and marked['o'][4]: return True
		# Case: Horizontal
		if marked['b'][0] and marked['i'][0] and marked['n'][0] and marked['g'][0] and marked['o'][0]: return True
		if marked['b'][1] and marked['i'][1] and marked['n'][1] and marked['g'][1] and marked['o'][1]: return True
		if marked['b'][2] and marked['i'][2] and marked['n'][2] and marked['g'][2] and marked['o'][2]: return True
		if marked['b'][3] and marked['i'][3] and marked['n'][3] and marked['g'][3] and marked['o'][3]: return True
		if marked['b'][4] and marked['i'][4] and marked['n'][4] and marked['g'][4] and marked['o'][4]: return True

		# No bingo
		return False

	def __eq__(self, o: object) -> bool:
		if not isinstance(o, Board): return False
		return self.id is o.id

	def __repr__(self):
		return 'B: %r\nI: %r\nN: %r\nG: %r\nO: %r' % (str(self.columns.b), str(self.columns.i),
		                                              str(self.columns.n), str(self.columns.g),
		                                              str(self.columns.o))


class BingoController:
	id = datetime.utcnow().timestamp()
	drawListeners = []

	boards = []
	calledNums = []
	numBingos = 0
	bingoLimit = 0
	timeLimit = tdZero
	endTime = datetime.min
	initialPause = 4
	limiterPause = GameSpeed.NORMAL

	def __init__(self, num_players, listeners, maxBingos=0, duration=tdZero, initialPause=4, limiterPause=3):
		self.numBingos = 0
		self.bingoLimit = maxBingos
		self.timeLimit = duration
		self.initialPause = initialPause
		self.limiterPause = limiterPause
		self.endTime = datetime.min
		self.drawListeners += listeners
		self.abort = False
		i = 0
		while i < num_players:
			brd = Board()
			self.boards.append(brd)
			i += 1

	def start(self) -> None:
		sleep(self.initialPause)
		self.endTime = datetime.utcnow() + self.timeLimit
		while not self.endGame():
			number = self.drawNumber()
			self.calledNums.append(number)
			self.updateDrawListeners(number)

			if self.abort: break
			else: sleep(self.limiterPause)

		# TODO: handle aborts better
		return

	def endGame(self) -> bool:
		return (0 < self.bingoLimit <= self.numBingos) or (tdZero < self.timeLimit and self.endTime <= datetime.utcnow())

	def abortGame(self) -> None:
		self.abort = True

	def drawNumber(self) -> int:
		while True:
			n = randrange(boardBounds['min'], boardBounds['max'], 1)
			if n in self.calledNums:
				continue
			else:
				return n

	def adjustSpeed(self, newSpeed=GameSpeed.NORMAL) -> None:
		if newSpeed <= 0 or newSpeed > GameSpeed.FAST:
			newSpeed = GameSpeed.NORMAL
		self.limiterPause = newSpeed

	def bingo(self, listener, board=None) -> None:
		self.numBingos += 1
		self.drawListeners.remove(listener)

	def updateDrawListeners(self, num) -> None:
		for listener in self.drawListeners:
			listener.numberDrawn(num)

	def __eq__(self, o: object) -> bool:
		if not isinstance(o, BingoController): return False
		return self.id is o.id


if __name__ == '__main__':
	bingoLim = 2
	timeLim = timedelta(minutes=10)
	game = BingoController(4, maxBingos=bingoLim, duration=timeLim)
	game.start()
