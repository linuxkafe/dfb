/**
 * Main entry point tests
 */
const { main } = require('../src/index.js');

describe('Main entry point', () => {
  test('main function exists and runs without error', () => {
    expect(() => main()).not.toThrow();
  });

  test('basic math', () => {
    expect(1 + 1).toBe(2);
  });
});