import { SnakeGame } from './monadical-snake';

const createMockContext = () => {
    return {
      clearRect: jest.fn(),
      fillRect: jest.fn(),
      strokeRect: jest.fn(),
      fillStyle: null,
      strokeStyle: null
    };
  };
  
  // If you're not using Jest, you can use a simpler mock like this:
  const createSimpleMockContext = () => {
    return {
      clearRect: (x, y, width, height) => {},
      fillRect: (x, y, width, height) => {},
      strokeRect: (x, y, width, height) => {},
      fillStyle: null,
      strokeStyle: null
    };
  };
  
  // Create a new instance with the mock context
  const mockCtx = createSimpleMockContext();

describe('Monadical snake', () => {
  describe('Eat apple', () => {
    
    
    test('Apple color is red', () => {
        const snakeGame = new SnakeGame()
        expect(snakeGame.appleColor).toBe('red');
    });

    test('Snake collides with apple', () => {
        const snakeGame = new SnakeGame(mockCtx)
        snakeGame.newApple = jest.fn().mockImplementation()
        snakeGame.nextDirection = { x: 0, y: -1 }
        snakeGame.apple = {
            x: 5,
            y: 3,
        }
        // In the first step newApple should not be called
        snakeGame.step()
        expect(snakeGame.newApple).toHaveBeenCalledTimes(0)

        // In the second step newApple should not be called
        snakeGame.step()
        expect(snakeGame.newApple).toHaveBeenCalledTimes(1)
    })

  });
});