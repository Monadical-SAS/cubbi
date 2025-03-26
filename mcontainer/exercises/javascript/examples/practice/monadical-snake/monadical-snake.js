// Code
const collides = (square1, square2) =>
  square1.x === square2.x && square1.y === square2.y;

const collidesWithSnake = (snake, square) =>
  snake.reduce((out, segment) => out || collides(segment, square), false);

const collidesWithWall = (segment, dims) => {
  let [dx, dy] = dims;
  let { x, y } = segment;
  return x >= dx || y >= dy || x < 0 || y < 0;
};

// weird math because JS modulo
// stackoverflow.com/questions/4467539/javascript-modulo-not-behaving
const mod = (m, n) => ((m % n) + n) % n;

export class SnakeGame {
  constructor(ctx) {
      this.newGame();
      this.ctx = ctx;
      this.appleColor = "green"; // Changed apple color to red
  }
  newGame() {
      this.dims = [25, 25];
      this.gameSize = 200;
      this.snake = [{ x: 5, y: 5 }];
      this.newApple();
      this.direction = null;
      this.nextDirection = null;
      this.inputQueue = [];
  }
  collidesWith(snake, square) {
      return snake.reduce((dead, segment) => collides(segment, newSegment), false);
  }
  newApple(won) {
      if (this.snake.length >= this.dims[0] * this.dims[1]) this.newGame();
      do {
          this.apple = {
              x: Math.floor(Math.random() * this.dims[0]),
              y: Math.floor(Math.random() * this.dims[1]),
          };
      } while (collidesWithSnake(this.snake, this.apple));
  }
  isDead(newSegment) {
      return collidesWithWall(newSegment, this.dims) || collidesWithSnake(this.snake.slice(1), newSegment);
  }
  step() {
      this.direction = this.getNextDirection();
      if (!this.direction) return;
      const head = this.snake[this.snake.length - 1];

      const newSegment = {
          x: head.x + this.direction.x,
          y: head.y + this.direction.y,
      };

      if (this.isDead(newSegment)) {
          return this.newGame();
      }

      if (collides(newSegment, this.apple)) {
          this.snake.push(newSegment);
          if (this.appleColor === "red") {
              this.newApple(true);
          } else {
              this.snake.shift();
          }
      } else {
          this.snake.push(newSegment);
          this.snake.shift();
      }
      this.draw();
  }
  draw() {
      this.ctx.clearRect(0, 0, this.gameSize + 11, this.gameSize + 11);
      this.ctx.fillStyle = "black";
      this.ctx.strokeStyle = "black 2px solid";
      let dimx, dimy, sx, sy;
      [dimx, dimy] = this.dims;
      sx = this.gameSize / dimx;
      sy = this.gameSize / dimy;

      this.ctx.strokeRect(10, 10, this.gameSize, this.gameSize);
      for (let segment of this.snake) {
          let { x, y } = segment;
          this.ctx.fillRect(10 + sx * x, 10 + sy * y, sx - 1, sy - 1);
      }
      this.ctx.fillStyle = this.appleColor;
      let { x, y } = this.apple;
      this.ctx.fillRect(10 + sx * x, 10 + sy * y, sx, sy);
  }
  getNextDirection() {
      if (!this.nextDirection) return this.direction;
      if (!this.direction) return this.nextDirection;
      let { x, y } = this.nextDirection;
      if (x === this.direction.x || y === this.direction.y) return this.direction; // cannot eat self
      return this.nextDirection;
  }
  keypress(event) {
      const keyToDirection = {
          37: { x: -1, y: 0 }, // Left
          38: { x: 0, y: -1 }, // Up
          39: { x: 1, y: 0 }, // Right
          40: { x: 0, y: 1 }, // Down
      };

      const direction = keyToDirection[event.keyCode];
      if (!direction)
          return;

      this.nextDirection = direction;
      event.preventDefault();
      return false;
  }
}